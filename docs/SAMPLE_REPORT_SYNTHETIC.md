# INDIA QUANT — Strategy research report (20261021_2131 IST)

> **SYNTHETIC TEST DATA.** These numbers come from a random-walk generator and exist only to exercise the software. They are NOT evidence about any strategy or market.

Capital ₹1,000; risk/trade 2.0%; slippage 5.0 bps/side; costs per Upstox published schedule (Oct 2026). Splits: 60% train / 20% validation / 20% test (chronological). Parameters chosen on train only.

## Bottom line

**No strategy passed all validation checks → the system recommends NO TRADE.**

## Summary

| instrument_key | strategy | verdict | trades_full | test_net_pnl | test_trades | test_maxdd | full_net_pnl | full_costs | skipped_unaffordable | skipped_cost_filter | flags |
|---|---|---|---|---|---|---|---|---|---|---|---|
| NSE_EQ/INE154A01025 | sma_crossover | NOT_TRADABLE_AT_THIS_CAPITAL | 0 | 0.0 | 0 | 0.0 | 0.0 |  | 0 | 19 | NO_TRADES_AFTER_AFFORDABILITY_AND_COST_FILTERS; TOO_FEW_TRADES (0 < 30); NON_POSITIVE_OUT_OF_SAMPLE; NON_POSITIVE_VALIDATION; PARAMETER_INSTABILITY (only 0% of grid profitable in train); COSTS_BLOCK_MOST_SIGNALS (19 signals failed the cost filter at capital ₹1,000); SYNTHETIC_DATA — results are a software test, not evidence |
| NSE_EQ/INE154A01025 | ema_adx_trend | NOT_TRADABLE_AT_THIS_CAPITAL | 0 | 0.0 | 0 | 0.0 | 0.0 |  | 0 | 69 | NO_TRADES_AFTER_AFFORDABILITY_AND_COST_FILTERS; TOO_FEW_TRADES (0 < 30); NON_POSITIVE_OUT_OF_SAMPLE; NON_POSITIVE_VALIDATION; PARAMETER_INSTABILITY (only 0% of grid profitable in train); COSTS_BLOCK_MOST_SIGNALS (69 signals failed the cost filter at capital ₹1,000); SYNTHETIC_DATA — results are a software test, not evidence |
| NSE_EQ/INE154A01025 | donchian_breakout | NOT_TRADABLE_AT_THIS_CAPITAL | 0 | 0.0 | 0 | 0.0 | 0.0 |  | 0 | 56 | NO_TRADES_AFTER_AFFORDABILITY_AND_COST_FILTERS; TOO_FEW_TRADES (0 < 30); NON_POSITIVE_OUT_OF_SAMPLE; NON_POSITIVE_VALIDATION; PARAMETER_INSTABILITY (only 0% of grid profitable in train); COSTS_BLOCK_MOST_SIGNALS (56 signals failed the cost filter at capital ₹1,000); SYNTHETIC_DATA — results are a software test, not evidence |
| NSE_EQ/INE154A01025 | relative_strength | NOT_TRADABLE_AT_THIS_CAPITAL | 0 | 0.0 | 0 | 0.0 | 0.0 |  | 0 | 38 | NO_TRADES_AFTER_AFFORDABILITY_AND_COST_FILTERS; TOO_FEW_TRADES (0 < 30); NON_POSITIVE_OUT_OF_SAMPLE; NON_POSITIVE_VALIDATION; PARAMETER_INSTABILITY (only 0% of grid profitable in train); COSTS_BLOCK_MOST_SIGNALS (38 signals failed the cost filter at capital ₹1,000); SYNTHETIC_DATA — results are a software test, not evidence |
| NSE_EQ/INE154A01025 | pullback_trend | NOT_TRADABLE_AT_THIS_CAPITAL | 0 | 0.0 | 0 | 0.0 | 0.0 |  | 0 | 27 | NO_TRADES_AFTER_AFFORDABILITY_AND_COST_FILTERS; TOO_FEW_TRADES (0 < 30); NON_POSITIVE_OUT_OF_SAMPLE; NON_POSITIVE_VALIDATION; PARAMETER_INSTABILITY (only 0% of grid profitable in train); COSTS_BLOCK_MOST_SIGNALS (27 signals failed the cost filter at capital ₹1,000); SYNTHETIC_DATA — results are a software test, not evidence |
| NSE_EQ/INE154A01025 | rsi_reversion | NO_SIGNALS | 0 | 0.0 | 0 | 0.0 | 0.0 |  | 0 | 0 | NO_TRADES_AFTER_AFFORDABILITY_AND_COST_FILTERS; TOO_FEW_TRADES (0 < 30); NON_POSITIVE_OUT_OF_SAMPLE; NON_POSITIVE_VALIDATION; PARAMETER_INSTABILITY (only 0% of grid profitable in train); SYNTHETIC_DATA — results are a software test, not evidence |
| NSE_EQ/INE154A01025 | bollinger_reversion | NOT_TRADABLE_AT_THIS_CAPITAL | 0 | 0.0 | 0 | 0.0 | 0.0 |  | 0 | 49 | NO_TRADES_AFTER_AFFORDABILITY_AND_COST_FILTERS; TOO_FEW_TRADES (0 < 30); NON_POSITIVE_OUT_OF_SAMPLE; NON_POSITIVE_VALIDATION; PARAMETER_INSTABILITY (only 0% of grid profitable in train); COSTS_BLOCK_MOST_SIGNALS (49 signals failed the cost filter at capital ₹1,000); SYNTHETIC_DATA — results are a software test, not evidence |
| NSE_EQ/INE154A01025 | zscore_reversion | NOT_TRADABLE_AT_THIS_CAPITAL | 0 | 0.0 | 0 | 0.0 | 0.0 |  | 0 | 73 | NO_TRADES_AFTER_AFFORDABILITY_AND_COST_FILTERS; TOO_FEW_TRADES (0 < 30); NON_POSITIVE_OUT_OF_SAMPLE; NON_POSITIVE_VALIDATION; PARAMETER_INSTABILITY (only 0% of grid profitable in train); COSTS_BLOCK_MOST_SIGNALS (73 signals failed the cost filter at capital ₹1,000); SYNTHETIC_DATA — results are a software test, not evidence |
| NSE_EQ/INE154A01025 | orb | REJECT | 22 | 12.18 | 4 | -0.0091 | -4.56 | 31.7 | 0 | 0 | TOO_FEW_TRADES (22 < 30); NON_POSITIVE_VALIDATION; EDGE_DISAPPEARS_AFTER_COSTS; PARAMETER_INSTABILITY (only 38% of grid profitable in train); EXPECTANCY_CI_INCLUDES_ZERO; SYNTHETIC_DATA — results are a software test, not evidence |
| NSE_EQ/INE154A01025 | vwap_reversion | NOT_TRADABLE_AT_THIS_CAPITAL | 0 | 0.0 | 0 | 0.0 | 0.0 |  | 0 | 203 | NO_TRADES_AFTER_AFFORDABILITY_AND_COST_FILTERS; TOO_FEW_TRADES (0 < 30); NON_POSITIVE_OUT_OF_SAMPLE; NON_POSITIVE_VALIDATION; PARAMETER_INSTABILITY (only 0% of grid profitable in train); COSTS_BLOCK_MOST_SIGNALS (203 signals failed the cost filter at capital ₹1,000); SYNTHETIC_DATA — results are a software test, not evidence |
| NSE_EQ/INE154A01025 | prev_day_breakout | REJECT | 1 | 0.0 | 0 | 0.0 | -0.56 | 1.48 | 0 | 11 | TOO_FEW_TRADES (1 < 30); NON_POSITIVE_OUT_OF_SAMPLE; NON_POSITIVE_VALIDATION; EDGE_DISAPPEARS_AFTER_COSTS; PARAMETER_INSTABILITY (only 0% of grid profitable in train); COSTS_BLOCK_MOST_SIGNALS (11 signals failed the cost filter at capital ₹1,000); SYNTHETIC_DATA — results are a software test, not evidence |
| NSE_EQ/INE062A01020 | sma_crossover | NOT_TRADABLE_AT_THIS_CAPITAL | 0 | 0.0 | 0 | 0.0 | 0.0 |  | 0 | 23 | NO_TRADES_AFTER_AFFORDABILITY_AND_COST_FILTERS; TOO_FEW_TRADES (0 < 30); NON_POSITIVE_OUT_OF_SAMPLE; NON_POSITIVE_VALIDATION; PARAMETER_INSTABILITY (only 0% of grid profitable in train); COSTS_BLOCK_MOST_SIGNALS (23 signals failed the cost filter at capital ₹1,000); SYNTHETIC_DATA — results are a software test, not evidence |
| NSE_EQ/INE062A01020 | ema_adx_trend | NOT_TRADABLE_AT_THIS_CAPITAL | 0 | 0.0 | 0 | 0.0 | 0.0 |  | 0 | 45 | NO_TRADES_AFTER_AFFORDABILITY_AND_COST_FILTERS; TOO_FEW_TRADES (0 < 30); NON_POSITIVE_OUT_OF_SAMPLE; NON_POSITIVE_VALIDATION; PARAMETER_INSTABILITY (only 0% of grid profitable in train); COSTS_BLOCK_MOST_SIGNALS (45 signals failed the cost filter at capital ₹1,000); SYNTHETIC_DATA — results are a software test, not evidence |
| NSE_EQ/INE062A01020 | donchian_breakout | NOT_TRADABLE_AT_THIS_CAPITAL | 0 | 0.0 | 0 | 0.0 | 0.0 |  | 0 | 36 | NO_TRADES_AFTER_AFFORDABILITY_AND_COST_FILTERS; TOO_FEW_TRADES (0 < 30); NON_POSITIVE_OUT_OF_SAMPLE; NON_POSITIVE_VALIDATION; PARAMETER_INSTABILITY (only 0% of grid profitable in train); COSTS_BLOCK_MOST_SIGNALS (36 signals failed the cost filter at capital ₹1,000); SYNTHETIC_DATA — results are a software test, not evidence |
| NSE_EQ/INE062A01020 | relative_strength | NOT_TRADABLE_AT_THIS_CAPITAL | 0 | 0.0 | 0 | 0.0 | 0.0 |  | 0 | 43 | NO_TRADES_AFTER_AFFORDABILITY_AND_COST_FILTERS; TOO_FEW_TRADES (0 < 30); NON_POSITIVE_OUT_OF_SAMPLE; NON_POSITIVE_VALIDATION; PARAMETER_INSTABILITY (only 0% of grid profitable in train); COSTS_BLOCK_MOST_SIGNALS (43 signals failed the cost filter at capital ₹1,000); SYNTHETIC_DATA — results are a software test, not evidence |
| NSE_EQ/INE062A01020 | pullback_trend | NOT_TRADABLE_AT_THIS_CAPITAL | 0 | 0.0 | 0 | 0.0 | 0.0 |  | 0 | 14 | NO_TRADES_AFTER_AFFORDABILITY_AND_COST_FILTERS; TOO_FEW_TRADES (0 < 30); NON_POSITIVE_OUT_OF_SAMPLE; NON_POSITIVE_VALIDATION; PARAMETER_INSTABILITY (only 0% of grid profitable in train); COSTS_BLOCK_MOST_SIGNALS (14 signals failed the cost filter at capital ₹1,000); SYNTHETIC_DATA — results are a software test, not evidence |
| NSE_EQ/INE062A01020 | rsi_reversion | NO_SIGNALS | 0 | 0.0 | 0 | 0.0 | 0.0 |  | 0 | 0 | NO_TRADES_AFTER_AFFORDABILITY_AND_COST_FILTERS; TOO_FEW_TRADES (0 < 30); NON_POSITIVE_OUT_OF_SAMPLE; NON_POSITIVE_VALIDATION; PARAMETER_INSTABILITY (only 0% of grid profitable in train); SYNTHETIC_DATA — results are a software test, not evidence |
| NSE_EQ/INE062A01020 | bollinger_reversion | NOT_TRADABLE_AT_THIS_CAPITAL | 0 | 0.0 | 0 | 0.0 | 0.0 |  | 0 | 50 | NO_TRADES_AFTER_AFFORDABILITY_AND_COST_FILTERS; TOO_FEW_TRADES (0 < 30); NON_POSITIVE_OUT_OF_SAMPLE; NON_POSITIVE_VALIDATION; PARAMETER_INSTABILITY (only 0% of grid profitable in train); COSTS_BLOCK_MOST_SIGNALS (50 signals failed the cost filter at capital ₹1,000); SYNTHETIC_DATA — results are a software test, not evidence |
| NSE_EQ/INE062A01020 | zscore_reversion | NOT_TRADABLE_AT_THIS_CAPITAL | 0 | 0.0 | 0 | 0.0 | 0.0 |  | 0 | 90 | NO_TRADES_AFTER_AFFORDABILITY_AND_COST_FILTERS; TOO_FEW_TRADES (0 < 30); NON_POSITIVE_OUT_OF_SAMPLE; NON_POSITIVE_VALIDATION; PARAMETER_INSTABILITY (only 0% of grid profitable in train); COSTS_BLOCK_MOST_SIGNALS (90 signals failed the cost filter at capital ₹1,000); SYNTHETIC_DATA — results are a software test, not evidence |
| NSE_EQ/INE062A01020 | orb | REJECT | 20 | -13.13 | 3 | -0.0131 | -51.39 | 24.83 | 0 | 0 | TOO_FEW_TRADES (20 < 30); NON_POSITIVE_OUT_OF_SAMPLE; NON_POSITIVE_VALIDATION; PARAMETER_INSTABILITY (only 0% of grid profitable in train); EXPECTANCY_CI_INCLUDES_ZERO; SYNTHETIC_DATA — results are a software test, not evidence |
| NSE_EQ/INE062A01020 | vwap_reversion | NOT_TRADABLE_AT_THIS_CAPITAL | 0 | 0.0 | 0 | 0.0 | 0.0 |  | 0 | 240 | NO_TRADES_AFTER_AFFORDABILITY_AND_COST_FILTERS; TOO_FEW_TRADES (0 < 30); NON_POSITIVE_OUT_OF_SAMPLE; NON_POSITIVE_VALIDATION; PARAMETER_INSTABILITY (only 0% of grid profitable in train); COSTS_BLOCK_MOST_SIGNALS (240 signals failed the cost filter at capital ₹1,000); SYNTHETIC_DATA — results are a software test, not evidence |
| NSE_EQ/INE062A01020 | prev_day_breakout | REJECT | 1 | 0.0 | 0 | 0.0 | -4.5 | 1.37 | 0 | 9 | TOO_FEW_TRADES (1 < 30); NON_POSITIVE_OUT_OF_SAMPLE; NON_POSITIVE_VALIDATION; PARAMETER_INSTABILITY (only 0% of grid profitable in train); COSTS_BLOCK_MOST_SIGNALS (9 signals failed the cost filter at capital ₹1,000); SYNTHETIC_DATA — results are a software test, not evidence |
| NSE_EQ/INE081A01020 | sma_crossover | NOT_TRADABLE_AT_THIS_CAPITAL | 0 | 0.0 | 0 | 0.0 | 0.0 |  | 0 | 18 | NO_TRADES_AFTER_AFFORDABILITY_AND_COST_FILTERS; TOO_FEW_TRADES (0 < 30); NON_POSITIVE_OUT_OF_SAMPLE; NON_POSITIVE_VALIDATION; PARAMETER_INSTABILITY (only 0% of grid profitable in train); COSTS_BLOCK_MOST_SIGNALS (18 signals failed the cost filter at capital ₹1,000); SYNTHETIC_DATA — results are a software test, not evidence |
| NSE_EQ/INE081A01020 | ema_adx_trend | NOT_TRADABLE_AT_THIS_CAPITAL | 0 | 0.0 | 0 | 0.0 | 0.0 |  | 0 | 35 | NO_TRADES_AFTER_AFFORDABILITY_AND_COST_FILTERS; TOO_FEW_TRADES (0 < 30); NON_POSITIVE_OUT_OF_SAMPLE; NON_POSITIVE_VALIDATION; PARAMETER_INSTABILITY (only 0% of grid profitable in train); COSTS_BLOCK_MOST_SIGNALS (35 signals failed the cost filter at capital ₹1,000); SYNTHETIC_DATA — results are a software test, not evidence |
| NSE_EQ/INE081A01020 | donchian_breakout | NOT_TRADABLE_AT_THIS_CAPITAL | 0 | 0.0 | 0 | 0.0 | 0.0 |  | 0 | 32 | NO_TRADES_AFTER_AFFORDABILITY_AND_COST_FILTERS; TOO_FEW_TRADES (0 < 30); NON_POSITIVE_OUT_OF_SAMPLE; NON_POSITIVE_VALIDATION; PARAMETER_INSTABILITY (only 0% of grid profitable in train); COSTS_BLOCK_MOST_SIGNALS (32 signals failed the cost filter at capital ₹1,000); SYNTHETIC_DATA — results are a software test, not evidence |
| NSE_EQ/INE081A01020 | relative_strength | NOT_TRADABLE_AT_THIS_CAPITAL | 0 | 0.0 | 0 | 0.0 | 0.0 |  | 0 | 56 | NO_TRADES_AFTER_AFFORDABILITY_AND_COST_FILTERS; TOO_FEW_TRADES (0 < 30); NON_POSITIVE_OUT_OF_SAMPLE; NON_POSITIVE_VALIDATION; PARAMETER_INSTABILITY (only 0% of grid profitable in train); COSTS_BLOCK_MOST_SIGNALS (56 signals failed the cost filter at capital ₹1,000); SYNTHETIC_DATA — results are a software test, not evidence |
| NSE_EQ/INE081A01020 | pullback_trend | NOT_TRADABLE_AT_THIS_CAPITAL | 0 | 0.0 | 0 | 0.0 | 0.0 |  | 0 | 15 | NO_TRADES_AFTER_AFFORDABILITY_AND_COST_FILTERS; TOO_FEW_TRADES (0 < 30); NON_POSITIVE_OUT_OF_SAMPLE; NON_POSITIVE_VALIDATION; PARAMETER_INSTABILITY (only 0% of grid profitable in train); COSTS_BLOCK_MOST_SIGNALS (15 signals failed the cost filter at capital ₹1,000); SYNTHETIC_DATA — results are a software test, not evidence |
| NSE_EQ/INE081A01020 | rsi_reversion | NO_SIGNALS | 0 | 0.0 | 0 | 0.0 | 0.0 |  | 0 | 0 | NO_TRADES_AFTER_AFFORDABILITY_AND_COST_FILTERS; TOO_FEW_TRADES (0 < 30); NON_POSITIVE_OUT_OF_SAMPLE; NON_POSITIVE_VALIDATION; PARAMETER_INSTABILITY (only 0% of grid profitable in train); SYNTHETIC_DATA — results are a software test, not evidence |
| NSE_EQ/INE081A01020 | bollinger_reversion | NOT_TRADABLE_AT_THIS_CAPITAL | 0 | 0.0 | 0 | 0.0 | 0.0 |  | 0 | 44 | NO_TRADES_AFTER_AFFORDABILITY_AND_COST_FILTERS; TOO_FEW_TRADES (0 < 30); NON_POSITIVE_OUT_OF_SAMPLE; NON_POSITIVE_VALIDATION; PARAMETER_INSTABILITY (only 0% of grid profitable in train); COSTS_BLOCK_MOST_SIGNALS (44 signals failed the cost filter at capital ₹1,000); SYNTHETIC_DATA — results are a software test, not evidence |
| NSE_EQ/INE081A01020 | zscore_reversion | NOT_TRADABLE_AT_THIS_CAPITAL | 0 | 0.0 | 0 | 0.0 | 0.0 |  | 0 | 98 | NO_TRADES_AFTER_AFFORDABILITY_AND_COST_FILTERS; TOO_FEW_TRADES (0 < 30); NON_POSITIVE_OUT_OF_SAMPLE; NON_POSITIVE_VALIDATION; PARAMETER_INSTABILITY (only 0% of grid profitable in train); COSTS_BLOCK_MOST_SIGNALS (98 signals failed the cost filter at capital ₹1,000); SYNTHETIC_DATA — results are a software test, not evidence |
| NSE_EQ/INE081A01020 | orb | INSUFFICIENT_EVIDENCE | 21 | 9.68 | 4 | -0.0097 | 17.94 | 31.62 | 0 | 0 | TOO_FEW_TRADES (21 < 30); PARAMETER_INSTABILITY (only 0% of grid profitable in train); EXPECTANCY_CI_INCLUDES_ZERO; SYNTHETIC_DATA — results are a software test, not evidence |
| NSE_EQ/INE081A01020 | vwap_reversion | NOT_TRADABLE_AT_THIS_CAPITAL | 0 | 0.0 | 0 | 0.0 | 0.0 |  | 0 | 178 | NO_TRADES_AFTER_AFFORDABILITY_AND_COST_FILTERS; TOO_FEW_TRADES (0 < 30); NON_POSITIVE_OUT_OF_SAMPLE; NON_POSITIVE_VALIDATION; PARAMETER_INSTABILITY (only 0% of grid profitable in train); COSTS_BLOCK_MOST_SIGNALS (178 signals failed the cost filter at capital ₹1,000); SYNTHETIC_DATA — results are a software test, not evidence |
| NSE_EQ/INE081A01020 | prev_day_breakout | REJECT | 1 | 0.0 | 0 | 0.0 | 1.45 | 1.63 | 0 | 16 | TOO_FEW_TRADES (1 < 30); NON_POSITIVE_OUT_OF_SAMPLE; PARAMETER_INSTABILITY (only 0% of grid profitable in train); COSTS_BLOCK_MOST_SIGNALS (16 signals failed the cost filter at capital ₹1,000); SYNTHETIC_DATA — results are a software test, not evidence |
| NSE_EQ/INE733E01010 | sma_crossover | NOT_TRADABLE_AT_THIS_CAPITAL | 0 | 0.0 | 0 | 0.0 | 0.0 |  | 0 | 24 | NO_TRADES_AFTER_AFFORDABILITY_AND_COST_FILTERS; TOO_FEW_TRADES (0 < 30); NON_POSITIVE_OUT_OF_SAMPLE; NON_POSITIVE_VALIDATION; PARAMETER_INSTABILITY (only 0% of grid profitable in train); COSTS_BLOCK_MOST_SIGNALS (24 signals failed the cost filter at capital ₹1,000); SYNTHETIC_DATA — results are a software test, not evidence |
| NSE_EQ/INE733E01010 | ema_adx_trend | NOT_TRADABLE_AT_THIS_CAPITAL | 0 | 0.0 | 0 | 0.0 | 0.0 |  | 0 | 77 | NO_TRADES_AFTER_AFFORDABILITY_AND_COST_FILTERS; TOO_FEW_TRADES (0 < 30); NON_POSITIVE_OUT_OF_SAMPLE; NON_POSITIVE_VALIDATION; PARAMETER_INSTABILITY (only 0% of grid profitable in train); COSTS_BLOCK_MOST_SIGNALS (77 signals failed the cost filter at capital ₹1,000); SYNTHETIC_DATA — results are a software test, not evidence |
| NSE_EQ/INE733E01010 | donchian_breakout | NOT_TRADABLE_AT_THIS_CAPITAL | 0 | 0.0 | 0 | 0.0 | 0.0 |  | 0 | 53 | NO_TRADES_AFTER_AFFORDABILITY_AND_COST_FILTERS; TOO_FEW_TRADES (0 < 30); NON_POSITIVE_OUT_OF_SAMPLE; NON_POSITIVE_VALIDATION; PARAMETER_INSTABILITY (only 0% of grid profitable in train); COSTS_BLOCK_MOST_SIGNALS (53 signals failed the cost filter at capital ₹1,000); SYNTHETIC_DATA — results are a software test, not evidence |
| NSE_EQ/INE733E01010 | relative_strength | NOT_TRADABLE_AT_THIS_CAPITAL | 0 | 0.0 | 0 | 0.0 | 0.0 |  | 3 | 62 | NO_TRADES_AFTER_AFFORDABILITY_AND_COST_FILTERS; TOO_FEW_TRADES (0 < 30); NON_POSITIVE_OUT_OF_SAMPLE; NON_POSITIVE_VALIDATION; PARAMETER_INSTABILITY (only 0% of grid profitable in train); COSTS_BLOCK_MOST_SIGNALS (62 signals failed the cost filter at capital ₹1,000); MOSTLY_UNAFFORDABLE (3 signals skipped at capital ₹1,000); SYNTHETIC_DATA — results are a software test, not evidence |
| NSE_EQ/INE733E01010 | pullback_trend | NOT_TRADABLE_AT_THIS_CAPITAL | 0 | 0.0 | 0 | 0.0 | 0.0 |  | 3 | 30 | NO_TRADES_AFTER_AFFORDABILITY_AND_COST_FILTERS; TOO_FEW_TRADES (0 < 30); NON_POSITIVE_OUT_OF_SAMPLE; NON_POSITIVE_VALIDATION; PARAMETER_INSTABILITY (only 0% of grid profitable in train); COSTS_BLOCK_MOST_SIGNALS (30 signals failed the cost filter at capital ₹1,000); MOSTLY_UNAFFORDABLE (3 signals skipped at capital ₹1,000); SYNTHETIC_DATA — results are a software test, not evidence |
| NSE_EQ/INE733E01010 | rsi_reversion | NO_SIGNALS | 0 | 0.0 | 0 | 0.0 | 0.0 |  | 0 | 0 | NO_TRADES_AFTER_AFFORDABILITY_AND_COST_FILTERS; TOO_FEW_TRADES (0 < 30); NON_POSITIVE_OUT_OF_SAMPLE; NON_POSITIVE_VALIDATION; PARAMETER_INSTABILITY (only 0% of grid profitable in train); SYNTHETIC_DATA — results are a software test, not evidence |
| NSE_EQ/INE733E01010 | bollinger_reversion | NOT_TRADABLE_AT_THIS_CAPITAL | 0 | 0.0 | 0 | 0.0 | 0.0 |  | 6 | 30 | NO_TRADES_AFTER_AFFORDABILITY_AND_COST_FILTERS; TOO_FEW_TRADES (0 < 30); NON_POSITIVE_OUT_OF_SAMPLE; NON_POSITIVE_VALIDATION; PARAMETER_INSTABILITY (only 0% of grid profitable in train); COSTS_BLOCK_MOST_SIGNALS (30 signals failed the cost filter at capital ₹1,000); MOSTLY_UNAFFORDABLE (6 signals skipped at capital ₹1,000); SYNTHETIC_DATA — results are a software test, not evidence |
| NSE_EQ/INE733E01010 | zscore_reversion | NOT_TRADABLE_AT_THIS_CAPITAL | 0 | 0.0 | 0 | 0.0 | 0.0 |  | 5 | 56 | NO_TRADES_AFTER_AFFORDABILITY_AND_COST_FILTERS; TOO_FEW_TRADES (0 < 30); NON_POSITIVE_OUT_OF_SAMPLE; NON_POSITIVE_VALIDATION; PARAMETER_INSTABILITY (only 0% of grid profitable in train); COSTS_BLOCK_MOST_SIGNALS (56 signals failed the cost filter at capital ₹1,000); MOSTLY_UNAFFORDABLE (5 signals skipped at capital ₹1,000); SYNTHETIC_DATA — results are a software test, not evidence |
| NSE_EQ/INE733E01010 | orb | REJECT | 23 | -20.45 | 6 | -0.0253 | -20.8 | 33.31 | 0 | 3 | TOO_FEW_TRADES (23 < 30); NON_POSITIVE_OUT_OF_SAMPLE; EDGE_DISAPPEARS_AFTER_COSTS; PARAMETER_INSTABILITY (only 0% of grid profitable in train); EXPECTANCY_CI_INCLUDES_ZERO; SYNTHETIC_DATA — results are a software test, not evidence |
| NSE_EQ/INE733E01010 | vwap_reversion | NOT_TRADABLE_AT_THIS_CAPITAL | 0 | 0.0 | 0 | 0.0 | 0.0 |  | 0 | 225 | NO_TRADES_AFTER_AFFORDABILITY_AND_COST_FILTERS; TOO_FEW_TRADES (0 < 30); NON_POSITIVE_OUT_OF_SAMPLE; NON_POSITIVE_VALIDATION; PARAMETER_INSTABILITY (only 0% of grid profitable in train); COSTS_BLOCK_MOST_SIGNALS (225 signals failed the cost filter at capital ₹1,000); SYNTHETIC_DATA — results are a software test, not evidence |
| NSE_EQ/INE733E01010 | prev_day_breakout | NOT_TRADABLE_AT_THIS_CAPITAL | 0 | 0.0 | 0 | 0.0 | 0.0 |  | 0 | 16 | NO_TRADES_AFTER_AFFORDABILITY_AND_COST_FILTERS; TOO_FEW_TRADES (0 < 30); NON_POSITIVE_OUT_OF_SAMPLE; NON_POSITIVE_VALIDATION; PARAMETER_INSTABILITY (only 0% of grid profitable in train); COSTS_BLOCK_MOST_SIGNALS (16 signals failed the cost filter at capital ₹1,000); SYNTHETIC_DATA — results are a software test, not evidence |
| NSE_EQ/INE213A01029 | sma_crossover | NOT_TRADABLE_AT_THIS_CAPITAL | 0 | 0.0 | 0 | 0.0 | 0.0 |  | 0 | 19 | NO_TRADES_AFTER_AFFORDABILITY_AND_COST_FILTERS; TOO_FEW_TRADES (0 < 30); NON_POSITIVE_OUT_OF_SAMPLE; NON_POSITIVE_VALIDATION; PARAMETER_INSTABILITY (only 0% of grid profitable in train); COSTS_BLOCK_MOST_SIGNALS (19 signals failed the cost filter at capital ₹1,000); SYNTHETIC_DATA — results are a software test, not evidence |
| NSE_EQ/INE213A01029 | ema_adx_trend | NOT_TRADABLE_AT_THIS_CAPITAL | 0 | 0.0 | 0 | 0.0 | 0.0 |  | 0 | 59 | NO_TRADES_AFTER_AFFORDABILITY_AND_COST_FILTERS; TOO_FEW_TRADES (0 < 30); NON_POSITIVE_OUT_OF_SAMPLE; NON_POSITIVE_VALIDATION; PARAMETER_INSTABILITY (only 0% of grid profitable in train); COSTS_BLOCK_MOST_SIGNALS (59 signals failed the cost filter at capital ₹1,000); SYNTHETIC_DATA — results are a software test, not evidence |
| NSE_EQ/INE213A01029 | donchian_breakout | NOT_TRADABLE_AT_THIS_CAPITAL | 0 | 0.0 | 0 | 0.0 | 0.0 |  | 0 | 51 | NO_TRADES_AFTER_AFFORDABILITY_AND_COST_FILTERS; TOO_FEW_TRADES (0 < 30); NON_POSITIVE_OUT_OF_SAMPLE; NON_POSITIVE_VALIDATION; PARAMETER_INSTABILITY (only 0% of grid profitable in train); COSTS_BLOCK_MOST_SIGNALS (51 signals failed the cost filter at capital ₹1,000); SYNTHETIC_DATA — results are a software test, not evidence |
| NSE_EQ/INE213A01029 | relative_strength | NOT_TRADABLE_AT_THIS_CAPITAL | 0 | 0.0 | 0 | 0.0 | 0.0 |  | 0 | 60 | NO_TRADES_AFTER_AFFORDABILITY_AND_COST_FILTERS; TOO_FEW_TRADES (0 < 30); NON_POSITIVE_OUT_OF_SAMPLE; NON_POSITIVE_VALIDATION; PARAMETER_INSTABILITY (only 0% of grid profitable in train); COSTS_BLOCK_MOST_SIGNALS (60 signals failed the cost filter at capital ₹1,000); SYNTHETIC_DATA — results are a software test, not evidence |
| NSE_EQ/INE213A01029 | pullback_trend | NOT_TRADABLE_AT_THIS_CAPITAL | 0 | 0.0 | 0 | 0.0 | 0.0 |  | 0 | 21 | NO_TRADES_AFTER_AFFORDABILITY_AND_COST_FILTERS; TOO_FEW_TRADES (0 < 30); NON_POSITIVE_OUT_OF_SAMPLE; NON_POSITIVE_VALIDATION; PARAMETER_INSTABILITY (only 0% of grid profitable in train); COSTS_BLOCK_MOST_SIGNALS (21 signals failed the cost filter at capital ₹1,000); SYNTHETIC_DATA — results are a software test, not evidence |
| NSE_EQ/INE213A01029 | rsi_reversion | NO_SIGNALS | 0 | 0.0 | 0 | 0.0 | 0.0 |  | 0 | 0 | NO_TRADES_AFTER_AFFORDABILITY_AND_COST_FILTERS; TOO_FEW_TRADES (0 < 30); NON_POSITIVE_OUT_OF_SAMPLE; NON_POSITIVE_VALIDATION; PARAMETER_INSTABILITY (only 0% of grid profitable in train); SYNTHETIC_DATA — results are a software test, not evidence |
| NSE_EQ/INE213A01029 | bollinger_reversion | NOT_TRADABLE_AT_THIS_CAPITAL | 0 | 0.0 | 0 | 0.0 | 0.0 |  | 0 | 40 | NO_TRADES_AFTER_AFFORDABILITY_AND_COST_FILTERS; TOO_FEW_TRADES (0 < 30); NON_POSITIVE_OUT_OF_SAMPLE; NON_POSITIVE_VALIDATION; PARAMETER_INSTABILITY (only 0% of grid profitable in train); COSTS_BLOCK_MOST_SIGNALS (40 signals failed the cost filter at capital ₹1,000); SYNTHETIC_DATA — results are a software test, not evidence |
| NSE_EQ/INE213A01029 | zscore_reversion | NOT_TRADABLE_AT_THIS_CAPITAL | 0 | 0.0 | 0 | 0.0 | 0.0 |  | 0 | 72 | NO_TRADES_AFTER_AFFORDABILITY_AND_COST_FILTERS; TOO_FEW_TRADES (0 < 30); NON_POSITIVE_OUT_OF_SAMPLE; NON_POSITIVE_VALIDATION; PARAMETER_INSTABILITY (only 0% of grid profitable in train); COSTS_BLOCK_MOST_SIGNALS (72 signals failed the cost filter at capital ₹1,000); SYNTHETIC_DATA — results are a software test, not evidence |
| NSE_EQ/INE213A01029 | orb | REJECT | 24 | -12.34 | 5 | -0.0196 | -17.52 | 38.42 | 0 | 0 | TOO_FEW_TRADES (24 < 30); NON_POSITIVE_OUT_OF_SAMPLE; NON_POSITIVE_VALIDATION; EDGE_DISAPPEARS_AFTER_COSTS; PARAMETER_INSTABILITY (only 12% of grid profitable in train); EXPECTANCY_CI_INCLUDES_ZERO; SYNTHETIC_DATA — results are a software test, not evidence |
| NSE_EQ/INE213A01029 | vwap_reversion | NOT_TRADABLE_AT_THIS_CAPITAL | 0 | 0.0 | 0 | 0.0 | 0.0 |  | 0 | 180 | NO_TRADES_AFTER_AFFORDABILITY_AND_COST_FILTERS; TOO_FEW_TRADES (0 < 30); NON_POSITIVE_OUT_OF_SAMPLE; NON_POSITIVE_VALIDATION; PARAMETER_INSTABILITY (only 0% of grid profitable in train); COSTS_BLOCK_MOST_SIGNALS (180 signals failed the cost filter at capital ₹1,000); SYNTHETIC_DATA — results are a software test, not evidence |
| NSE_EQ/INE213A01029 | prev_day_breakout | NOT_TRADABLE_AT_THIS_CAPITAL | 0 | 0.0 | 0 | 0.0 | 0.0 |  | 0 | 17 | NO_TRADES_AFTER_AFFORDABILITY_AND_COST_FILTERS; TOO_FEW_TRADES (0 < 30); NON_POSITIVE_OUT_OF_SAMPLE; NON_POSITIVE_VALIDATION; COSTS_BLOCK_MOST_SIGNALS (17 signals failed the cost filter at capital ₹1,000); SYNTHETIC_DATA — results are a software test, not evidence |
| NSE_EQ/INE522F01014 | sma_crossover | NOT_TRADABLE_AT_THIS_CAPITAL | 0 | 0.0 | 0 | 0.0 | 0.0 |  | 0 | 21 | NO_TRADES_AFTER_AFFORDABILITY_AND_COST_FILTERS; TOO_FEW_TRADES (0 < 30); NON_POSITIVE_OUT_OF_SAMPLE; NON_POSITIVE_VALIDATION; PARAMETER_INSTABILITY (only 0% of grid profitable in train); COSTS_BLOCK_MOST_SIGNALS (21 signals failed the cost filter at capital ₹1,000); SYNTHETIC_DATA — results are a software test, not evidence |
| NSE_EQ/INE522F01014 | ema_adx_trend | NOT_TRADABLE_AT_THIS_CAPITAL | 0 | 0.0 | 0 | 0.0 | 0.0 |  | 0 | 66 | NO_TRADES_AFTER_AFFORDABILITY_AND_COST_FILTERS; TOO_FEW_TRADES (0 < 30); NON_POSITIVE_OUT_OF_SAMPLE; NON_POSITIVE_VALIDATION; PARAMETER_INSTABILITY (only 0% of grid profitable in train); COSTS_BLOCK_MOST_SIGNALS (66 signals failed the cost filter at capital ₹1,000); SYNTHETIC_DATA — results are a software test, not evidence |
| NSE_EQ/INE522F01014 | donchian_breakout | NOT_TRADABLE_AT_THIS_CAPITAL | 0 | 0.0 | 0 | 0.0 | 0.0 |  | 0 | 60 | NO_TRADES_AFTER_AFFORDABILITY_AND_COST_FILTERS; TOO_FEW_TRADES (0 < 30); NON_POSITIVE_OUT_OF_SAMPLE; NON_POSITIVE_VALIDATION; PARAMETER_INSTABILITY (only 0% of grid profitable in train); COSTS_BLOCK_MOST_SIGNALS (60 signals failed the cost filter at capital ₹1,000); SYNTHETIC_DATA — results are a software test, not evidence |
| NSE_EQ/INE522F01014 | relative_strength | NOT_TRADABLE_AT_THIS_CAPITAL | 0 | 0.0 | 0 | 0.0 | 0.0 |  | 0 | 36 | NO_TRADES_AFTER_AFFORDABILITY_AND_COST_FILTERS; TOO_FEW_TRADES (0 < 30); NON_POSITIVE_OUT_OF_SAMPLE; NON_POSITIVE_VALIDATION; PARAMETER_INSTABILITY (only 0% of grid profitable in train); COSTS_BLOCK_MOST_SIGNALS (36 signals failed the cost filter at capital ₹1,000); SYNTHETIC_DATA — results are a software test, not evidence |
| NSE_EQ/INE522F01014 | pullback_trend | NOT_TRADABLE_AT_THIS_CAPITAL | 0 | 0.0 | 0 | 0.0 | 0.0 |  | 6 | 34 | NO_TRADES_AFTER_AFFORDABILITY_AND_COST_FILTERS; TOO_FEW_TRADES (0 < 30); NON_POSITIVE_OUT_OF_SAMPLE; NON_POSITIVE_VALIDATION; PARAMETER_INSTABILITY (only 0% of grid profitable in train); COSTS_BLOCK_MOST_SIGNALS (34 signals failed the cost filter at capital ₹1,000); MOSTLY_UNAFFORDABLE (6 signals skipped at capital ₹1,000); SYNTHETIC_DATA — results are a software test, not evidence |
| NSE_EQ/INE522F01014 | rsi_reversion | NO_SIGNALS | 0 | 0.0 | 0 | 0.0 | 0.0 |  | 0 | 0 | NO_TRADES_AFTER_AFFORDABILITY_AND_COST_FILTERS; TOO_FEW_TRADES (0 < 30); NON_POSITIVE_OUT_OF_SAMPLE; NON_POSITIVE_VALIDATION; PARAMETER_INSTABILITY (only 0% of grid profitable in train); SYNTHETIC_DATA — results are a software test, not evidence |
| NSE_EQ/INE522F01014 | bollinger_reversion | NOT_TRADABLE_AT_THIS_CAPITAL | 0 | 0.0 | 0 | 0.0 | 0.0 |  | 1 | 33 | NO_TRADES_AFTER_AFFORDABILITY_AND_COST_FILTERS; TOO_FEW_TRADES (0 < 30); NON_POSITIVE_OUT_OF_SAMPLE; NON_POSITIVE_VALIDATION; PARAMETER_INSTABILITY (only 0% of grid profitable in train); COSTS_BLOCK_MOST_SIGNALS (33 signals failed the cost filter at capital ₹1,000); MOSTLY_UNAFFORDABLE (1 signals skipped at capital ₹1,000); SYNTHETIC_DATA — results are a software test, not evidence |
| NSE_EQ/INE522F01014 | zscore_reversion | NOT_TRADABLE_AT_THIS_CAPITAL | 0 | 0.0 | 0 | 0.0 | 0.0 |  | 0 | 57 | NO_TRADES_AFTER_AFFORDABILITY_AND_COST_FILTERS; TOO_FEW_TRADES (0 < 30); NON_POSITIVE_OUT_OF_SAMPLE; NON_POSITIVE_VALIDATION; PARAMETER_INSTABILITY (only 0% of grid profitable in train); COSTS_BLOCK_MOST_SIGNALS (57 signals failed the cost filter at capital ₹1,000); SYNTHETIC_DATA — results are a software test, not evidence |
| NSE_EQ/INE522F01014 | orb | REJECT | 23 | 1.96 | 4 | -0.0094 | -21.05 | 34.25 | 0 | 0 | TOO_FEW_TRADES (23 < 30); NON_POSITIVE_VALIDATION; EDGE_DISAPPEARS_AFTER_COSTS; PARAMETER_INSTABILITY (only 0% of grid profitable in train); EXPECTANCY_CI_INCLUDES_ZERO; SYNTHETIC_DATA — results are a software test, not evidence |
| NSE_EQ/INE522F01014 | vwap_reversion | NOT_TRADABLE_AT_THIS_CAPITAL | 0 | 0.0 | 0 | 0.0 | 0.0 |  | 0 | 232 | NO_TRADES_AFTER_AFFORDABILITY_AND_COST_FILTERS; TOO_FEW_TRADES (0 < 30); NON_POSITIVE_OUT_OF_SAMPLE; NON_POSITIVE_VALIDATION; PARAMETER_INSTABILITY (only 0% of grid profitable in train); COSTS_BLOCK_MOST_SIGNALS (232 signals failed the cost filter at capital ₹1,000); SYNTHETIC_DATA — results are a software test, not evidence |
| NSE_EQ/INE522F01014 | prev_day_breakout | REJECT | 2 | 0.0 | 0 | 0.0 | -5.12 | 2.96 | 0 | 15 | TOO_FEW_TRADES (2 < 30); NON_POSITIVE_OUT_OF_SAMPLE; NON_POSITIVE_VALIDATION; PARAMETER_INSTABILITY (only 0% of grid profitable in train); COSTS_BLOCK_MOST_SIGNALS (15 signals failed the cost filter at capital ₹1,000); SYNTHETIC_DATA — results are a software test, not evidence |
| NSE_EQ/INE263A01024 | sma_crossover | NOT_TRADABLE_AT_THIS_CAPITAL | 0 | 0.0 | 0 | 0.0 | 0.0 |  | 0 | 20 | NO_TRADES_AFTER_AFFORDABILITY_AND_COST_FILTERS; TOO_FEW_TRADES (0 < 30); NON_POSITIVE_OUT_OF_SAMPLE; NON_POSITIVE_VALIDATION; PARAMETER_INSTABILITY (only 0% of grid profitable in train); COSTS_BLOCK_MOST_SIGNALS (20 signals failed the cost filter at capital ₹1,000); SYNTHETIC_DATA — results are a software test, not evidence |
| NSE_EQ/INE263A01024 | ema_adx_trend | NOT_TRADABLE_AT_THIS_CAPITAL | 0 | 0.0 | 0 | 0.0 | 0.0 |  | 0 | 52 | NO_TRADES_AFTER_AFFORDABILITY_AND_COST_FILTERS; TOO_FEW_TRADES (0 < 30); NON_POSITIVE_OUT_OF_SAMPLE; NON_POSITIVE_VALIDATION; PARAMETER_INSTABILITY (only 0% of grid profitable in train); COSTS_BLOCK_MOST_SIGNALS (52 signals failed the cost filter at capital ₹1,000); SYNTHETIC_DATA — results are a software test, not evidence |
| NSE_EQ/INE263A01024 | donchian_breakout | NOT_TRADABLE_AT_THIS_CAPITAL | 0 | 0.0 | 0 | 0.0 | 0.0 |  | 0 | 54 | NO_TRADES_AFTER_AFFORDABILITY_AND_COST_FILTERS; TOO_FEW_TRADES (0 < 30); NON_POSITIVE_OUT_OF_SAMPLE; NON_POSITIVE_VALIDATION; PARAMETER_INSTABILITY (only 0% of grid profitable in train); COSTS_BLOCK_MOST_SIGNALS (54 signals failed the cost filter at capital ₹1,000); SYNTHETIC_DATA — results are a software test, not evidence |
| NSE_EQ/INE263A01024 | relative_strength | NOT_TRADABLE_AT_THIS_CAPITAL | 0 | 0.0 | 0 | 0.0 | 0.0 |  | 0 | 54 | NO_TRADES_AFTER_AFFORDABILITY_AND_COST_FILTERS; TOO_FEW_TRADES (0 < 30); NON_POSITIVE_OUT_OF_SAMPLE; NON_POSITIVE_VALIDATION; PARAMETER_INSTABILITY (only 0% of grid profitable in train); COSTS_BLOCK_MOST_SIGNALS (54 signals failed the cost filter at capital ₹1,000); SYNTHETIC_DATA — results are a software test, not evidence |
| NSE_EQ/INE263A01024 | pullback_trend | NOT_TRADABLE_AT_THIS_CAPITAL | 0 | 0.0 | 0 | 0.0 | 0.0 |  | 0 | 20 | NO_TRADES_AFTER_AFFORDABILITY_AND_COST_FILTERS; TOO_FEW_TRADES (0 < 30); NON_POSITIVE_OUT_OF_SAMPLE; NON_POSITIVE_VALIDATION; PARAMETER_INSTABILITY (only 0% of grid profitable in train); COSTS_BLOCK_MOST_SIGNALS (20 signals failed the cost filter at capital ₹1,000); SYNTHETIC_DATA — results are a software test, not evidence |
| NSE_EQ/INE263A01024 | rsi_reversion | NO_SIGNALS | 0 | 0.0 | 0 | 0.0 | 0.0 |  | 0 | 0 | NO_TRADES_AFTER_AFFORDABILITY_AND_COST_FILTERS; TOO_FEW_TRADES (0 < 30); NON_POSITIVE_OUT_OF_SAMPLE; NON_POSITIVE_VALIDATION; PARAMETER_INSTABILITY (only 0% of grid profitable in train); SYNTHETIC_DATA — results are a software test, not evidence |
| NSE_EQ/INE263A01024 | bollinger_reversion | NOT_TRADABLE_AT_THIS_CAPITAL | 0 | 0.0 | 0 | 0.0 | 0.0 |  | 0 | 31 | NO_TRADES_AFTER_AFFORDABILITY_AND_COST_FILTERS; TOO_FEW_TRADES (0 < 30); NON_POSITIVE_OUT_OF_SAMPLE; NON_POSITIVE_VALIDATION; PARAMETER_INSTABILITY (only 0% of grid profitable in train); COSTS_BLOCK_MOST_SIGNALS (31 signals failed the cost filter at capital ₹1,000); SYNTHETIC_DATA — results are a software test, not evidence |
| NSE_EQ/INE263A01024 | zscore_reversion | NOT_TRADABLE_AT_THIS_CAPITAL | 0 | 0.0 | 0 | 0.0 | 0.0 |  | 0 | 65 | NO_TRADES_AFTER_AFFORDABILITY_AND_COST_FILTERS; TOO_FEW_TRADES (0 < 30); NON_POSITIVE_OUT_OF_SAMPLE; NON_POSITIVE_VALIDATION; PARAMETER_INSTABILITY (only 0% of grid profitable in train); COSTS_BLOCK_MOST_SIGNALS (65 signals failed the cost filter at capital ₹1,000); SYNTHETIC_DATA — results are a software test, not evidence |
| NSE_EQ/INE263A01024 | orb | REJECT | 24 | -11.48 | 6 | -0.0181 | -24.65 | 34.16 | 0 | 2 | TOO_FEW_TRADES (24 < 30); NON_POSITIVE_OUT_OF_SAMPLE; EDGE_DISAPPEARS_AFTER_COSTS; PARAMETER_INSTABILITY (only 0% of grid profitable in train); EXPECTANCY_CI_INCLUDES_ZERO; SYNTHETIC_DATA — results are a software test, not evidence |
| NSE_EQ/INE263A01024 | vwap_reversion | NOT_TRADABLE_AT_THIS_CAPITAL | 0 | 0.0 | 0 | 0.0 | 0.0 |  | 0 | 185 | NO_TRADES_AFTER_AFFORDABILITY_AND_COST_FILTERS; TOO_FEW_TRADES (0 < 30); NON_POSITIVE_OUT_OF_SAMPLE; NON_POSITIVE_VALIDATION; PARAMETER_INSTABILITY (only 0% of grid profitable in train); COSTS_BLOCK_MOST_SIGNALS (185 signals failed the cost filter at capital ₹1,000); SYNTHETIC_DATA — results are a software test, not evidence |
| NSE_EQ/INE263A01024 | prev_day_breakout | NOT_TRADABLE_AT_THIS_CAPITAL | 0 | 0.0 | 0 | 0.0 | 0.0 |  | 0 | 14 | NO_TRADES_AFTER_AFFORDABILITY_AND_COST_FILTERS; TOO_FEW_TRADES (0 < 30); NON_POSITIVE_OUT_OF_SAMPLE; NON_POSITIVE_VALIDATION; PARAMETER_INSTABILITY (only 0% of grid profitable in train); COSTS_BLOCK_MOST_SIGNALS (14 signals failed the cost filter at capital ₹1,000); SYNTHETIC_DATA — results are a software test, not evidence |
| NSE_EQ/INE242A01010 | sma_crossover | NOT_TRADABLE_AT_THIS_CAPITAL | 0 | 0.0 | 0 | 0.0 | 0.0 |  | 0 | 17 | NO_TRADES_AFTER_AFFORDABILITY_AND_COST_FILTERS; TOO_FEW_TRADES (0 < 30); NON_POSITIVE_OUT_OF_SAMPLE; NON_POSITIVE_VALIDATION; PARAMETER_INSTABILITY (only 0% of grid profitable in train); COSTS_BLOCK_MOST_SIGNALS (17 signals failed the cost filter at capital ₹1,000); SYNTHETIC_DATA — results are a software test, not evidence |
| NSE_EQ/INE242A01010 | ema_adx_trend | NOT_TRADABLE_AT_THIS_CAPITAL | 0 | 0.0 | 0 | 0.0 | 0.0 |  | 0 | 47 | NO_TRADES_AFTER_AFFORDABILITY_AND_COST_FILTERS; TOO_FEW_TRADES (0 < 30); NON_POSITIVE_OUT_OF_SAMPLE; NON_POSITIVE_VALIDATION; PARAMETER_INSTABILITY (only 0% of grid profitable in train); COSTS_BLOCK_MOST_SIGNALS (47 signals failed the cost filter at capital ₹1,000); SYNTHETIC_DATA — results are a software test, not evidence |
| NSE_EQ/INE242A01010 | donchian_breakout | NOT_TRADABLE_AT_THIS_CAPITAL | 0 | 0.0 | 0 | 0.0 | 0.0 |  | 0 | 33 | NO_TRADES_AFTER_AFFORDABILITY_AND_COST_FILTERS; TOO_FEW_TRADES (0 < 30); NON_POSITIVE_OUT_OF_SAMPLE; NON_POSITIVE_VALIDATION; PARAMETER_INSTABILITY (only 0% of grid profitable in train); COSTS_BLOCK_MOST_SIGNALS (33 signals failed the cost filter at capital ₹1,000); SYNTHETIC_DATA — results are a software test, not evidence |
| NSE_EQ/INE242A01010 | relative_strength | NOT_TRADABLE_AT_THIS_CAPITAL | 0 | 0.0 | 0 | 0.0 | 0.0 |  | 0 | 45 | NO_TRADES_AFTER_AFFORDABILITY_AND_COST_FILTERS; TOO_FEW_TRADES (0 < 30); NON_POSITIVE_OUT_OF_SAMPLE; NON_POSITIVE_VALIDATION; PARAMETER_INSTABILITY (only 0% of grid profitable in train); COSTS_BLOCK_MOST_SIGNALS (45 signals failed the cost filter at capital ₹1,000); SYNTHETIC_DATA — results are a software test, not evidence |
| NSE_EQ/INE242A01010 | pullback_trend | NOT_TRADABLE_AT_THIS_CAPITAL | 0 | 0.0 | 0 | 0.0 | 0.0 |  | 0 | 16 | NO_TRADES_AFTER_AFFORDABILITY_AND_COST_FILTERS; TOO_FEW_TRADES (0 < 30); NON_POSITIVE_OUT_OF_SAMPLE; NON_POSITIVE_VALIDATION; PARAMETER_INSTABILITY (only 0% of grid profitable in train); COSTS_BLOCK_MOST_SIGNALS (16 signals failed the cost filter at capital ₹1,000); SYNTHETIC_DATA — results are a software test, not evidence |
| NSE_EQ/INE242A01010 | rsi_reversion | NOT_TRADABLE_AT_THIS_CAPITAL | 0 | 0.0 | 0 | 0.0 | 0.0 |  | 0 | 1 | NO_TRADES_AFTER_AFFORDABILITY_AND_COST_FILTERS; TOO_FEW_TRADES (0 < 30); NON_POSITIVE_OUT_OF_SAMPLE; NON_POSITIVE_VALIDATION; PARAMETER_INSTABILITY (only 0% of grid profitable in train); COSTS_BLOCK_MOST_SIGNALS (1 signals failed the cost filter at capital ₹1,000); SYNTHETIC_DATA — results are a software test, not evidence |
| NSE_EQ/INE242A01010 | bollinger_reversion | NOT_TRADABLE_AT_THIS_CAPITAL | 0 | 0.0 | 0 | 0.0 | 0.0 |  | 0 | 40 | NO_TRADES_AFTER_AFFORDABILITY_AND_COST_FILTERS; TOO_FEW_TRADES (0 < 30); NON_POSITIVE_OUT_OF_SAMPLE; NON_POSITIVE_VALIDATION; PARAMETER_INSTABILITY (only 0% of grid profitable in train); COSTS_BLOCK_MOST_SIGNALS (40 signals failed the cost filter at capital ₹1,000); SYNTHETIC_DATA — results are a software test, not evidence |
| NSE_EQ/INE242A01010 | zscore_reversion | NOT_TRADABLE_AT_THIS_CAPITAL | 0 | 0.0 | 0 | 0.0 | 0.0 |  | 0 | 88 | NO_TRADES_AFTER_AFFORDABILITY_AND_COST_FILTERS; TOO_FEW_TRADES (0 < 30); NON_POSITIVE_OUT_OF_SAMPLE; NON_POSITIVE_VALIDATION; PARAMETER_INSTABILITY (only 0% of grid profitable in train); COSTS_BLOCK_MOST_SIGNALS (88 signals failed the cost filter at capital ₹1,000); SYNTHETIC_DATA — results are a software test, not evidence |
| NSE_EQ/INE242A01010 | orb | REJECT | 17 | -9.09 | 2 | -0.0091 | 2.67 | 21.57 | 0 | 0 | TOO_FEW_TRADES (17 < 30); NON_POSITIVE_OUT_OF_SAMPLE; PARAMETER_INSTABILITY (only 12% of grid profitable in train); EXPECTANCY_CI_INCLUDES_ZERO; SYNTHETIC_DATA — results are a software test, not evidence |
| NSE_EQ/INE242A01010 | vwap_reversion | NOT_TRADABLE_AT_THIS_CAPITAL | 0 | 0.0 | 0 | 0.0 | 0.0 |  | 0 | 193 | NO_TRADES_AFTER_AFFORDABILITY_AND_COST_FILTERS; TOO_FEW_TRADES (0 < 30); NON_POSITIVE_OUT_OF_SAMPLE; NON_POSITIVE_VALIDATION; PARAMETER_INSTABILITY (only 0% of grid profitable in train); COSTS_BLOCK_MOST_SIGNALS (193 signals failed the cost filter at capital ₹1,000); SYNTHETIC_DATA — results are a software test, not evidence |
| NSE_EQ/INE242A01010 | prev_day_breakout | REJECT | 1 | 0.0 | 0 | 0.0 | -1.5 | 1.36 | 0 | 9 | TOO_FEW_TRADES (1 < 30); NON_POSITIVE_OUT_OF_SAMPLE; NON_POSITIVE_VALIDATION; PARAMETER_INSTABILITY (only 0% of grid profitable in train); COSTS_BLOCK_MOST_SIGNALS (9 signals failed the cost filter at capital ₹1,000); SYNTHETIC_DATA — results are a software test, not evidence |
| NSE_EQ/INE009A01021 | sma_crossover | NOT_TRADABLE_AT_THIS_CAPITAL | 0 | 0.0 | 0 | 0.0 | 0.0 |  | 0 | 18 | NO_TRADES_AFTER_AFFORDABILITY_AND_COST_FILTERS; TOO_FEW_TRADES (0 < 30); NON_POSITIVE_OUT_OF_SAMPLE; NON_POSITIVE_VALIDATION; PARAMETER_INSTABILITY (only 0% of grid profitable in train); COSTS_BLOCK_MOST_SIGNALS (18 signals failed the cost filter at capital ₹1,000); SYNTHETIC_DATA — results are a software test, not evidence |
| NSE_EQ/INE009A01021 | ema_adx_trend | NOT_TRADABLE_AT_THIS_CAPITAL | 0 | 0.0 | 0 | 0.0 | 0.0 |  | 0 | 48 | NO_TRADES_AFTER_AFFORDABILITY_AND_COST_FILTERS; TOO_FEW_TRADES (0 < 30); NON_POSITIVE_OUT_OF_SAMPLE; NON_POSITIVE_VALIDATION; PARAMETER_INSTABILITY (only 0% of grid profitable in train); COSTS_BLOCK_MOST_SIGNALS (48 signals failed the cost filter at capital ₹1,000); SYNTHETIC_DATA — results are a software test, not evidence |
| NSE_EQ/INE009A01021 | donchian_breakout | NOT_TRADABLE_AT_THIS_CAPITAL | 0 | 0.0 | 0 | 0.0 | 0.0 |  | 0 | 47 | NO_TRADES_AFTER_AFFORDABILITY_AND_COST_FILTERS; TOO_FEW_TRADES (0 < 30); NON_POSITIVE_OUT_OF_SAMPLE; NON_POSITIVE_VALIDATION; PARAMETER_INSTABILITY (only 0% of grid profitable in train); COSTS_BLOCK_MOST_SIGNALS (47 signals failed the cost filter at capital ₹1,000); SYNTHETIC_DATA — results are a software test, not evidence |
| NSE_EQ/INE009A01021 | relative_strength | NOT_TRADABLE_AT_THIS_CAPITAL | 0 | 0.0 | 0 | 0.0 | 0.0 |  | 0 | 49 | NO_TRADES_AFTER_AFFORDABILITY_AND_COST_FILTERS; TOO_FEW_TRADES (0 < 30); NON_POSITIVE_OUT_OF_SAMPLE; NON_POSITIVE_VALIDATION; PARAMETER_INSTABILITY (only 0% of grid profitable in train); COSTS_BLOCK_MOST_SIGNALS (49 signals failed the cost filter at capital ₹1,000); SYNTHETIC_DATA — results are a software test, not evidence |
| NSE_EQ/INE009A01021 | pullback_trend | NOT_TRADABLE_AT_THIS_CAPITAL | 0 | 0.0 | 0 | 0.0 | 0.0 |  | 0 | 16 | NO_TRADES_AFTER_AFFORDABILITY_AND_COST_FILTERS; TOO_FEW_TRADES (0 < 30); NON_POSITIVE_OUT_OF_SAMPLE; NON_POSITIVE_VALIDATION; PARAMETER_INSTABILITY (only 0% of grid profitable in train); COSTS_BLOCK_MOST_SIGNALS (16 signals failed the cost filter at capital ₹1,000); SYNTHETIC_DATA — results are a software test, not evidence |
| NSE_EQ/INE009A01021 | rsi_reversion | NOT_TRADABLE_AT_THIS_CAPITAL | 0 | 0.0 | 0 | 0.0 | 0.0 |  | 0 | 1 | NO_TRADES_AFTER_AFFORDABILITY_AND_COST_FILTERS; TOO_FEW_TRADES (0 < 30); NON_POSITIVE_OUT_OF_SAMPLE; NON_POSITIVE_VALIDATION; PARAMETER_INSTABILITY (only 0% of grid profitable in train); COSTS_BLOCK_MOST_SIGNALS (1 signals failed the cost filter at capital ₹1,000); SYNTHETIC_DATA — results are a software test, not evidence |
| NSE_EQ/INE009A01021 | bollinger_reversion | NOT_TRADABLE_AT_THIS_CAPITAL | 0 | 0.0 | 0 | 0.0 | 0.0 |  | 0 | 58 | NO_TRADES_AFTER_AFFORDABILITY_AND_COST_FILTERS; TOO_FEW_TRADES (0 < 30); NON_POSITIVE_OUT_OF_SAMPLE; NON_POSITIVE_VALIDATION; PARAMETER_INSTABILITY (only 0% of grid profitable in train); COSTS_BLOCK_MOST_SIGNALS (58 signals failed the cost filter at capital ₹1,000); SYNTHETIC_DATA — results are a software test, not evidence |
| NSE_EQ/INE009A01021 | zscore_reversion | NOT_TRADABLE_AT_THIS_CAPITAL | 0 | 0.0 | 0 | 0.0 | 0.0 |  | 0 | 94 | NO_TRADES_AFTER_AFFORDABILITY_AND_COST_FILTERS; TOO_FEW_TRADES (0 < 30); NON_POSITIVE_OUT_OF_SAMPLE; NON_POSITIVE_VALIDATION; PARAMETER_INSTABILITY (only 0% of grid profitable in train); COSTS_BLOCK_MOST_SIGNALS (94 signals failed the cost filter at capital ₹1,000); SYNTHETIC_DATA — results are a software test, not evidence |
| NSE_EQ/INE009A01021 | orb | REJECT | 23 | -8.28 | 3 | -0.0142 | -22.79 | 32.17 | 0 | 0 | TOO_FEW_TRADES (23 < 30); NON_POSITIVE_OUT_OF_SAMPLE; NON_POSITIVE_VALIDATION; EDGE_DISAPPEARS_AFTER_COSTS; PARAMETER_INSTABILITY (only 0% of grid profitable in train); EXPECTANCY_CI_INCLUDES_ZERO; SYNTHETIC_DATA — results are a software test, not evidence |
| NSE_EQ/INE009A01021 | vwap_reversion | NOT_TRADABLE_AT_THIS_CAPITAL | 0 | 0.0 | 0 | 0.0 | 0.0 |  | 0 | 185 | NO_TRADES_AFTER_AFFORDABILITY_AND_COST_FILTERS; TOO_FEW_TRADES (0 < 30); NON_POSITIVE_OUT_OF_SAMPLE; NON_POSITIVE_VALIDATION; PARAMETER_INSTABILITY (only 0% of grid profitable in train); COSTS_BLOCK_MOST_SIGNALS (185 signals failed the cost filter at capital ₹1,000); SYNTHETIC_DATA — results are a software test, not evidence |
| NSE_EQ/INE009A01021 | prev_day_breakout | NOT_TRADABLE_AT_THIS_CAPITAL | 0 | 0.0 | 0 | 0.0 | 0.0 |  | 0 | 13 | NO_TRADES_AFTER_AFFORDABILITY_AND_COST_FILTERS; TOO_FEW_TRADES (0 < 30); NON_POSITIVE_OUT_OF_SAMPLE; NON_POSITIVE_VALIDATION; PARAMETER_INSTABILITY (only 0% of grid profitable in train); COSTS_BLOCK_MOST_SIGNALS (13 signals failed the cost filter at capital ₹1,000); SYNTHETIC_DATA — results are a software test, not evidence |
| NSE_EQ/INE002A01018 | sma_crossover | NOT_TRADABLE_AT_THIS_CAPITAL | 0 | 0.0 | 0 | 0.0 | 0.0 |  | 0 | 22 | NO_TRADES_AFTER_AFFORDABILITY_AND_COST_FILTERS; TOO_FEW_TRADES (0 < 30); NON_POSITIVE_OUT_OF_SAMPLE; NON_POSITIVE_VALIDATION; PARAMETER_INSTABILITY (only 0% of grid profitable in train); COSTS_BLOCK_MOST_SIGNALS (22 signals failed the cost filter at capital ₹1,000); SYNTHETIC_DATA — results are a software test, not evidence |
| NSE_EQ/INE002A01018 | ema_adx_trend | NOT_TRADABLE_AT_THIS_CAPITAL | 0 | 0.0 | 0 | 0.0 | 0.0 |  | 0 | 66 | NO_TRADES_AFTER_AFFORDABILITY_AND_COST_FILTERS; TOO_FEW_TRADES (0 < 30); NON_POSITIVE_OUT_OF_SAMPLE; NON_POSITIVE_VALIDATION; PARAMETER_INSTABILITY (only 0% of grid profitable in train); COSTS_BLOCK_MOST_SIGNALS (66 signals failed the cost filter at capital ₹1,000); SYNTHETIC_DATA — results are a software test, not evidence |
| NSE_EQ/INE002A01018 | donchian_breakout | NOT_TRADABLE_AT_THIS_CAPITAL | 0 | 0.0 | 0 | 0.0 | 0.0 |  | 0 | 51 | NO_TRADES_AFTER_AFFORDABILITY_AND_COST_FILTERS; TOO_FEW_TRADES (0 < 30); NON_POSITIVE_OUT_OF_SAMPLE; NON_POSITIVE_VALIDATION; PARAMETER_INSTABILITY (only 0% of grid profitable in train); COSTS_BLOCK_MOST_SIGNALS (51 signals failed the cost filter at capital ₹1,000); SYNTHETIC_DATA — results are a software test, not evidence |
| NSE_EQ/INE002A01018 | relative_strength | NOT_TRADABLE_AT_THIS_CAPITAL | 0 | 0.0 | 0 | 0.0 | 0.0 |  | 0 | 41 | NO_TRADES_AFTER_AFFORDABILITY_AND_COST_FILTERS; TOO_FEW_TRADES (0 < 30); NON_POSITIVE_OUT_OF_SAMPLE; NON_POSITIVE_VALIDATION; PARAMETER_INSTABILITY (only 0% of grid profitable in train); COSTS_BLOCK_MOST_SIGNALS (41 signals failed the cost filter at capital ₹1,000); SYNTHETIC_DATA — results are a software test, not evidence |
| NSE_EQ/INE002A01018 | pullback_trend | NOT_TRADABLE_AT_THIS_CAPITAL | 0 | 0.0 | 0 | 0.0 | 0.0 |  | 1 | 28 | NO_TRADES_AFTER_AFFORDABILITY_AND_COST_FILTERS; TOO_FEW_TRADES (0 < 30); NON_POSITIVE_OUT_OF_SAMPLE; NON_POSITIVE_VALIDATION; PARAMETER_INSTABILITY (only 0% of grid profitable in train); COSTS_BLOCK_MOST_SIGNALS (28 signals failed the cost filter at capital ₹1,000); MOSTLY_UNAFFORDABLE (1 signals skipped at capital ₹1,000); SYNTHETIC_DATA — results are a software test, not evidence |
| NSE_EQ/INE002A01018 | rsi_reversion | NO_SIGNALS | 0 | 0.0 | 0 | 0.0 | 0.0 |  | 0 | 0 | NO_TRADES_AFTER_AFFORDABILITY_AND_COST_FILTERS; TOO_FEW_TRADES (0 < 30); NON_POSITIVE_OUT_OF_SAMPLE; NON_POSITIVE_VALIDATION; PARAMETER_INSTABILITY (only 0% of grid profitable in train); SYNTHETIC_DATA — results are a software test, not evidence |
| NSE_EQ/INE002A01018 | bollinger_reversion | NOT_TRADABLE_AT_THIS_CAPITAL | 0 | 0.0 | 0 | 0.0 | 0.0 |  | 0 | 36 | NO_TRADES_AFTER_AFFORDABILITY_AND_COST_FILTERS; TOO_FEW_TRADES (0 < 30); NON_POSITIVE_OUT_OF_SAMPLE; NON_POSITIVE_VALIDATION; PARAMETER_INSTABILITY (only 0% of grid profitable in train); COSTS_BLOCK_MOST_SIGNALS (36 signals failed the cost filter at capital ₹1,000); SYNTHETIC_DATA — results are a software test, not evidence |
| NSE_EQ/INE002A01018 | zscore_reversion | NOT_TRADABLE_AT_THIS_CAPITAL | 0 | 0.0 | 0 | 0.0 | 0.0 |  | 0 | 74 | NO_TRADES_AFTER_AFFORDABILITY_AND_COST_FILTERS; TOO_FEW_TRADES (0 < 30); NON_POSITIVE_OUT_OF_SAMPLE; NON_POSITIVE_VALIDATION; PARAMETER_INSTABILITY (only 0% of grid profitable in train); COSTS_BLOCK_MOST_SIGNALS (74 signals failed the cost filter at capital ₹1,000); SYNTHETIC_DATA — results are a software test, not evidence |
| NSE_EQ/INE002A01018 | orb | REJECT | 19 | -8.22 | 2 | -0.0082 | -23.83 | 25.37 | 0 | 3 | TOO_FEW_TRADES (19 < 30); NON_POSITIVE_OUT_OF_SAMPLE; NON_POSITIVE_VALIDATION; EDGE_DISAPPEARS_AFTER_COSTS; PARAMETER_INSTABILITY (only 0% of grid profitable in train); EXPECTANCY_CI_INCLUDES_ZERO; SYNTHETIC_DATA — results are a software test, not evidence |
| NSE_EQ/INE002A01018 | vwap_reversion | NOT_TRADABLE_AT_THIS_CAPITAL | 0 | 0.0 | 0 | 0.0 | 0.0 |  | 0 | 210 | NO_TRADES_AFTER_AFFORDABILITY_AND_COST_FILTERS; TOO_FEW_TRADES (0 < 30); NON_POSITIVE_OUT_OF_SAMPLE; NON_POSITIVE_VALIDATION; PARAMETER_INSTABILITY (only 0% of grid profitable in train); COSTS_BLOCK_MOST_SIGNALS (210 signals failed the cost filter at capital ₹1,000); SYNTHETIC_DATA — results are a software test, not evidence |
| NSE_EQ/INE002A01018 | prev_day_breakout | NOT_TRADABLE_AT_THIS_CAPITAL | 0 | 0.0 | 0 | 0.0 | 0.0 |  | 0 | 12 | NO_TRADES_AFTER_AFFORDABILITY_AND_COST_FILTERS; TOO_FEW_TRADES (0 < 30); NON_POSITIVE_OUT_OF_SAMPLE; NON_POSITIVE_VALIDATION; PARAMETER_INSTABILITY (only 0% of grid profitable in train); COSTS_BLOCK_MOST_SIGNALS (12 signals failed the cost filter at capital ₹1,000); SYNTHETIC_DATA — results are a software test, not evidence |

