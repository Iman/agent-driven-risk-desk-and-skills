---
name: risk-backtest
description: Backtest a supplied VaR series, and optionally an Expected Shortfall series, against realised P&L over the hosted Risk Desk MCP. Use to judge a forecast record with exception counts, Kupiec, Christoffersen, the Basel traffic light and the Acerbi-Szekely ES test, not to compute VaR.
---

# Risk Backtest, hosted

Call `risk_desk_status` first to check availability, input limits and
reporting conventions. Then use `risk_backtest` on the connected hosted
Risk Desk MCP. Discover its input schema instead of guessing field names.
No local runtime or market-data feed is needed.

For a requested demonstration, omit `request` to use the shipped synthetic
example. Label the result as synthetic; its `data_origin` is
`synthetic_demo`. For the user's own record, pass it in `request`; never
substitute the demo when input is missing or invalid. Ask only for
missing required fields.

Report degraded status, its reason, currency, horizon, confidence and sign
convention before the figures. Preserve source and as-of information.
If the service is unavailable, report the failure without inventing results.

For supplied data, require realised P&L in time order (positive is
profit) and, for each row, the VaR forecast made before that P&L was known
(positive is a loss), with confidence and horizon. An ES test also needs
an ES forecast per row, each above its VaR, and the null family (normal,
or Student-t with its degrees of freedom).

Report, in order: exceptions against expected exceptions; the Basel zone,
or the reason it is unavailable; Kupiec, Christoffersen independence and
conditional coverage, each with statistic and p-value; then the ES test
with its null, simulations, seed and Monte Carlo standard error.

An exception is a realised loss strictly greater than VaR. The Basel zone
is given only for one-day 99% VaR and is not a capital figure; no
multiplier is reported. Z2 is zero in expectation when forecasts are
right; negative values mean risk was understated, and its p-value is the
left tail under the stated null, not under the forecaster's own model.
Kupiec and Christoffersen p-values are asymptotic chi-square.

A test that does not reject has not validated the model. With few
expected exceptions the tests have little power; say how many were
expected. This is a research calculation, not a regulatory submission and
not investment advice.

Before sending user data, establish that the user is permitted to share
it with a hosted service. Existing permission in the conversation is
sufficient. `data_mode` records their declaration; it is not a rights
certificate and the service does not check it.

Producing the VaR forecasts is not available here: this tool tests a
record, it does not build one. Use `risk_tail` for a VaR figure.
Counterparty XVA is also not available here; it needs a local ORE project
and the local `risk-desk` plugin.
