# INDIA QUANT — personal Indian-market intelligence & automated trading (Upstox)

Local Windows application for NSE/BSE research, risk analysis and **deliberately-activated** automated trading
through your own Upstox account. Python + SQLite + Streamlit. No cloud, no paid services.

> **Read first.** Trading can lose money quickly. Nothing in this project is investment advice, and no strategy in it
> has been shown to be profitable. During the build, Upstox was unreachable from the build environment, so **no real
> market data was analysed**: every number you see before you run `SYNC_DATA.bat` + `RUN_RESEARCH.bat` yourself is
> either a unit-test fixture or labelled `SYNTHETIC_TEST_DATA`. The default answer of the system is **NO TRADE**.

## What's in the box

| Area | Where |
|---|---|
| Upstox REST adapter (OAuth, v3 orders, candles, quotes, funds, positions, option chain, charges, holidays, news) | `indiaquant/broker/` |
| Instrument master (NSE/BSE equity, indices, F&O; lot/tick/expiry/strike; rollover) | `indiaquant/data/instruments.py` |
| Historical downloader (incremental, chunked to API limits, validated) | `indiaquant/data/history.py` |
| Live quotes: V3 WebSocket via official SDK, REST-polling fallback, de-dup, ordering, freshness | `indiaquant/data/feed.py` |
| Indicators, cost model (2026 STT), options (BS estimates + broker Greeks), regimes, cointegration | `indiaquant/analytics/` |
| STOCKSHIELD retail-risk intelligence (transparent, non-accusatory) | `indiaquant/analytics/stockshield.py` |
| 11 strategies (trend, breakout, mean reversion, intraday ORB/VWAP/PDH) | `indiaquant/strategies/catalog.py` |
| Backtester + train/validation/test + walk-forward + verdicts | `indiaquant/backtest.py` |
| ML vs. baselines (volatility, adverse-move), model registry | `indiaquant/analytics/ml.py` |
| Research pipeline → `reports/` | `indiaquant/research.py` |
| Risk engine, order manager, state machine, kill switch, engine loop | `indiaquant/execution/` |
| Dashboard (9 tabs) | `dashboard/app.py` |
| CLI | `python -m indiaquant.cli --help` |
| Tests (70) | `tests/` |
| Docs | `docs/` (RESEARCH, RISK, SECURITY, DATABASE, TROUBLESHOOTING, REGULATORY_CHECKLIST, COMPLETION_REPORT) |

## Install (Windows 10/11)

1. Install **Python 3.11–3.13 (64-bit)** from python.org; tick "Add python.exe to PATH".
2. Unzip INDIA QUANT to a folder without special permissions, e.g. `C:\IndiaQuant`.
3. Double-click **`INSTALL_WINDOWS.bat`** (creates `.venv`, installs packages, creates `.env` and the database).
4. Double-click **`RUN_TESTS.bat`** — expect all tests to pass.
5. Double-click **`RUN_DASHBOARD.bat`** → opens http://127.0.0.1:8501 (local only).

PowerShell equivalent:
```powershell
cd C:\IndiaQuant
py -3 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
Copy-Item .env.example .env
.\.venv\Scripts\python.exe -m indiaquant.cli init
.\.venv\Scripts\python.exe -m pytest -q tests
.\.venv\Scripts\python.exe -m streamlit run dashboard\app.py --server.address 127.0.0.1
```

## Daily workflow

| Step | Script | Places orders? |
|---|---|---|
| Log in (token expires 03:30 IST daily) | `LOGIN.bat` | No |
| Instruments, holidays, candles | `SYNC_DATA.bat` | No |
| Research on real data | `RUN_RESEARCH.bat` | No |
| One analysis cycle | `RUN_ANALYSIS.bat` | No |
| Health / config check | `HEALTH_CHECK.bat` | No |
| Dashboard | `RUN_DASHBOARD.bat` | Only via explicit buttons |
| Engine loop | `RUN_LIVE.bat` | **Only if LIVE_ACTIVE today** |
| Emergency stop | `KILL_SWITCH.bat` | Cancels; liquidates only if you type YES |

Execution states: `SETUP → ANALYSIS → RESEARCH → LIVE_READY → LIVE_ACTIVE`, any → `HALTED`.
Starting the app never enables LIVE_ACTIVE; a restart downgrades it; activation expires at day change.

## How a trade can (rarely) happen
signal on completed bar → **research gate** (latest real-data verdict for that strategy+instrument must be
CANDIDATE) → regime gate → STOCKSHIELD not HIGH → **risk engine** (≈25 checks: session, freshness, spread, tick,
affordability, costs vs risk, exposure, positions, orders, failures, daily loss, segment/product permissions) →
state LIVE_ACTIVE → LIMIT order with idempotent tag → protective SL order after fill → square-off 15:10 for intraday.

Configuration: `config/settings.json` (limits, watchlist, enabled strategies). See `docs/RISK.md`.
To study strategies independent of the ₹1,000 constraint: `python -m indiaquant.cli research --capital 100000`
(research only — live sizing still uses your real cash).

---

# FINAL STEP — ADD YOUR UPSTOX API CREDENTIALS

Do this only after `INSTALL_WINDOWS.bat` and `RUN_TESTS.bat` succeed. **Never paste any of these values into a chat,
screenshot, email or GitHub.**

