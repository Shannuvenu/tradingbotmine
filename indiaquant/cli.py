"""INDIA QUANT command line.  Usage:  python -m indiaquant.cli <command> [options]

Analysis-only commands never place orders. Live order placement requires:
  live-ready  ->  live-activate (typed confirmation)  ->  run
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import date, timedelta

from .config import ROOT, load_settings, save_default_settings, validate_settings
from .logging_setup import setup_logging


def _svc(args):
    from .app import build
    return build(sandbox=getattr(args, "sandbox", False))


def cmd_init(args):
    save_default_settings()
    svc = _svc(args)
    for d in ("logs", "reports", "secrets", "data_store"):
        (ROOT / d).mkdir(exist_ok=True)
    print(f"Database ready at {svc.settings.db_path} (schema v{svc.db.migrate()}). Settings: config/settings.json")


def cmd_validate(args):
    s = load_settings()
    errs = validate_settings(s)
    from .config import Secrets
    print("Settings:", "OK" if not errs else "PROBLEMS")
    for e in errs:
        print("  -", e)
    print("Secrets:", Secrets.from_env())
    return 1 if errs else 0


def cmd_health(args):
    from .app import api_health, readiness_checks
    svc = _svc(args)
    print(f"State: {svc.state.state} | Session: {svc.calendar.status().phase}")
    for k, v in readiness_checks(svc).items():
        print(f"  [{'OK ' if v['ok'] else 'NO '}] {k}: {v['detail']}")
    if svc.token_info:
        print("Read-only endpoint checks:")
        for k, v in api_health(svc).items():
            print(f"  {k}: {v}")


def cmd_login(args):
    from .broker.auth import interactive_login
    rec = interactive_login(open_browser=not args.no_browser)
    print(f"Logged in as {rec.get('user_id')}. Token stored in secrets/token.json; expires {rec['expires_at']}.")
    print(f"Exchanges enabled: {rec.get('exchanges')} | products: {rec.get('products')}")


def cmd_logout(args):
    from .broker.auth import clear_token
    svc = _svc(args)
    if svc.client.has_token:
        try:
            svc.client.logout()
            print("Upstox session revoked (logout API).")
        except Exception as e:
            print(f"Logout API call failed ({e}); token deleted locally anyway.")
    clear_token()
    print("Local token removed.")


def cmd_sync_instruments(args):
    from .data.instruments import InstrumentMaster, download_bod
    svc = _svc(args)
    im = InstrumentMaster(svc.db)
    for ex in args.exchange:
        ins = download_bod(ex)
        print(f"{ex}: {im.store(ins)} instruments stored")
    print("Purged expired:", im.purge_expired(date.today().isoformat()), "| counts:", im.count())


def cmd_sync_holidays(args):
    svc = _svc(args)
    n = svc.calendar.store_holidays(svc.client.holidays())
    print(f"{n} exchange-holiday rows stored for {date.today().year}")


def cmd_fetch_history(args):
    from .data.history import HistoryService
    svc = _svc(args)
    hs = HistoryService(svc.client, svc.db)
    keys = args.keys or (svc.settings.watchlist + [svc.settings.benchmark_key])
    start = date.today() - timedelta(days=args.days)
    for k in keys:
        for iv in args.interval:
            try:
                n = hs.update(k, iv, start=start)
                print(f"{k} {iv}: {n} rows")
            except Exception as e:
                print(f"{k} {iv}: FAILED {e}")


def cmd_research(args):
    from .research import run_research
    svc = _svc(args)
    if not args.synthetic:
        n = svc.db.query("SELECT COUNT(*) n FROM candles WHERE source NOT LIKE 'SYNTHETIC%'")[0]["n"]
        if n == 0:
            print("No real candles in the database. Run `fetch-history` after login, or use --synthetic "
                  "to exercise the software on clearly-labelled synthetic test data.")
            return 1
    res = run_research(svc.db, svc.settings, synthetic=args.synthetic, keys=args.keys,
                       strategies=args.strategies, capital=args.capital)
    s = res["summary"]
    cols = [c for c in ("instrument_key", "strategy", "verdict", "test_net_pnl", "trades_full", "flags") if c in s]
    print(s[cols].to_string(index=False, max_colwidth=70))
    print("\nReport:", res["report_path"])


def cmd_analyze(args):
    from .data.feed import LiveFeed
    from .execution.engine import TradingEngine
    svc = _svc(args)
    if not svc.client.has_token:
        print("Analysis needs market data: run `login` first.")
        return 1
    if svc.state.state == "SETUP":
        svc.state.to_analysis()
    feed = LiveFeed(svc.client, svc.settings.watchlist, use_websocket=False)
    eng = TradingEngine(svc.settings, svc.db, svc.client, svc.state, svc.calendar, feed)
    feed.poll_once()
    info = eng.cycle()
    print(json.dumps(info, indent=1, default=str))
    for r in svc.db.query("SELECT ts, instrument_key, strategy, decision, decision_reasons FROM signals "
                          "ORDER BY ts DESC LIMIT 20"):
        print(r)


def cmd_live_ready(args):
    from .app import readiness_checks
    svc = _svc(args)
    checks = readiness_checks(svc)
    for k, v in checks.items():
        print(f"  [{'OK ' if v['ok'] else 'NO '}] {k}: {v['detail']}")
    try:
        svc.state.mark_live_ready(checks)
        print("State -> LIVE_READY. Orders are still NOT allowed until `live-activate`.")
    except Exception as e:
        print("Cannot enter LIVE_READY:", e)
        return 1


def cmd_live_activate(args):
    from .execution.state import CONFIRM_PHRASE
    svc = _svc(args)
    print("\n" + "!" * 72 + "\n  WARNING: this enables REAL ORDERS with REAL MONEY in your Upstox account.\n"
          "  Losses can exceed modelled stops (gaps, partial fills, charges, outages).\n"
          "  Activation lasts only for today's IST date.\n" + "!" * 72)
    phrase = input(f"\nType exactly: {CONFIRM_PHRASE}\n> ")
    try:
        svc.state.activate_live(phrase)
        print("LIVE_ACTIVE for today. Start the engine with RUN_LIVE.bat (or `run`). Stop: KILL file / `kill`.")
    except Exception as e:
        print("Not activated:", e)
        return 1


def cmd_run(args):
    from .data.feed import LiveFeed
    from .execution.engine import TradingEngine
    svc = _svc(args)
    if not svc.client.has_token:
        print("No valid token; run login.")
        return 1
    feed = LiveFeed(svc.client, svc.settings.watchlist, use_websocket=not args.no_ws)
    eng = TradingEngine(svc.settings, svc.db, svc.client, svc.state, svc.calendar, feed)
    print(f"Engine starting in state {svc.state.state} (orders only if LIVE_ACTIVE for today). Ctrl+C to stop.")
    eng.run(interval_s=args.interval, max_cycles=args.cycles)


def cmd_halt(args):
    _svc(args).state.halt(args.reason or "manual halt")
    print("HALTED. No new orders. Existing orders/positions unchanged (use `kill` to cancel, --flatten to exit).")


def cmd_resume(args):
    _svc(args).state.resume(args.ack)
    print("Resumed to LIVE_READY (not LIVE_ACTIVE).")


def cmd_kill(args):
    from .execution.engine import TradingEngine
    from .data.feed import LiveFeed
    svc = _svc(args)
    (ROOT / "KILL").write_text("kill switch engaged\n", encoding="utf-8")
    feed = LiveFeed(svc.client, svc.settings.watchlist, use_websocket=False)
    if args.flatten:
        try:
            feed.poll_once()
        except Exception as e:
            print("quote poll failed:", e)
    eng = TradingEngine(svc.settings, svc.db, svc.client, svc.state, svc.calendar, feed)
    try:
        print(eng.kill_switch(args.reason or "manual kill", flatten=args.flatten))
    except Exception as e:
        print("Kill: state HALTED and KILL file written, but broker actions failed:", e,
              "\nCancel/exit manually in the Upstox app NOW if you have open orders/positions.")


def cmd_status(args):
    svc = _svc(args)
    print(json.dumps({"state": svc.state.info, "session": svc.calendar.status().__dict__,
                      "token": {k: v for k, v in (svc.token_info or {}).items() if k != "access_token"},
                      "last_cycle": svc.db.get_state("last_cycle")}, indent=1, default=str))


def main(argv=None):
    setup_logging()
    p = argparse.ArgumentParser(prog="indiaquant")
    p.add_argument("--sandbox", action="store_true", help="route order calls to Upstox sandbox")
    sp = p.add_subparsers(dest="cmd", required=True)
    sp.add_parser("init").set_defaults(f=cmd_init)
    sp.add_parser("validate-config").set_defaults(f=cmd_validate)
    sp.add_parser("health").set_defaults(f=cmd_health)
    a = sp.add_parser("login"); a.add_argument("--no-browser", action="store_true"); a.set_defaults(f=cmd_login)
    sp.add_parser("logout").set_defaults(f=cmd_logout)
    a = sp.add_parser("sync-instruments"); a.add_argument("--exchange", nargs="+", default=["NSE", "BSE"])
    a.set_defaults(f=cmd_sync_instruments)
    sp.add_parser("sync-holidays").set_defaults(f=cmd_sync_holidays)
    a = sp.add_parser("fetch-history"); a.add_argument("--keys", nargs="*"); a.add_argument("--interval", nargs="+",
                                                                                           default=["1d"])
    a.add_argument("--days", type=int, default=365 * 5); a.set_defaults(f=cmd_fetch_history)
    a = sp.add_parser("research"); a.add_argument("--synthetic", action="store_true")
    a.add_argument("--keys", nargs="*"); a.add_argument("--strategies", nargs="*"); a.add_argument("--capital", type=float)
    a.set_defaults(f=cmd_research)
    sp.add_parser("analyze").set_defaults(f=cmd_analyze)
    sp.add_parser("live-ready").set_defaults(f=cmd_live_ready)
    sp.add_parser("live-activate").set_defaults(f=cmd_live_activate)
    a = sp.add_parser("run"); a.add_argument("--interval", type=int, default=60); a.add_argument("--cycles", type=int)
    a.add_argument("--no-ws", action="store_true"); a.set_defaults(f=cmd_run)
    a = sp.add_parser("halt"); a.add_argument("--reason", default=""); a.set_defaults(f=cmd_halt)
    a = sp.add_parser("resume"); a.add_argument("--ack", required=True); a.set_defaults(f=cmd_resume)
    a = sp.add_parser("kill"); a.add_argument("--reason", default=""); a.add_argument("--flatten", action="store_true")
    a.set_defaults(f=cmd_kill)
    sp.add_parser("status").set_defaults(f=cmd_status)
    args = p.parse_args(argv)
    return args.f(args) or 0


if __name__ == "__main__":
    sys.exit(main())
