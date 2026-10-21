# INDIA QUANT — Research notes, sources and implementation decisions

Access date for every web source below: **21 Oct 2026** (unless stated). Facts were read from the
page at that time; brokers and regulators change them — re-check before relying on them.

Evidence labels used throughout the project:

| Label | Meaning |
|---|---|
| THEORY | Established financial theory / mechanism |
| PUBLISHED | Reported in published research; **not re-verified by this project** |
| MEASURED | Produced by this project's backtester on real Upstox data (only in `reports/` after you run research) |
| UNVERIFIED | Hypothesis / practitioner folklore |

> **What was and was not measured in this build.** The build environment could not reach Upstox
> (`api.upstox.com`, `assets.upstox.com` blocked by network policy) and had no credentials, so **no real
> market data was downloaded and no profitability was measured.** All backtests run during development
> used clearly-labelled synthetic random-walk data purely to test the software. Real-data research runs
> on your PC via `RUN_RESEARCH.bat` after login and `SYNC_DATA.bat`.

---

## 1. Upstox API (official docs)

| Topic | Source | Finding → implementation |
|---|---|---|
| Docs index | https://upstox.com/developer/api-documentation/llms.txt | Full endpoint catalogue; v2 order/candle/quote/feed endpoints have v3 replacements. |
| Authentication | https://upstox.com/developer/api-documentation/authentication | OAuth2 code flow: `GET https://api.upstox.com/v2/login/authorization/dialog?response_type=code&client_id&redirect_uri&state` → `POST /v2/login/authorization/token` (form: code, client_id, client_secret, redirect_uri, grant_type=authorization_code). Code is single-use. → `broker/auth.py` with local callback server + `state` CSRF check. |
| Token validity | https://upstox.com/developer/api-documentation/get-token | Token valid until **03:30 IST next day** regardless of issue time; response includes `exchanges`, `products`, `order_types`. A TOTP+PIN token endpoint exists — **deliberately not used** (would require storing your PIN/TOTP secret). → `token_expiry()`, daily re-login. |
| Place order V3 | https://upstox.com/developer/api-documentation/v3/place-order | `POST https://api-hft.upstox.com/v3/order/place`, body fields quantity, product (I/D/MTF), validity (DAY/IOC), price, tag, instrument_token, order_type (MARKET/LIMIT/SL/SL-M), transaction_type, disclosed_quantity, trigger_price, is_amo, slice, market_protection. Response `data.order_ids[]`. `X-Algo-Name` header only for exchange-approved algos. → `OrderRequest.payload()`. |
| Algo/static IP circular | https://upstox.com/developer/api-documentation/announcements/algo-trading-circular ; https://upstox.com/developer/api-documentation/appendix/my-apps-support-for-algo-trading-circular ; https://upstox.com/developer/api-documentation/announcements/static-ip-apis | From **1 Apr 2026** all API order calls (place/modify/cancel/multi/GTT) must originate from a **registered static IP** (primary + optional secondary, user level, changeable once per week; changing it invalidates the token). Algo registration needed only above **10 orders/second**. → readiness check reads `GET /v2/user/ip`; engine stays far below 10 OPS. |
| Regulatory changes live | https://community.upstox.com/t/important-update-regulatory-changes-for-api-and-algo-trading-are-now-live/14874 | **Market orders no longer permitted via API**; Market Price Protection on by default; MCX API trading temporarily disabled. → only LIMIT/SL orders; client refuses MARKET. |
| Rate limits | https://upstox.com/developer/api-documentation/rate-limiting | Orders (non-registered algo) 10/s, 500/min, 2000/30 min; standard APIs 50/s, 500/min, 2000/30 min. → limiter runs at 8/s and 25/s with margin. |
| Instruments | https://upstox.com/developer/api-documentation/instruments | BOD JSON files (`complete/NSE/BSE.json.gz`), refreshed ~06:00 IST; `instrument_key` is unique, `exchange_token` can be reused; `expiry` epoch ms; tick_size sample value 5.0 (interpreted as paise → ₹0.05, cross-checked at runtime). |
| Historical candles V3 | https://upstox.com/developer/api-documentation/v3/get-historical-candle-data | `/v3/historical-candle/{key}/{unit}/{interval}/{to}/{from}`; minutes from Jan 2022 (≤1 month/request for ≤15m), days from Jan 2000 (≤10 years/request). Row = [ts, o, h, l, c, volume, oi]. → `data/history.py` chunking. |
| LTP V3 | https://upstox.com/developer/api-documentation/ltp-v3 | Response map keyed `EXCHANGE:SYMBOL`; re-keyed by `instrument_token`. |
| Funds V3 | https://upstox.com/developer/api-documentation/get-funds-and-margin-v3 | `GET /v3/user/get-funds-and-margin` with `Api-Version: 3.0`; **down 00:00–05:30 IST (423 Locked)**. |
| Order details | https://upstox.com/developer/api-documentation/get-order-details | Status/filled_quantity/pending_quantity/status_message fields used for reconciliation. |
| Option chain | https://upstox.com/developer/api-documentation/get-pc-option-chain | `/v2/option/chain?instrument_key&expiry_date`; broker Greeks (delta, gamma, theta, vega, iv, pop). |
| Brokerage API | https://upstox.com/developer/api-documentation/get-brokerage | `/v2/charges/brokerage` returns per-order charge breakdown. |
| Holidays | https://upstox.com/developer/api-documentation/get-market-holidays | `/v2/market/holidays`; entries with `holiday_type`, `closed_exchanges`. → no hard-coded holidays. |
| Sandbox | https://upstox.com/developer/api-documentation/sandbox | Separate sandbox app, 30-day token, sandbox orders only; host not printed on the page (we default to the SDK's `api-sandbox.upstox.com`, overridable). |
| News / corporate actions | https://upstox.com/developer/api-documentation/get-news ; .../get-corporate-actions | `/v2/news?category=instrument_keys&instrument_keys=` (≤30 keys); `/v2/fundamentals/{isin}/corporate-actions`. |
| Deprecations | https://upstox.com/developer/api-documentation/announcements/deprecation-notice-v2 | v2 place/modify/cancel/candles/LTP/OHLC/feed → v3. We use v3 for all of these. |

