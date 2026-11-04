---
name: risk-liquidity
description: Estimate days to liquidate each asset at a participation rate of average daily traded value, the holdings schedule by day, the exogenous bid-ask spread cost and liquidity-adjusted VaR, over the hosted Risk Desk MCP. Use to ask how long a linear book takes to exit or what the spread adds to VaR, not for market impact.
---

# Risk Liquidity, hosted

Call `risk_desk_status` first to check availability, input limits and
reporting conventions. Then use `risk_liquidity` on the connected hosted
Risk Desk MCP. Discover its input schema instead of guessing field names.
No local runtime or market-data feed is needed.

For a requested demonstration, omit `request` to use the shipped synthetic
example. Label the result as synthetic; its `data_origin` is
`synthetic_demo`. For the user's own book, pass it in `request`; never
substitute the demo when input is missing or invalid. Ask only for
missing required fields.

Report degraded status, its reason, currency and sign convention before
the figures. When P&L is supplied, degraded names every asset that takes
longer to exit than the VaR horizon. Then give the longest days to
liquidate and the slowest assets, the schedule at the days the user cares
about, the cost of liquidity, and when present VaR and liquidity-adjusted
VaR with confidence and horizon. Preserve source and as-of information.
If the service is unavailable, report the failure without inventing results.

For supplied data, the book is signed linear positions in the stated
currency with an explicit NAV. Require the participation rate, the spread
multiplier (no default; ask for it and say what it was), and for exactly
every asset its average daily traded value in the base currency, mean
relative spread and spread volatility. Relative spread is (ask - bid) /
mid, so 0.002 is 20 basis points. P&L, confidence and horizon are optional
and go together, as for `risk_tail`. Never invent a volume or a spread.

Cost of liquidity and VaR are positive losses. Short positions pay the
half spread too, so values are absolute. Days are days of average traded
value, not calendar days.

VaR is at the P&L horizon and the spread cost is a one-off exit cost;
neither is rescaled to the liquidation period. When an asset takes longer
to exit than the horizon, say that the liquidity-adjusted VaR does not
cover the extra days. The spread add-on is market-wide spread risk, not
the price impact of selling a large block, which can be far larger. This
liquidity-adjusted VaR adds the spread cost to historical VaR, while the
1999 Bangia et al. paper used parametric VaR. Do not present the paper's
range for the multiplier as a default. This is research output, not
investment advice.

Before sending user data, establish that the user is permitted to share
it with a hosted service. Existing permission in the conversation is
sufficient. `data_mode` records their declaration; it is not a rights
certificate and the service does not check it.

Market impact modelling and Counterparty XVA are not available here. XVA
needs a trusted local ORE project directory and the local `risk-desk`
plugin.