## gaps

```json
{
 "NSE_EQ|INE154A01025": {
  "n_days": 1499,
  "gap_up_days": 138,
  "gap_down_days": 146,
  "gap_up_fill_rate": 0.848,
  "gap_down_fill_rate": 0.788,
  "mean_open_to_close_after_gap_up": -0.00785,
  "mean_open_to_close_after_gap_down": 0.00749,
  "max_abs_gap": 0.0116
 },
 "NSE_EQ|INE062A01020": {
  "n_days": 1499,
  "gap_up_days": 141,
  "gap_down_days": 124,
  "gap_up_fill_rate": 0.78,
  "gap_down_fill_rate": 0.726,
  "mean_open_to_close_after_gap_up": -0.00798,
  "mean_open_to_close_after_gap_down": 0.00608,
  "max_abs_gap": 0.012
 },
 "NSE_EQ|INE081A01020": {
  "n_days": 1499,
  "gap_up_days": 121,
  "gap_down_days": 137,
  "gap_up_fill_rate": 0.702,
  "gap_down_fill_rate": 0.664,
  "mean_open_to_close_after_gap_up": -0.00389,
  "mean_open_to_close_after_gap_down": 0.00309,
  "max_abs_gap": 0.0137
 },
 "NSE_EQ|INE733E01010": {
  "n_days": 1499,
  "gap_up_days": 159,
  "gap_down_days": 144,
  "gap_up_fill_rate": 0.767,
  "gap_down_fill_rate": 0.715,
  "mean_open_to_close_after_gap_up": -0.00689,
  "mean_open_to_close_after_gap_down": 0.00658,
  "max_abs_gap": 0.0147
 },
 "NSE_EQ|INE213A01029": {
  "n_days": 1499,
  "gap_up_days": 134,
  "gap_down_days": 124,
  "gap_up_fill_rate": 0.761,
  "gap_down_fill_rate": 0.677,
  "mean_open_to_close_after_gap_up": -0.00528,
  "mean_open_to_close_after_gap_down": 0.00505,
  "max_abs_gap": 0.0132
 },
 "NSE_EQ|INE522F01014": {
  "n_days": 1499,
  "gap_up_days": 140,
  "gap_down_days": 135,
  "gap_up_fill_rate": 0.743,
  "gap_down_fill_rate": 0.696,
  "mean_open_to_close_after_gap_up": -0.00703,
  "mean_open_to_close_after_gap_down": 0.00573,
  "max_abs_gap": 0.013
 },
 "NSE_EQ|INE263A01024": {
  "n_days": 1499,
  "gap_up_days": 149,
  "gap_down_days": 135,
  "gap_up_fill_rate": 0.745,
  "gap_down_fill_rate": 0.778,
  "mean_open_to_close_after_gap_up": -0.00734,
  "mean_open_to_close_after_gap_down": 0.0082,
  "max_abs_gap": 0.0126
 },
 "NSE_EQ|INE242A01010": {
  "n_days": 1499,
  "gap_up_days": 141,
  "gap_down_days": 134,
  "gap_up_fill_rate": 0.78,
  "gap_down_fill_rate": 0.799,
  "mean_open_to_close_after_gap_up": -0.00819,
  "mean_open_to_close_after_gap_down": 0.00769,
  "max_abs_gap": 0.0136
 },
 "NSE_EQ|INE009A01021": {
  "n_days": 1499,
  "gap_up_days": 156,
  "gap_down_days": 139,
  "gap_up_fill_rate": 0.744,
  "gap_down_fill_rate": 0.827,
  "mean_open_to_close_after_gap_up": -0.00778,
  "mean_open_to_close_after_gap_down": 0.00752,
  "max_abs_gap": 0.0137
 },
 "NSE_EQ|INE002A01018": {
  "n_days": 1499,
  "gap_up_days": 146,
  "gap_down_days": 155,
  "gap_up_fill_rate": 0.747,
  "gap_down_fill_rate": 0.768,
  "mean_open_to_close_after_gap_up": -0.00597,
  "mean_open_to_close_after_gap_down": 0.0069,
  "max_abs_gap": 0.0135
 }
}
```

