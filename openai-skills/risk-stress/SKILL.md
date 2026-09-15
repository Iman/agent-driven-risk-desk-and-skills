---
name: risk-stress
description: Revalue linear positions under explicitly supplied asset-return scenarios, over the hosted Risk Desk MCP. Use for scenario loss and contribution analysis.
---

# Risk Stress, hosted

Use `risk_stress` over the hosted Risk Desk MCP. Nothing is installed and
no market data is fetched: the user supplies both the positions and every
shock, and the service revalues exactly those.

Every scenario must name exactly the portfolio assets, including an
explicit zero where no change is intended. A missing asset is refused
rather than treated as unchanged. Report scenario P&L, loss, stressed NAV
and per-position contributions. A negative loss is a scenario the book
gains in.

Scenario severity is not an event probability, and no probability is
attached to any scenario. A scenario named after a historical episode
carries the shape somebody chose for it, not a fitted event and not a
forecast. Say so when the user names one that way.

The model is linear. Do not apply it to option premium values, credit
migration or nonlinear margin calls.

Before anything is sent, confirm the user is permitted to share the
positions with a hosted service. `data_mode` records their declaration; it
is not a rights certificate and the service does not check it.

Counterparty exposure and XVA are not available here. They need a trusted
local ORE project directory, which a remote endpoint cannot read. Point
the user at the local `risk-desk` plugin for that.