**1. Create the developer app.** Sign in at **https://account.upstox.com/developer/apps** (linked as "Manage API Apps"
from https://upstox.com/developer/api-documentation/). Create a new app (for trading, Upstox lists an Algo Trading App
type). A separate *Sandbox* app can be created for test orders; its token works only for sandbox orders.

**2. App settings.**
- **Redirect URL:** `http://127.0.0.1:8765/callback` — must match `.env` character-for-character. If Upstox rejects a
  plain-http localhost URL, use the exact value it accepts and set the same in `.env`; LOGIN.bat requires the host to be
  `127.0.0.1` or `localhost` (change the port if 8765 is busy).
- **Postback/notifier URL:** leave blank or as Upstox requires (not used by this app).
- **Static IPs:** enter your PC's *public* static IP as Primary (see step 9). Required for order placement only.

**3. Credentials you will get:** *API Key* (= client_id) and *API Secret* (= client_secret). The access token is
created by logging in (step 6); you do not copy it manually.

**4–5. Where they go.** Open the file **`.env`** in the project folder (Notepad is fine) and fill:
```
UPSTOX_CLIENT_ID=<API Key>
UPSTOX_CLIENT_SECRET=<API Secret>
UPSTOX_REDIRECT_URI=http://127.0.0.1:8765/callback
UPSTOX_ACCESS_TOKEN=
```
Leave `UPSTOX_ACCESS_TOKEN` empty (it is only a fallback for a token you generate manually on the portal).
Run `HEALTH_CHECK.bat`: "credentials" should show `client_id=set, client_secret=set`.

**6. Authorize and get the token.** Double-click **`LOGIN.bat`**. Your browser opens the official Upstox login page
(`https://api.upstox.com/v2/login/authorization/dialog?...`). Log in with your own password + 2FA/TOTP. You are
redirected to `127.0.0.1:8765/callback`; the app exchanges the one-time code and saves the token to
`secrets/token.json` with its expiry (03:30 IST next day). Repeat every trading day.

**7. Verify without placing an order.** Run **`HEALTH_CHECK.bat`**. It calls only read-only endpoints (profile, funds,
positions, holdings, order book, trades, holidays) and prints `ok` or the exact error. No order endpoint is called.

**8. Segments and funds.** In the same output, `profile` lists `exchanges` (e.g. NSE, BSE, NFO) and `products`
(I, D, …) enabled on your account, and `funds` shows *cash available to trade*. The funds API is offline 00:00–05:30 IST.
Then run **`SYNC_DATA.bat`** to download instruments, the holiday list, 5 years of daily and ~4 months of 1-minute
candles for the watchlist and Nifty 50.

**9. Static IP, algo registration, tagging.**
- `HEALTH_CHECK.bat` shows `static_ip: primary=… secondary=…` read from `GET /v2/user/ip`. Your PC's public IP must be
  one of them, otherwise every order is rejected. Find your public IP from your router or ISP; home connections are usually
  dynamic — request a static IP from your ISP (or run the engine on a static-IP VPS). The IP can be changed once per week,
  and changing it invalidates the access token (log in again).
- Algo registration with the exchange is required only above **10 orders per second**. This app's default is at most
  10 orders per *session*, so no registration is needed. Only if you have an exchange-approved algo, put its name in
  `config/settings.json → "algo_name"` (sent as the `X-Algo-Name` header).
- Every order is tagged automatically (`IQE…` entry, `IQS…` stop, `IQX…` exit) for traceability.
- Work through `docs/REGULATORY_CHECKLIST.md`.

**10. Run in analysis mode.** `RUN_RESEARCH.bat` (real-data backtests → `reports/`), then `RUN_ANALYSIS.bat` or
`RUN_LIVE.bat` while the state is not LIVE_ACTIVE: signals and risk decisions are logged (dashboard → *Portfolio &
Execution → Signal decisions*) and **no orders are sent**.

**11. Enable live trading deliberately.** Only if you accept the risk and a strategy has a CANDIDATE verdict on real data:
```
.venv\Scripts\python.exe -m indiaquant.cli live-ready      (runs all readiness checks)
.venv\Scripts\python.exe -m indiaquant.cli live-activate   (type the confirmation phrase)
RUN_LIVE.bat
```
(or the dashboard buttons in *Portfolio & Execution*). Activation lasts only for today's IST date. Consider a first
day with `"max_orders_per_session": 2` in `config/settings.json`.

**12. Stop and revoke.**
- Stop now: **`KILL_SWITCH.bat`** or dashboard **EMERGENCY STOP** (halt + cancel pending; positions stay open).
  Liquidation is a separate, explicit confirmation. Ctrl+C in RUN_LIVE stops the loop but does not cancel orders.
- If the PC is unreachable: use the Upstox app/website to cancel orders, exit positions, and enable Upstox's own
  segment Kill Switch.
- Revoke access: `.venv\Scripts\python.exe -m indiaquant.cli logout` (Upstox logout + deletes the local token); for full
  revocation regenerate/delete the API secret or the app at https://account.upstox.com/developer/apps.
- Resume after a halt: delete the `KILL` file, then `python -m indiaquant.cli resume --ack "what I checked"`
  (returns to LIVE_READY, never straight to LIVE_ACTIVE).