## regime_now

```json
{
 "NSE_EQ|INE154A01025": [
  "SIDEWAYS",
  "LOW_VOLATILITY",
  "MEAN_REVERTING"
 ],
 "NSE_EQ|INE062A01020": [
  "STRONG_DOWNTREND",
  "LOW_VOLATILITY"
 ],
 "NSE_EQ|INE081A01020": [
  "UNCERTAIN_CONFLICTING",
  "STRONG_DOWNTREND",
  "LOW_VOLATILITY",
  "MEAN_REVERTING"
 ],
 "NSE_EQ|INE733E01010": [
  "STRONG_UPTREND",
  "LOW_VOLATILITY"
 ],
 "NSE_EQ|INE213A01029": [
  "STRONG_UPTREND"
 ],
 "NSE_EQ|INE522F01014": [
  "UNCERTAIN_CONFLICTING",
  "STRONG_DOWNTREND",
  "HIGH_VOLATILITY",
  "MEAN_REVERTING"
 ],
 "NSE_EQ|INE263A01024": [
  "SIDEWAYS",
  "HIGH_VOLATILITY"
 ],
 "NSE_EQ|INE242A01010": [
  "SIDEWAYS",
  "LOW_VOLATILITY"
 ],
 "NSE_EQ|INE009A01021": [
  "UNCERTAIN_CONFLICTING",
  "STRONG_DOWNTREND",
  "HIGH_VOLATILITY",
  "MEAN_REVERTING"
 ],
 "NSE_EQ|INE002A01018": [
  "HIGH_VOLATILITY",
  "MEAN_REVERTING"
 ]
}
```

