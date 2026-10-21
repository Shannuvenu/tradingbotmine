# Troubleshooting

| Symptom | Cause / fix |
|---|---|
| `python` not found in INSTALL | Install Python 3.11–3.13 64-bit from python.org, tick "Add python.exe to PATH", reopen the window. |
| `upstox-python-sdk` fails to install | Optional. The installer retries core packages; live data falls back to REST polling. |
| `Invalid Credentials` on Upstox login page | `UPSTOX_CLIENT_ID` / `UPSTOX_REDIRECT_URI` in `.env` must exactly match the app on account.upstox.com (including `http://`, port, path). |
| Browser shows "can't reach 127.0.0.1:8765" after login | LOGIN.bat window closed or port busy. Run LOGIN.bat again; or change the port in both `.env` and the Upstox app. |
| `AuthExpired` / 401 | Tokens expire at 03:30 IST daily. Run LOGIN.bat each trading day. Changing static IPs also invalidates tokens. |
| Funds check fails at night | Funds API is in maintenance 00:00–05:30 IST (HTTP 423). Retry after 05:30. |
| Orders rejected mentioning IP | Your public IP is not the static IP registered in the Upstox app. Check with your ISP; IPs can be changed once per week. |
| Order rejected "market orders not allowed" | Not from this app (it never sends MARKET). Check other tools. |
| Session `UNKNOWN_HOLIDAY_DATA` | Run `SYNC_DATA.bat` (sync-holidays). Live trading refuses to run without it. |
| Research says NO_DATA | Run SYNC_DATA.bat after login. Intraday strategies need ≥10 days of 1-minute bars; swing ≥300 daily bars. |
| Every decision is NO_TRADE | Expected until a strategy earns a CANDIDATE verdict on real data and all risk checks pass. Read `decision_reasons` in the dashboard. |
| Dashboard blank / port in use | Close other Streamlit windows or change `--server.port` in RUN_DASHBOARD.bat. |
| A 404 in HEALTH_CHECK | Upstox changed an endpoint path. Update `ENDPOINTS` in `indiaquant/broker/upstox.py` from the official docs. |
| KILL file present | Delete the file `KILL` in the project folder deliberately, then `resume --ack "..."`. |
| Tests fail on Windows | Run from the project folder: `.venv\Scripts\python -m pytest -q tests`. Send the output (no secrets) for help. |
