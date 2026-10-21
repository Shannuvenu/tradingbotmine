# Risk engine defaults and rationale (₹1,000 account)

Edit `config/settings.json` (created by `init`) — never the code. `HEALTH_CHECK.bat` validates it.

| Setting | Default | Why |
|---|---|---|
| starting_capital | 1000 | Sizing base; live checks also use broker-reported cash (lower of the two). |
| max_risk_per_trade_pct | 2% (₹20) | Modelled stop-loss risk per trade. **Not a maximum loss**: gaps, partial fills, rejections and charges can exceed it. |
| max_daily_loss_pct | 5% (₹50) | Realised + unrealised; breach → automatic HALT + cancel pending orders. |
| max_capital_exposure_pct | 80% | Keeps cash for charges and avoids margin shortfall penalties. |
| max_open_positions | 2 | Concentration is unavoidable with ₹1,000; cap the count. |
| max_orders_per_session | 10 | Far below the 10 orders/second SEBI threshold; limits churn costs. |
| max_order_notional | ₹800 | No leverage. |
| max_spread_pct | 0.5% | Wider spreads make the stop/target maths meaningless. |
| max_data_age_seconds | 30 | Stale quote → reject. Intraday signals older than 120 s → reject. |
| max_consecutive_failures | 3 | Repeated rejections/API errors → HALT. |
| max_cost_to_risk_ratio | 0.5 | Round-trip costs may not exceed half the stop risk. |
| min_reward_cost_ratio | 3.0 | Expected move must be ≥3× costs. |
| allow_short / allow_derivatives / allow_option_buying | false | Unlimited or leveraged risk, or contracts unaffordable at ₹1,000. |
| allow_option_writing | false (cannot be enabled) | Naked writing has undefined risk; validation rejects `true`. |
| allowed_products | I, D | MTF (borrowed money) rejected by validation. |
| limit_price_buffer_pct | 0.2% | Marketable LIMIT orders (MARKET orders are not accepted via API since Apr 2026). |
| intraday_entry_cutoff / squareoff | 14:45 / 15:10 IST | Avoid broker auto square-off (₹75 + GST) and closing illiquidity. |

## What "NO TRADE" means
The engine returns NO TRADE when any of these is true: no real-data research verdict of CANDIDATE for that
strategy+instrument, unfavourable regime, STOCKSHIELD level HIGH, or any risk check fails. With ₹1,000 this
will be the most common outcome. That is correct behaviour.

## Practical arithmetic at ₹1,000
* Delivery (swing) round trip on ₹500 ≈ ₹72 → blocked by the cost filter. Swing strategies remain useful for
  research and for analysis-only alerts; they cannot trade economically until capital is far larger.
* Intraday round trip on ₹500 ≈ ₹1.36 → passes cost checks if the stop distance is wide enough, but a ₹20 risk
  budget with a ₹400 share allows ~1 share and a ~₹5–20 stop.
* Futures/options: lot value × price is far beyond ₹1,000 for almost every contract; the engine rejects rather than
  substituting a different instrument.

## Emergency controls
* `KILL_SWITCH.bat` / dashboard **EMERGENCY STOP**: state → HALTED, KILL file written, pending orders cancelled.
  **Positions are not closed.**
* Liquidation is a separate explicit action (`kill --flatten`, or the dashboard checkbox + button): marketable LIMIT
  sells for every long position. It crosses the spread, may fill partially or not at all in a fast market,
  realises P&L and incurs charges. If anything fails, exit manually in the Upstox app.
* Upstox also offers a broker-side Kill Switch per segment in its app/API — use it if this PC is unreachable.
