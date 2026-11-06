---
name: risk-portfolio
description: Aggregate gross and net exposure, leverage and asset concentration for linear positions in one base currency, over the hosted Risk Desk MCP.
---

# Risk Portfolio, hosted

Call `risk_desk_status` first to check availability, input limits and
reporting conventions. Then use `risk_exposure` on the connected hosted Risk
Desk MCP. Discover its input schema instead of guessing field names.
No local runtime or market-data feed is needed.

For a requested demonstration, omit `request` to use the synthetic energy
book. Label the result as synthetic. For the user's own book, pass the
supplied data in `request`; never substitute the demo when input is
missing or invalid. Ask only for missing required fields.

Report degraded status, its reason, base currency, horizon and sign
convention before the figures. Preserve source and as-of information.
If the service is unavailable, report the failure without inventing results.

For supplied data, require signed market values translated into the
stated currency and an explicit NAV. Currency conversion must be complete before the
request is sent; the service performs none. Confirm that each position is
a linear asset. Options require sensitivities or full revaluation;
premium market value is not delta exposure.

Explain net against gross. Gross concentration uses absolute position
values before offsetting, so a share of gross is never negative; leverage
divides by the supplied NAV. A negative net value is a short. Do not
describe any of these amounts as counterparty EAD or as regulated capital.

Before sending user data, establish that the user is permitted to share
it with a hosted service. Existing permission in the conversation is
sufficient. `data_mode` records their declaration; it
is not a rights certificate and the service does not check it.

Counterparty XVA is not available here. They need a trusted
local ORE project directory, which a remote endpoint cannot read. Point
the user at the local `risk-desk` plugin for that.

## Data and result limits

For every calculation with a supplied `request`, set the separate boolean
`rights_confirmed=true` only after the user confirms permission for hosted
processing and output delivery. Existing explicit permission is sufficient.
Never infer permission from an attachment or `data_mode`. No-input synthetic
demonstrations need no confirmation. Confirmation does not verify a licence.

Keep model and data limitations visible. Results can be wrong; reproducibility
does not establish fitness or regulatory approval. Do not present a ranking or
comparison as a personal recommendation, executable quote or guaranteed loss
limit. Independently verify material results before use.

[Terms](https://riskdesk.avidquant.com/terms) and
[privacy](https://riskdesk.avidquant.com/privacy) explain data handling and legal limits.