**Paths used but not individually re-read this session** (listed in the docs index; `HEALTH_CHECK.bat` calls the read-only ones and reports any 404): positions `/v2/portfolio/short-term-positions`, order book `/v2/order/retrieve-all`, order history `/v2/order/history`, trades `/v2/order/trades/get-trades-for-day`, modify v3 `PUT api-hft…/v3/order/modify`, cancel v3 `DELETE api-hft…/v3/order/cancel?order_id=`, margin `POST /v2/charges/margin`, profile `/v2/user/profile`, market status `/v2/market/status/{exchange}`, intraday v3 `/v3/historical-candle/intraday/{key}/{unit}/{interval}`, logout `DELETE /v2/logout`, static IP `GET /v2/user/ip`.

## 2. SEBI / exchange rules for retail algo trading

* SEBI circular **SEBI/HO/MIRSD/MIRSD-PoD/P/CIR/2025/0000013 (4 Feb 2025)** "Safer participation of retail investors in algorithmic trading"; timeline extended (Jul 2025 → 1 Oct 2025, later circular SEBI/HO/MIRSD/MIRSD-PoD/P/CIR/2025/132); exchange implementation **NSE/INVG/67858 (5 May 2025)**; enforcement at brokers from **1 Apr 2026**.
  Sources: https://www.sebi.gov.in/legal/circulars/jul-2025/extension-of-timeline-for-implementation-of-sebi-circular-sebi-ho-mirsd-mirsd-pod-p-cir-2025-0000013-dated-february-04-2025_95677.html ; Upstox announcements above; summary at https://www.quotaguard.com/blog/sebis-static-ip-mandate-is-live-fix-your-cloud-trading-bot-now (secondary source).
* Practical consequences for this project: static IP for order calls; ≤10 orders/s without algo registration (we default to ≤10 orders/session); orders tagged (`tag` field) for traceability; no market orders.
* **Not legal advice.** Confirm your obligations with Upstox support and the current circulars.

## 3. Charges (Upstox, NSE/BSE) — https://upstox.com/brokerage-charges/

