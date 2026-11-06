---
name: risk-derivatives
description: Calculate cash Greeks, spot and vol scenario grids, and historical full-revaluation VaR and Expected Shortfall for a book of linear positions and European options on spot or futures underlyings, over the hosted Risk Desk MCP. Use when a book holds options, not for American or exotic options or option quotes.
---

# Risk Derivatives, hosted

Call `risk_desk_status` first to check availability, input limits and
reporting conventions. Then use the connected hosted Risk Desk MCP.
Discover the input schema instead of guessing field names. No local
runtime or market-data feed is needed.

- `risk_derivatives_greeks`: cash delta, gamma, vega, theta and rho now.
- `risk_derivatives_grid`: full revaluation over spot and vol shocks,
  against delta-gamma and delta-gamma-vega.
- `risk_derivatives_historical`: full-revaluation P&L, VaR and ES under
  supplied spot returns and vol changes.

For a requested demonstration, omit `request` to use the shipped synthetic
example. Label the result as synthetic; its `data_origin` is
`synthetic_demo`. For the user's own book, pass it in `request`; never
substitute the demo when input is missing or invalid. Ask only for
missing required fields.

Report degraded status, its reason, currency and sign convention before
the figures. Preserve source and as-of information. If the service is
unavailable, report the failure without inventing results. For the
historical tool, also report the time mode, horizon, scenarios without vol
changes and options settled within the horizon; each changes what the VaR
means.

Spot underlyings are priced with Black-Scholes-Merton and futures with
Black-76. Every position needs a signed quantity and an explicit
multiplier; there is no default, because a missing 100 is a hundredfold
error. An option needs kind, strike, implied vol per 1.00 (0.20, not 20),
a continuously compounded rate and one of expiry or year fraction; on a
spot underlying it also needs a carry yield (0 if none), on a future it
takes none. Prices are already in the stated currency. Never invent a
price, vol or term.

Units: cash delta per 1.00 relative move; cash gamma as the change in cash
delta for a 1% rise; vega per 0.01 of implied vol; theta per calendar day,
negative is decay; rho per 0.01 of the rate. Positive P&L is profit; the
tail block reports VaR and ES as losses, and a negative value is a gain.
Approximation error is approximation minus full revaluation.

Totals add underlyings: no cross-gamma, and total vega moves every vol
together. The approximations have no vanna or vomma. Grid cells move every
underlying and every vol by the same shock; they are not correlated
scenarios. A fixed time mode excludes theta over the horizon; decay
includes it. An option expiring inside the horizon is valued at its
payoff, not rolled. Model values are not quotes, and European exercise
with one flat vol per option is assumed. Do not scale a one-day result to
ten days.

Before sending user data, establish that the user is permitted to share
it with a hosted service. Existing permission in the conversation is
sufficient. `data_mode` records their declaration; it is not a rights
certificate and the service does not check it.

Implied volatility solving, American and exotic options, and Counterparty
XVA are not available here. XVA needs a trusted local ORE project
directory and the local `risk-desk` plugin.

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
