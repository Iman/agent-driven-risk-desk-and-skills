---
name: risk-stress
description: Revalue linear positions under explicitly supplied asset-return scenarios, over the hosted Risk Desk MCP. Use for scenario loss and contribution analysis.
---

# Risk Stress, hosted

Call `risk_desk_status` first to check availability, input limits and
reporting conventions. Then use `risk_stress` on the connected hosted Risk
Desk MCP. Discover its input schema instead of guessing field names.
No local runtime or market-data feed is needed.

For a requested demonstration, omit `request` to use the synthetic energy
book. Label the result as synthetic. For the user's own book, pass the
supplied data in `request`; never substitute the demo when input is
missing or invalid. Ask only for missing required fields.

Report degraded status, its reason, base currency, horizon and sign
convention before the figures. Preserve source and as-of information.
If the service is unavailable, report the failure without inventing results.

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

Before sending user data, establish that the user is permitted to share
it with a hosted service. Existing permission in the conversation is
sufficient. `data_mode` records their declaration; it
is not a rights certificate and the service does not check it.

Counterparty exposure and XVA are not available here. They need a trusted
local ORE project directory, which a remote endpoint cannot read. Point
the user at the local `risk-desk` plugin for that.
