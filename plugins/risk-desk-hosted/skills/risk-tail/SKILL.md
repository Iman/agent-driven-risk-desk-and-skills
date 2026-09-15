---
name: risk-tail
description: Calculate historical VaR and Expected Shortfall from P&L the user supplies, over the hosted Risk Desk MCP. Use for loss quantiles and tail severity, not counterparty XVA.
---

# Risk Tail, hosted

Use `risk_tail` over the hosted Risk Desk MCP. Nothing is installed and no
market data is fetched: the user supplies the P&L observations and the
service computes over exactly those.

Require the currency, as-of date, source, data mode, portfolio value,
confidence and horizon. Each P&L observation must already cover that
horizon. Do not convert daily results to another horizon by silently
scaling them.

Report degraded status first. Give VaR and Expected Shortfall as monetary
losses; negative values mean gains and are not floored at zero. Include
the sample count and the tail probability mass. The small-tail warning is
a reporting rule, not a confidence test. Do not call ES the mean of all
losing observations. These are empirical results over one supplied
sample, not validated forecasts.

Before anything is sent, confirm the user is permitted to share the data
with a hosted service. `data_mode` records their declaration; it is not a
rights certificate and the service does not check it.

Counterparty exposure and XVA are not available here. They need a trusted
local ORE project directory, which a remote endpoint cannot read. Point
the user at the local `risk-desk` plugin for that.
