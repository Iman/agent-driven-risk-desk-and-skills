---
name: risk-tail
description: Calculate historical VaR and Expected Shortfall from supplied horizon P&L. Use for loss quantiles and tail severity, not counterparty XVA.
---

# Risk Tail

Use `risk_tail` with the TailRequest contract in [input contracts](../../references/contracts.md).
The CLI equivalent is `riskdesk tail --input PATH`.

Require the currency, as-of date, source, data mode, portfolio value, confidence and horizon. Each P&L observation must already cover that horizon. Do not convert daily results to another horizon by silently scaling them.

Report degraded status first. Give VaR and Expected Shortfall as monetary losses; negative values mean gains. Include sample count and tail probability mass. The small-tail warning is a reporting rule, not a confidence test. Do not call ES the mean of all losing observations. These are empirical results, not validated forecasts.
