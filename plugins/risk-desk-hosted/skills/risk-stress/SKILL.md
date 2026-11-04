---
name: risk-stress
description: Revalue linear positions under supplied asset-return scenarios, replay a dated window from the user's own prices, list the dated scenario library, find the most plausible shock for a target loss, or scale a scenario to a target loss, over the hosted Risk Desk MCP. Use for scenario loss and contribution analysis.
---

# Risk Stress, hosted

Call `risk_desk_status` first to check availability, input limits and
reporting conventions. Then use the connected hosted Risk Desk MCP.
Discover the input schema instead of guessing field names.
No local runtime or market-data feed is needed.

- `risk_stress`: revalue explicit scenarios.
- `risk_stress_replay`: replay a dated window from the user's prices.
- `risk_scenario_library`: the dated windows (Lehman 2008, COVID 2020,
  UK gilt and LDI 2022), with sources. No arguments; dates only, no prices.
- `risk_reverse_stress`: the most plausible shock for a target loss under
  the user's covariance.
- `risk_scenario_scale`: the multiple of one scenario that hits a target
  loss.

For a requested demonstration, omit `request` to use the shipped synthetic
example. Label the result as synthetic. For the user's own book, pass the
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

A replay needs the user's own licensed price levels with a level on both
window dates; nothing is interpolated or filled. A replay through a proxy
series is degraded and names each proxy. A worst peak-to-trough replay
takes each asset's worst fall separately; do not call it the book's worst
loss in the window. For reverse stress, report the shocks, Mahalanobis
distance, solution and binding floors; the distance ranks plausibility,
it is not a probability, and `loss_exceedance_probability_if_normal`
holds only under joint normal returns with mean zero and the supplied
covariance, so say so in the same sentence. For scaling, report the
multiple; it is a distance along one scenario, not a probability. Name the
user as the source of prices, covariance and floors.

The model is linear. Do not apply it to option premium values, credit
migration or nonlinear margin calls.

Before sending user data, establish that the user is permitted to share
it with a hosted service. Existing permission in the conversation is
sufficient. `data_mode` records their declaration; it
is not a rights certificate and the service does not check it.

Counterparty XVA is not available here. It needs a trusted local ORE
project directory, which a remote endpoint cannot read. Point the user at
the local `risk-desk` plugin for that.