Brokerage: delivery ₹20/order; intraday min(₹20, 0.1%); futures min(₹20, 0.05%); options ₹20 flat.
STT from **1 Apr 2026** (Budget 2026-27): delivery 0.1% both sides; intraday 0.025% sell; futures **0.05%** sell; options **0.15%** of premium on sell; exercised options 0.15%. Corroborated by Zerodha support and news coverage (5paisa, ICICI Direct).
Exchange txn (NSE from 1 Mar 2026): equity 0.00307%, futures 0.00183%, options 0.03553% of premium; BSE equity varies by scrip group. SEBI ₹10/crore. Stamp (buy): 0.015% delivery, 0.003% intraday/options, 0.002% futures. GST 18% on brokerage + transaction (+DP). DP ₹20 + GST per scrip per day on delivery sells. Auto square-off charge ₹75 + GST (engine squares off itself at 15:10 to avoid it).

**Measured consequence (arithmetic, not a backtest):** a ₹500 delivery round trip costs ≈ ₹72 (≈14% of the position: ₹40 brokerage + ₹23.60 DP + GST), so swing/delivery trading with ₹1,000 cannot pass the cost filter. Intraday on ₹500 costs ≈ ₹1.36 round trip (brokerage is 0.1% when that is below ₹20).

## 4. Market structure

NSE/BSE equity: pre-open 09:00–09:15 IST, continuous 09:15–15:30. Holidays from the Upstox API. NSE and BSE instrument keys differ (`NSE_EQ|ISIN` vs `BSE_EQ|ISIN`); cross-venue linking is explicit via ISIN. Derivative lot sizes are large (index option lots are tens of units; SEBI's Nov-2024 framework raised minimum contract value), so ₹1,000 cannot fund futures and only very cheap option premiums × lot.

## 5. Strategy literature (PUBLISHED; not re-verified)

* Time-series momentum — Moskowitz, Ooi & Pedersen (2012), *JFE*; trend following over a century — Hurst, Ooi & Pedersen (2017).
* Technical MA rules — Brock, Lakonishok & LeBaron (1992); later work (Sullivan, Timmermann & White 1999) shows data-snooping bias erodes results.
* Cross-sectional momentum — Jegadeesh & Titman (1993); Indian evidence e.g. Sehgal & Balakrishnan (2002); momentum crashes — Daniel & Moskowitz (2016).
* Short-term reversal — Lehmann (1990); Jegadeesh (1990).
* Variance-ratio test — Lo & MacKinlay (1988) (used in regime features).
* Opening-range breakout — Zarattini, Barbon & Aziz (2023/24) on US equities; **no comparable Indian evidence found → UNVERIFIED for NSE**.
* Backtest overfitting — Bailey, Borwein, López de Prado & Zhu (2014); Harvey, Liu & Zhu (2016) on multiple testing.
* Retail F&O outcomes — SEBI studies (FY22, FY24) report >90% of individual F&O traders lost money.

## 6. Methodology decisions

| Risk | Control in code |
|---|---|
| Look-ahead | signals at close, fills next open; causal indicators; Donchian/volume use prior bars; unit test `test_causality` |
| Overfitting | small parameter grids; selection on train only; validation + untouched test; walk-forward; parameter-stability flag; bootstrap CI of expectancy |
| Survivorship | only currently-listed instruments are downloadable → stated in every report |
| Costs | full statutory schedule + slippage; live cost-to-risk filter mirrored in backtests |
| Small capital | integer quantities from actual capital; unaffordable/cost-blocked signals counted |
| Corporate actions | >25% overnight jumps flagged; corporate-actions API available for confirmation; Upstox does not document adjustment |
| Fundamentals timing | news/fundamentals are display-only; not used by strategies (avoids pre-release leakage) |
| ML | chronological splits with 5-bar purge, baselines, `passed_validation` gate, may only reduce size |
| Confidence | regime/StockShield scores are labelled heuristic and uncalibrated |

## 7. Arbitrage assessment

* NSE↔BSE same-ISIN: computed from bid/ask with full costs and depth; leg risk and broker cross-exchange netting caveats returned with every result. Home-PC latency makes persistent edges unlikely.
* Cash–futures basis: requires shorting futures (margin far above ₹1,000) → not executable for this account.
* Crypto-style triangular arbitrage: no equivalent in NSE/BSE cash equities; not implemented.

## 8. Known limitations

* No real data was available in the build environment; all evidence must come from your own runs.
* Upstox may adjust endpoints; the health check surfaces 404s.
* Option IV/Greeks from Black–Scholes are labelled estimates; broker Greeks preferred.
* Market-wide breadth, sector indices and ASM/GSM surveillance lists are not wired in (no verified free API used).
