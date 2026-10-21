"""Service container shared by CLI and dashboard."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from .broker.auth import load_token
from .broker.upstox import READ_ONLY_HEALTH, UpstoxClient, UpstoxError
from .config import DATA_DIR, Secrets, load_settings, save_default_settings, validate_settings
from .data.calendar import MarketCalendar, now_ist
from .db import Database
from .execution.state import ExecutionState


@dataclass
class Services:
    settings: object
    db: Database
    client: UpstoxClient
    state: ExecutionState
    calendar: MarketCalendar
    token_info: dict | None


def build(sandbox: bool = False) -> Services:
    save_default_settings()
    s = load_settings()
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    db = Database(s.db_path)
    tok = load_token()
    client = UpstoxClient(tok["access_token"] if tok else "", db=db, sandbox=sandbox, algo_name=s.algo_name)
    return Services(s, db, client, ExecutionState(db), MarketCalendar(db), tok)


def readiness_checks(svc: Services) -> dict:
    """All must pass before LIVE_READY. Read-only calls only; never places an order."""
    checks = {}
    errs = validate_settings(svc.settings)
    checks["settings"] = {"ok": not errs, "detail": "; ".join(errs) or "valid"}
    sec = Secrets.from_env()
    checks["credentials"] = {"ok": bool(sec.client_id and sec.redirect_uri), "detail": repr(sec)}
    checks["token"] = {"ok": bool(svc.token_info), "detail": "valid token present" if svc.token_info else
                       "no valid token; run login"}
    if not svc.token_info:
        return checks
    try:
        prof = svc.client.profile()
        checks["profile"] = {"ok": bool(prof.get("is_active")),
                             "detail": f"exchanges={prof.get('exchanges')} products={prof.get('products')}"}
    except UpstoxError as e:
        checks["profile"] = {"ok": False, "detail": str(e)}
    try:
        cash = svc.client.available_cash()
        checks["funds"] = {"ok": cash > 0, "detail": f"cash available to trade ₹{cash:,.2f}"}
    except (UpstoxError, KeyError, TypeError) as e:
        checks["funds"] = {"ok": False, "detail": f"{e} (funds API is down 00:00–05:30 IST daily)"}
    try:
        ips = svc.client.static_ips()
        checks["static_ip"] = {"ok": bool(ips.get("primary_ip")),
                               "detail": f"primary={ips.get('primary_ip')} secondary={ips.get('secondary_ip')} "
                                         "(orders must originate from one of these)"}
    except UpstoxError as e:
        checks["static_ip"] = {"ok": False, "detail": f"could not read static IPs: {e}"}
    y = now_ist().year
    checks["holidays"] = {"ok": svc.calendar.has_holiday_data(y),
                          "detail": "loaded" if svc.calendar.has_holiday_data(y) else "run sync-holidays"}
    n = svc.db.query("SELECT COUNT(*) n FROM instruments")[0]["n"]
    checks["instruments"] = {"ok": n > 0, "detail": f"{n} instruments in master"}
    return checks


def api_health(svc: Services) -> dict:
    out = {}
    for name in READ_ONLY_HEALTH:
        try:
            {"profile": svc.client.profile, "funds_v3": svc.client.funds, "positions": svc.client.positions,
             "holdings": svc.client.holdings, "order_book": svc.client.order_book,
             "trades_today": svc.client.trades_today, "holidays": svc.client.holidays}[name]()
            out[name] = "ok"
        except UpstoxError as e:
            out[name] = f"ERROR {e.status}: {e}"
    return out


def today() -> str:
    return date.today().isoformat()