## stockshield

```json
{
 "NSE_EQ|INE154A01025": {
  "score": 0.0,
  "level": "LOW",
  "contributions": {
   "abnormal_volume": 0.0,
   "price_spike": 0.0,
   "price_volume_divergence": 0.0,
   "rapid_reversal": 0.0,
   "false_breakout": 0.0,
   "liquidity_deterioration": 0.0,
   "volatility_expansion": 0.0
  }
 },
 "NSE_EQ|INE062A01020": {
  "score": 1.7,
  "level": "LOW",
  "contributions": {
   "abnormal_volume": 0.0,
   "price_spike": 0.0,
   "price_volume_divergence": 1.69,
   "rapid_reversal": 0.0,
   "false_breakout": 0.0,
   "liquidity_deterioration": 0.0,
   "volatility_expansion": 0.0
  }
 },
 "NSE_EQ|INE081A01020": {
  "score": 0.0,
  "level": "LOW",
  "contributions": {
   "abnormal_volume": 0.0,
   "price_spike": 0.0,
   "price_volume_divergence": 0.0,
   "rapid_reversal": 0.0,
   "false_breakout": 0.0,
   "liquidity_deterioration": 0.0,
   "volatility_expansion": 0.0
  }
 },
 "NSE_EQ|INE733E01010": {
  "score": 0.0,
  "level": "LOW",
  "contributions": {
   "abnormal_volume": 0.0,
   "price_spike": 0.0,
   "price_volume_divergence": 0.0,
   "rapid_reversal": 0.0,
   "false_breakout": 0.0,
   "liquidity_deterioration": 0.0,
   "volatility_expansion": 0.0
  }
 },
 "NSE_EQ|INE213A01029": {
  "score": 15.0,
  "level": "LOW",
  "contributions": {
   "abnormal_volume": 0.0,
   "price_spike": 0.0,
   "price_volume_divergence": 0.0,
   "rapid_reversal": 0.0,
   "false_breakout": 15.0,
   "liquidity_deterioration": 0.0,
   "volatility_expansion": 0.0
  }
 },
 "NSE_EQ|INE522F01014": {
  "score": 15.2,
  "level": "LOW",
  "contributions": {
   "abnormal_volume": 0.0,
   "price_spike": 0.0,
   "price_volume_divergence": 0.0,
   "rapid_reversal": 0.0,
   "false_breakout": 15.0,
   "liquidity_deterioration": 0.0,
   "volatility_expansion": 0.17
  }
 },
 "NSE_EQ|INE263A01024": {
  "score": 0.6,
  "level": "LOW",
  "contributions": {
   "abnormal_volume": 0.0,
   "price_spike": 0.0,
   "price_volume_divergence": 0.0,
   "rapid_reversal": 0.0,
   "false_breakout": 0.0,
   "liquidity_deterioration": 0.0,
   "volatility_expansion": 0.59
  }
 },
 "NSE_EQ|INE242A01010": {
  "score": 0.0,
  "level": "LOW",
  "contributions": {
   "abnormal_volume": 0.0,
   "price_spike": 0.0,
   "price_volume_divergence": 0.0,
   "rapid_reversal": 0.0,
   "false_breakout": 0.0,
   "liquidity_deterioration": 0.0,
   "volatility_expansion": 0.0
  }
 },
 "NSE_EQ|INE009A01021": {
  "score": 15.6,
  "level": "LOW",
  "contributions": {
   "abnormal_volume": 0.0,
   "price_spike": 0.0,
   "price_volume_divergence": 0.08,
   "rapid_reversal": 0.0,
   "false_breakout": 15.0,
   "liquidity_deterioration": 0.0,
   "volatility_expansion": 0.49
  }
 },
 "NSE_EQ|INE002A01018": {
  "score": 0.8,
  "level": "LOW",
  "contributions": {
   "abnormal_volume": 0.0,
   "price_spike": 0.0,
   "price_volume_divergence": 0.0,
   "rapid_reversal": 0.0,
   "false_breakout": 0.0,
   "liquidity_deterioration": 0.0,
   "volatility_expansion": 0.78
  }
 }
}
```

