# Regulatory & broker requirement checklist (verify yourself — not legal advice)

Status as read on 21 Oct 2026 from Upstox/SEBI sources listed in RESEARCH.md.

- [ ] Upstox account active with the segments you intend to use (equity; F&O needs separate activation and income proof).
- [ ] Developer app created at https://account.upstox.com/developer/apps (API key/secret, redirect URL).
- [ ] **Static IP** registered in the app (primary, optional secondary). All place/modify/cancel/multi/GTT calls must come
      from it since 1 Apr 2026. Changeable once per calendar week; changing it invalidates the access token.
      Typical home broadband IPs are dynamic — ask your ISP for a static IP, or run the engine on a VPS with a static IP
      (code works unchanged; dashboard stays local).
- [ ] Order rate stays below **10 orders/second** (this app: ≤10 orders per session by default) → no SEBI algo registration
      needed. If you ever exceed it, the strategy must be exchange-registered and `algo_name` set (sent as `X-Algo-Name`).
- [ ] Orders carry a `tag` (this app tags every order `IQ…`) for traceability.
- [ ] No MARKET orders via API (Upstox, Apr 2026) — app uses LIMIT/SL only.
- [ ] MCX API trading temporarily disabled at Upstox (not used by this app).
- [ ] Daily login: access token expires 03:30 IST.
- [ ] Understand charges, including F&O STT increase effective 1 Apr 2026 (futures 0.05%, options 0.15% of premium).
- [ ] Read SEBI's risk disclosure on derivatives (most retail F&O traders lose money).
- [ ] Tax: intraday equity = speculative business income; F&O = non-speculative business income; keep the trade log
      (`orders`, `fills`, audit tables) and the broker P&L report. Consult a tax professional.
