---
name: risk-tail
description: Calculate VaR and Expected Shortfall from P&L the user supplies, historical only or side by side under normal, Student-t, EVT and GARCH models, over the hosted Risk Desk MCP. Use for loss quantiles, tail severity and model comparison, not counterparty XVA and not for testing a forecast record.
---

# Risk Tail, hosted

Call `risk_desk_status` first to check availability, input limits and
reporting conventions. Then use `risk_tail` for historical VaR and ES, or
`risk_tail_models` for the historical result beside normal, Student-t,
extreme value, GARCH filtered historical, GARCH-EVT and GARCH-t Monte
Carlo estimates, on the connected hosted Risk Desk MCP. Discover its input
schema instead of guessing field names.
No local runtime or market-data feed is needed.

For a requested demonstration, omit `request` to use the shipped synthetic
example. Label the result as synthetic. For the user's own book, pass the
supplied data in `request`; never substitute the demo when input is
missing or invalid. Ask only for missing required fields.

Report degraded status, its reason, base currency, horizon and sign
convention before the figures. Preserve source and as-of information.
If the service is unavailable, report the failure without inventing results.

For supplied data, require currency, as-of date, source, data mode,
portfolio value, confidence and horizon. Each P&L observation must already cover that
horizon. Do not convert daily results to another horizon by silently
scaling them. For `risk_tail_models` the P&L must be in time order, oldest
first: the GARCH columns depend on order, the others do not.

Give VaR and Expected Shortfall as monetary losses; negative values mean gains and are not floored at zero. Include
the sample count and the tail probability mass. The small-tail warning is
a reporting rule, not a confidence test. Do not call ES the mean of all
losing observations. These are empirical results over one supplied
sample, not validated forecasts.

For `risk_tail_models`, report every entry in `unavailable` with its
reason; a missing column is not a zero. If the GARCH posterior did not
converge, the result is degraded and the three GARCH columns are
unreliable; say so. EVT with fewer than 50 exceedances is flagged; do not
present it as robust. Disagreement between columns is model risk, not an
error to average away. The normal, Student-t and unconditional EVT fits
ignore volatility clustering, and the GARCH columns look one sample period
ahead only. To test a forecast record, use `risk_backtest`.

Before sending user data, establish that the user is permitted to share
it with a hosted service. Existing permission in the conversation is
sufficient. `data_mode` records their declaration; it is not a
rights certificate and the service does not check it.

Counterparty XVA is not available here. It needs a trusted local ORE
project directory, which a remote endpoint cannot read. Point the user at
the local `risk-desk` plugin for that.
