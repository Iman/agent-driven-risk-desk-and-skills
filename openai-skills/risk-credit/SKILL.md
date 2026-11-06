---
name: risk-credit
description: Calculate portfolio credit VaR, expected and unexpected loss from obligor exposure, PD and LGD with the Vasicek ASRF quantile or a seeded one-factor Gaussian copula Monte Carlo, over the hosted Risk Desk MCP. Use for default loss on a loan or bond book, not for IRB capital or rating migration.
---

# Risk Credit, hosted

Call `risk_desk_status` first to check availability, input limits and
reporting conventions. Then use the connected hosted Risk Desk MCP.
Discover the input schema instead of guessing field names. No local
runtime or market-data feed is needed.

- `risk_credit_asrf`: the Vasicek asymptotic single risk factor loss
  quantile. Exact for an infinitely granular book; it ignores name
  concentration.
- `risk_credit_copula`: a seeded Monte Carlo of the same one-factor model
  for the actual list of obligors. It captures concentration and gives
  Expected Shortfall.

For a requested demonstration, omit `request` to use the shipped synthetic
example. Label the result as synthetic; its `data_origin` is
`synthetic_demo`. For the user's own book, pass it in `request`; never
substitute the demo when input is missing or invalid. Ask only for
missing required fields.

Report degraded status, its reason, currency, confidence and horizon
before the figures. Preserve source and as-of information. If the service
is unavailable, report the failure without inventing results. For the
copula, degraded means too little tail probability mass: suggest more
scenarios within the limits that `risk_desk_status` states.

For supplied data, each obligor needs a unique id, exposure in the request
currency, PD over the stated horizon and LGD. The ASRF also needs each
obligor's asset correlation; the copula needs each factor loading, the
scenario count and a seed. PD, LGD, correlation and loadings are the
user's inputs: the tools do not estimate them and you must not invent
them. Use a supervisory correlation only if the user asks, and say so.

Report credit VaR, expected loss and unexpected loss; for the copula also
Expected Shortfall, scenarios and seed, and for the ASRF the largest
contributions, which add up to the credit VaR. Loss is positive.
Unexpected loss is credit VaR minus expected loss, not the standard
deviation of loss, which the copula reports separately.

Neither tool gives IRB capital or a risk weight: no maturity adjustment,
no CRE31.7 correlation multiplier and no PD or LGD floor. For a
concentrated book the ASRF understates the loss quantile. The copula
carries Monte Carlo error; quote its seed and scenario count. Default mode
only: no rating migration or spread loss, fixed LGD and one systematic
factor. A loss quantile is a model output, not a backtested forecast.

Before sending user data, establish that the user is permitted to share
it with a hosted service. Existing permission in the conversation is
sufficient. `data_mode` records their declaration; it is not a rights
certificate and the service does not check it.

Counterparty XVA is not available here. It needs a trusted local ORE
project directory, which a remote endpoint cannot read. Point the user at
the local `risk-desk` plugin for that.

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
