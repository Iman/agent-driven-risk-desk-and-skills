---
name: risk-tail
description: Calculate historical VaR and Expected Shortfall from P&L the user supplies, over the hosted Risk Desk MCP. Use for loss quantiles and tail severity, not counterparty XVA.
---

# Risk Tail, hosted

Call `risk_desk_status` first to check availability, input limits and
reporting conventions. Then use `risk_tail` on the connected hosted Risk
Desk MCP. Discover its input schema instead of guessing field names.
No local runtime or market-data feed is needed.

For a requested demonstration, omit `request` to use the synthetic energy
book. Label the result as synthetic. For the user's own book, pass the
supplied data in `request`; never substitute the demo when input is
missing or invalid. Ask only for missing required fields.

Report degraded status, its reason, base currency, horizon and sign
convention before the figures. Preserve source and as-of information.
If the service is unavailable, report the failure without inventing results.

For supplied data, require currency, as-of date, source, data mode,
portfolio value, confidence and horizon. Each P&L observation must already cover that
horizon. Do not convert daily results to another horizon by silently
scaling them.

Give VaR and Expected Shortfall as monetary losses; negative values mean gains and are not floored at zero. Include
the sample count and the tail probability mass. The small-tail warning is
a reporting rule, not a confidence test. Do not call ES the mean of all
losing observations. These are empirical results over one supplied
sample, not validated forecasts.

Before sending user data, establish that the user is permitted to share
it with a hosted service. Existing permission in the conversation is
sufficient. `data_mode` records their declaration; it is not a
rights certificate and the service does not check it.

Counterparty exposure and XVA are not available here. They need a trusted
local ORE project directory, which a remote endpoint cannot read. Point
the user at the local `risk-desk` plugin for that.