## Machine learning vs baselines

- NSE_EQ|INE154A01025: volatility → use ridge for sizing only; adverse-move → do not use; baseline is as good
- NSE_EQ|INE062A01020: volatility → use ridge for sizing only; adverse-move → do not use; baseline is as good
- NSE_EQ|INE081A01020: volatility → use ridge for sizing only; adverse-move → do not use; baseline is as good
- NSE_EQ|INE733E01010: volatility → prefer baseline (persistence); adverse-move → do not use; baseline is as good
- NSE_EQ|INE213A01029: volatility → use ridge for sizing only; adverse-move → do not use; baseline is as good
- NSE_EQ|INE522F01014: volatility → prefer baseline (persistence); adverse-move → do not use; baseline is as good
- NSE_EQ|INE263A01024: volatility → prefer baseline (persistence); adverse-move → do not use; baseline is as good
- NSE_EQ|INE242A01010: volatility → prefer baseline (persistence); adverse-move → do not use; baseline is as good
- NSE_EQ|INE009A01021: volatility → use ridge for sizing only; adverse-move → do not use; baseline is as good
- NSE_EQ|INE002A01018: volatility → use ridge for sizing only; adverse-move → do not use; baseline is as good

## cross_sectional_momentum

| instrument_key | mom_12_1 | ret_1m |
|---|---|---|
| NSE_EQ/INE263A01024 | 0.4588 | 0.0338 |
| NSE_EQ/INE154A01025 | 0.1927 | 0.0104 |
| NSE_EQ/INE213A01029 | 0.1291 | 0.1575 |
| NSE_EQ/INE002A01018 | 0.1276 | 0.0377 |
| NSE_EQ/INE242A01010 | -0.0109 | 0.0135 |
| NSE_EQ/INE522F01014 | -0.018 | -0.0403 |
| NSE_EQ/INE062A01020 | -0.1385 | -0.0848 |
| NSE_EQ/INE081A01020 | -0.1498 | -0.0748 |
| NSE_EQ/INE733E01010 | -0.1527 | 0.1245 |
| NSE_EQ/INE009A01021 | -0.1611 | -0.0946 |

