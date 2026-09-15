---
name: risk-portfolio
description: Aggregate gross and net exposure, leverage and asset concentration for linear positions in one base currency, over the hosted Risk Desk MCP.
---

# Risk Portfolio, hosted

Use `risk_exposure` over the hosted Risk Desk MCP. Nothing is installed
and no market data is fetched: the user supplies the positions and the
service aggregates exactly those.

Require signed market values already translated into the stated currency,
and an explicit NAV. Currency conversion must be complete before the
request is sent; the service performs none. Confirm that each position is
a linear asset. Options require sensitivities or full revaluation;
premium market value is not delta exposure.

Explain net against gross. Gross concentration uses absolute position
values before offsetting, so a share of gross is never negative; leverage
divides by the supplied NAV. A negative net value is a short. Do not
describe any of these amounts as counterparty EAD or as regulated capital.

Before anything is sent, confirm the user is permitted to share the
positions with a hosted service. `data_mode` records their declaration; it
is not a rights certificate and the service does not check it.

Counterparty exposure and XVA are not available here. They need a trusted
local ORE project directory, which a remote endpoint cannot read. Point
the user at the local `risk-desk` plugin for that.
