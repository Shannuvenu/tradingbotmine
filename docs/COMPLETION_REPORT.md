# Completion report — INDIA QUANT build (21 Oct 2026)

## Environment facts
* Build ran in a Linux sandbox with Python 3.13, numpy, pandas, scipy, scikit-learn, requests.
* **Network policy blocked** `api.upstox.com`, `assets.upstox.com` and PyPI. Consequences:
  * No real market data, instrument files or API responses were obtained. No Upstox endpoint was called.
  * Streamlit, Plotly, pytest and the Upstox SDK could not be installed here; the dashboard was verified by executing
    the full script against a recording stub of Streamlit/Plotly, not in a real browser.
* Official documentation *was* readable via web fetch; all API/regulatory/charge facts come from it (docs/RESEARCH.md).

## What works and was verified here (actually run)
| Item | Evidence |
|---|---|
| 70 automated tests pass (`python -m unittest tests.test_core tests.test_integration`) | covers all 20 acceptance areas below |
| CLI: init, validate-config, health (no-token path), status, research (`--synthetic` and the no-real-data refusal), analyze (no-token refusal) | run manually |
| Full synthetic research pipeline over 10 instruments × 11 strategies, report generation (~70 s) | `docs/SAMPLE_REPORT_SYNTHETIC.md` |
| Dashboard script executes end-to-end (all 9 tabs) with no token | `TestDashboard` |
| OAuth callback flow (local server, state check, code exchange call shape) | `TestLoginAndHistory` (exchange mocked) |

Acceptance mapping: 1 instruments `TestInstruments` · 2 candles `TestValidation` · 3 timezone/sessions/token expiry
`TestCalendar` · 4 indicators + causality `TestIndicators` · 5 signals `TestStrategies` · 6 backtest maths, next-open
fills, gap stops, square-off `TestBacktest` · 7 costs (2026 STT) `TestCosts` · 8–9 sizing, affordability, cost
rejection `TestRisk` · 10 duplicates `test_duplicate_prevention` · 11 stale data `test_stale_quote_and_signal` +
feed tests · 12 daily loss `test_daily_loss` · 13 partial fills `test_partial_fill_and_refresh` · 14 restart recovery
`test_restart_recovery_from_db`, `test_restart_never_resumes_live` · 15 broker errors `TestBrokerErrors` · 16 kill
switch `test_kill_file_halts`, `test_kill_switch_engine_cancels` · 17 live authorization
`test_activation_requires_phrase_and_ready`, `test_orders_blocked_unless_live_active`, `test_activation_expires_next_day`
· 18 redaction `TestRedaction` · 19 persistence `TestDatabase` · 20 dashboard `TestDashboard`.

## Findings that are arithmetic, not opinion
* At ₹1,000, any delivery (swing) trade costs ≈ ₹72 round trip on a ₹500 position → every swing strategy is blocked by
  the cost filter (verdict `NOT_TRADABLE_AT_THIS_CAPITAL`). Intraday costs ≈ ₹1.4 on ₹500 and can pass.
* F&O lots are unaffordable for practically every contract at ₹1,000; F&O is disabled by default.
* Synthetic-data runs were never CANDIDATE (by construction they cannot count as evidence).

## Not verified / remaining actions for you
| Item | Why blocked | What to do |
|---|---|---|
| Every live API call | no network/credentials in build env | FINAL STEP in README → `HEALTH_CHECK.bat` reports each endpoint |
| Endpoint paths not re-read this session (positions, order book/history, trades, modify/cancel v3, margin, profile, market status, intraday v3, logout, static-IP GET) | documented in docs index but pages not individually fetched | HEALTH_CHECK flags any 404; fix in `ENDPOINTS` |
| Tick-size unit (JSON shows 5.0 → assumed paise) | no live file | after SYNC_DATA, `verify_tick_size` and order rejections would reveal a mismatch; check one instrument's tick in the Upstox app |
| WebSocket V3 via SDK (`MarketDataStreamerV3`) | SDK not installable here | if it fails, the feed falls back to REST polling automatically (logged) |
| Sandbox host | not printed on docs page | defaults to SDK value; override `UPSTOX_SANDBOX_BASE` |
| Real-data strategy evidence | no data | `SYNC_DATA.bat` → `RUN_RESEARCH.bat`; read `reports/` |
| Static IP | your network | obtain/register a static IP, or trading orders will be rejected |
| Streamlit visual check | not installable here | `RUN_DASHBOARD.bat`; report any widget error |
| Corporate-action adjustment of candles | Upstox does not document it | large-jump flags in data quality; confirm via corporate-actions API |
| Market breadth, sector indices, ASM/GSM lists | no verified free source wired | optional future work |

## Safety properties (enforced in code and tested)
No order without LIVE_ACTIVE-today; restart downgrades; KILL file halts; MARKET orders refused; order calls never
auto-retried; uncertain outcomes reconciled by tag; daily-loss halt; consecutive-failure halt; no leverage, shorting,
F&O or option writing by default; option writing cannot be enabled; secrets redacted from logs.