## pairs

| a | b | t_in | coint_in | t_out | coint_out | hedge_ratio | half_life |
|---|---|---|---|---|---|---|---|
| NSE_EQ/INE154A01025 | NSE_EQ/INE062A01020 | -2.056 | False | -0.498 | False | 0.4518 | 74.5378 |
| NSE_EQ/INE154A01025 | NSE_EQ/INE081A01020 | -0.61 | False | -1.818 | False | 0.149 | 335.1063 |
| NSE_EQ/INE154A01025 | NSE_EQ/INE733E01010 | -1.264 | False | -1.507 | False | -0.234 | 144.5035 |
| NSE_EQ/INE154A01025 | NSE_EQ/INE213A01029 | -0.525 | False | -1.892 | False | -0.1254 | 401.0395 |
| NSE_EQ/INE154A01025 | NSE_EQ/INE522F01014 | -2.725 | False | -1.762 | False | -0.5427 | 48.7695 |
| NSE_EQ/INE154A01025 | NSE_EQ/INE263A01024 | -1.161 | False | -2.23 | False | -0.303 | 174.8426 |
| NSE_EQ/INE154A01025 | NSE_EQ/INE242A01010 | -0.861 | False | -1.779 | False | 0.1454 | 230.4321 |
| NSE_EQ/INE154A01025 | NSE_EQ/INE009A01021 | -1.264 | False | -1.552 | False | 0.312 | 152.2353 |
| NSE_EQ/INE154A01025 | NSE_EQ/INE002A01018 | -1.541 | False | -2.455 | False | -0.5399 | 101.6762 |
| NSE_EQ/INE062A01020 | NSE_EQ/INE081A01020 | -1.016 | False | -0.948 | False | 0.3854 | 263.7674 |
| NSE_EQ/INE062A01020 | NSE_EQ/INE733E01010 | -1.316 | False | -2.43 | False | -0.3206 | 176.6312 |
| NSE_EQ/INE062A01020 | NSE_EQ/INE213A01029 | -0.736 | False | -0.845 | False | -0.5266 | 317.8597 |
| NSE_EQ/INE062A01020 | NSE_EQ/INE522F01014 | -2.46 | False | -2.041 | False | -0.6794 | 77.9961 |
| NSE_EQ/INE062A01020 | NSE_EQ/INE263A01024 | -1.665 | False | -1.179 | False | -0.6656 | 151.7024 |
| NSE_EQ/INE062A01020 | NSE_EQ/INE242A01010 | -1.028 | False | -2.887 | False | 0.2975 | 247.4486 |
| NSE_EQ/INE062A01020 | NSE_EQ/INE009A01021 | -1.436 | False | -0.948 | False | 0.1911 | 209.2545 |
| NSE_EQ/INE062A01020 | NSE_EQ/INE002A01018 | -1.731 | False | -1.268 | False | -0.8409 | 105.89 |
| NSE_EQ/INE081A01020 | NSE_EQ/INE733E01010 | -2.7 | False | -2.432 | False | -0.3353 | 43.2858 |
| NSE_EQ/INE081A01020 | NSE_EQ/INE213A01029 | -2.039 | False | -2.27 | False | -0.3 | 89.6361 |
| NSE_EQ/INE081A01020 | NSE_EQ/INE522F01014 | -1.882 | False | -2.275 | False | -0.3113 | 89.378 |
| NSE_EQ/INE081A01020 | NSE_EQ/INE263A01024 | -2.037 | False | -2.759 | False | 0.2131 | 93.9163 |
| NSE_EQ/INE081A01020 | NSE_EQ/INE242A01010 | -3.65 | True | -2.288 | False | 0.3794 | 26.2836 |
| NSE_EQ/INE081A01020 | NSE_EQ/INE009A01021 | -3.032 | False | -2.144 | False | -0.6771 | 38.7313 |
| NSE_EQ/INE081A01020 | NSE_EQ/INE002A01018 | -2.335 | False | -2.245 | False | -0.5369 | 60.9746 |
| NSE_EQ/INE733E01010 | NSE_EQ/INE213A01029 | -0.842 | False | -1.764 | False | 0.4468 | 552.9586 |
| NSE_EQ/INE733E01010 | NSE_EQ/INE522F01014 | -2.203 | False | -3.116 | False | 1.2561 | 93.2529 |
| NSE_EQ/INE733E01010 | NSE_EQ/INE263A01024 | -1.197 | False | -2.106 | False | -0.3684 | 399.5038 |
| NSE_EQ/INE733E01010 | NSE_EQ/INE242A01010 | -2.508 | False | -2.785 | False | -0.9441 | 58.3399 |
| NSE_EQ/INE733E01010 | NSE_EQ/INE009A01021 | -0.546 | False | -1.661 | False | 1.1399 | 476.5269 |
| NSE_EQ/INE733E01010 | NSE_EQ/INE002A01018 | -3.071 | False | -2.424 | False | 1.9408 | 37.0728 |
| NSE_EQ/INE213A01029 | NSE_EQ/INE522F01014 | -1.871 | False | -1.323 | False | -0.0459 | 113.273 |
| NSE_EQ/INE213A01029 | NSE_EQ/INE263A01024 | -1.555 | False | -2.372 | False | 0.4025 | 125.0716 |
| NSE_EQ/INE213A01029 | NSE_EQ/INE242A01010 | -1.589 | False | -2.219 | False | -0.1242 | 126.2334 |
| NSE_EQ/INE213A01029 | NSE_EQ/INE009A01021 | -1.861 | False | -2.863 | False | 0.1189 | 112.3142 |
| NSE_EQ/INE213A01029 | NSE_EQ/INE002A01018 | -1.656 | False | -2.538 | False | 0.2438 | 120.4376 |
| NSE_EQ/INE522F01014 | NSE_EQ/INE263A01024 | -0.641 | False | -2.387 | False | 0.3456 | 507.9331 |
| NSE_EQ/INE522F01014 | NSE_EQ/INE242A01010 | -1.205 | False | -2.509 | False | -0.4009 | 188.2692 |
| NSE_EQ/INE522F01014 | NSE_EQ/INE009A01021 | 0.001 | False | -1.827 | False | 0.151 |  |
| NSE_EQ/INE522F01014 | NSE_EQ/INE002A01018 | -1.72 | False | -2.326 | False | 0.8467 | 105.2581 |
| NSE_EQ/INE263A01024 | NSE_EQ/INE242A01010 | -2.563 | False | -0.622 | False | 0.0276 | 49.2995 |
| NSE_EQ/INE263A01024 | NSE_EQ/INE009A01021 | -2.703 | False | -1.918 | False | -0.0669 | 47.0394 |
| NSE_EQ/INE263A01024 | NSE_EQ/INE002A01018 | -2.545 | False | -2.007 | False | -0.025 | 50.1489 |
| NSE_EQ/INE242A01010 | NSE_EQ/INE009A01021 | -1.506 | False | -2.316 | False | -1.317 | 142.1079 |
| NSE_EQ/INE242A01010 | NSE_EQ/INE002A01018 | -2.599 | False | -3.504 | True | -1.7044 | 55.7209 |
| NSE_EQ/INE009A01021 | NSE_EQ/INE002A01018 | -1.176 | False | -1.17 | False | 0.2991 | 164.5884 |
