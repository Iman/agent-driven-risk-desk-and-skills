---
name: risk-limits
description: Grade a limit set on gross, net, leverage, gross share, VaR, Expected Shortfall or a named stress loss against Risk Desk results, and run a pre-trade what-if that revalues a linear book with proposed trades, over the hosted Risk Desk MCP. Use for limit utilisation and what a proposed trade would do, not for orders or recommendations.
---

# Risk Limits, hosted

Call `risk_desk_status` first to check availability, input limits and
reporting conventions. Then use the connected hosted Risk Desk MCP.
Discover the input schema instead of guessing field names. No local
runtime or market-data feed is needed.

- `risk_limits` grades each limit against results that `risk_exposure`,
  `risk_tail` and `risk_stress` already returned. Pass those results
  unchanged; do not edit or recompute them.
- `risk_what_if` applies proposed trades to a book, recomputes exposure,
  and stress and tail when their inputs are given, then grades the limits
  on the book after the trades.

For a requested demonstration, omit `request` to use the shipped synthetic
example. Label the result as synthetic; its `data_origin` is
`synthetic_demo`. For the user's own book and limits, pass them in
`request`; never substitute the demo when input is missing or invalid, and
never grade the user's limits against a demo result. Ask only for missing
required fields.

Report degraded status and its reason first. Then the overall status and
status counts; every breach and warning with value, limit and
utilisation; every limit not evaluated, with its reason; and for VaR and
ES the confidence and horizon behind the value. For a what-if, give the
change first, then before and after, then the limits after. Preserve
source and as-of information. If the service is unavailable, report the
failure without inventing results.

Each limit has a unique name, a metric, a direction (max or min), a hard
limit and an optional warning on the safe side of it. A gross share limit
names its asset; a stress loss limit names its scenario. A what-if trade
is a signed change in market value; a sale of a long is negative.

Overall status is the worst of breach, warning, not evaluated and within,
so a book with an unevaluated limit is never within. Status decides, not
utilisation; utilisation is null for a zero limit or an overflowing ratio.
Overflow carries a reason and degraded status. A result in another
currency is not evaluated; a differing as-of date is evaluated and
flagged, so give both dates. Loss is positive for VaR, ES and stress loss,
and a negative value is a gain.

A what-if is a revaluation at as-of prices, cash-financed, with no costs,
no market impact and unchanged NAV; it is not an execution estimate. Its
VaR and ES assume each linear position's historical P&L scales with its
value; say so whenever quoting them. Never recommend a trade, size or
hedge. This is research output, not investment advice.

Before sending user data, establish that the user is permitted to share
it with a hosted service. Existing permission in the conversation is
sufficient. `data_mode` records their declaration; it is not a rights
certificate and the service does not check it.

Placing or routing orders is not available here, and neither is
Counterparty XVA, which needs a local ORE project and the local
`risk-desk` plugin.

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
