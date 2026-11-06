---
name: risk-counterparty
description: Calculate Basel SA-CCR exposure at default for one derivative netting set, or summarise a simulated exposure profile into peak PFE, EPE, Effective EE and Effective EPE, over the hosted Risk Desk MCP. Use for counterparty exposure measures, not for XVA or credit capital.
---

# Risk Counterparty, hosted

Call `risk_desk_status` first to check availability, input limits and
reporting conventions. Then use `risk_saccr` for SA-CCR exposure at
default (CRE52) or `risk_exposure_profile` for an exposure profile summary
(CRE50, CRE53) on the connected hosted Risk Desk MCP. Discover the input
schema instead of guessing field names. No local runtime is needed.

For a requested demonstration, omit `request` to use the shipped synthetic
example. Label the result as synthetic; its `data_origin` is
`synthetic_demo`. For the user's own trades or profile, pass them in
`request`; never substitute the demo when input is missing or invalid.
Ask only for missing required fields.

Report degraded status and its reason first. For SA-CCR, then `ead` with
the currency, replacement cost, multiplier, PFE and the add-on per asset
class, and for a margined set whether the unmargined cap applied. For a
profile, Effective EPE and EPE with the averaging horizon, then peak PFE
with its time. Preserve source, as-of and the input hash. If the service
is unavailable, report the failure without inventing results.

For SA-CCR, every amount is in the request currency and times are years
from the as-of date. Each trade needs its asset class, notional, signed
market value to the bank, maturity and long or short position, plus the
class fields and option terms the schema asks for. A margined set needs
its threshold, minimum transfer amount, NICA, remargining period and MPOR;
the MPOR must be at least nine business days plus the remargining period.
For a profile, keep the column names exactly as ORE writes them; the first
row is at Time 0, times increase, and all rows are one netting set.
Never invent a trade term, rating, market value, collateral amount or
exposure row.

Exposure is a positive amount the bank could lose on counterparty
default. Market value and collateral are signed from the bank's side.
Replacement cost is floored at zero; excess collateral lowers the
multiplier, never the replacement cost below zero.

These are research calculations, not a regulatory submission. SA-CCR EAD
is an exposure measure, not a loss forecast, a price or a capital
requirement; no risk weight is applied. Only one bilateral netting set is
modelled: no basis or volatility hedging sets, CDO tranches, central
counterparty MPOR floors, 20-day MPOR cases or multiple netting sets. FX
and equity add-ons are partially verified: their constants are checked
against CRE52.72, but no published worked example exists, and the result
says so in its assumptions; report it. The profile summary is not an IMM
EAD, and it is only as good as the simulation behind it.

Before sending user data, establish that the user is permitted to share
it with a hosted service. Existing permission in the conversation is
sufficient. `data_mode` records their declaration; it is not a rights
certificate and the service does not check it.

Counterparty XVA and running an ORE simulation are not available here.
They need a trusted local ORE project directory, which a remote endpoint
cannot read. Point the user at the local `risk-desk` plugin for that.

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
