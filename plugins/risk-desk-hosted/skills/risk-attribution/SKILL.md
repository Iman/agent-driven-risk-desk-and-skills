---
name: risk-attribution
description: Estimate a covariance matrix from supplied returns, split VaR and Expected Shortfall into per-position contributions, and split portfolio variance into factor and idiosyncratic parts, over the hosted Risk Desk MCP. Use to find which positions or factors drive the risk.
---

# Risk Attribution, hosted

Call `risk_desk_status` first to check availability, input limits and
reporting conventions. Then use the tool that answers the question on the
connected hosted Risk Desk MCP. Discover its input schema instead of
guessing field names. No local runtime or market-data feed is needed.

- `risk_covariance`: sample, EWMA or Ledoit-Wolf covariance, volatility
  and correlation of a return history.
- `risk_var_attribution`: parametric normal VaR and ES with per-position
  contributions and incremental VaR.
- `risk_es_attribution`: historical-simulation ES with per-position
  contributions.
- `risk_factor_exposure`: factor betas and the systematic and
  idiosyncratic split of portfolio variance.

For a requested demonstration, omit `request` to use the shipped synthetic
example. Label the result as synthetic; its `data_origin` is
`synthetic_demo`. For the user's own data, pass it in `request`; never
substitute the demo when input is missing or invalid. Ask only for
missing required fields.

Report degraded status, its reason, currency, horizon, method and the
observations used before the figures. Preserve source and as-of
information. If the service is unavailable, report the failure without
inventing results.

For supplied data, positions are signed linear market values already in
the stated currency, each naming an asset in the asset list. Return rows
are simple returns, oldest first, one value per asset, and each row already
spans the stated horizon; nothing rescales them. Never invent a missing
return, covariance entry or factor return. EWMA needs a decay from the
user; there is no default.

Loss is positive. A negative contribution means the position lowers risk
at the margin, a hedge in this book; a share above 100 percent is
possible. Component VaR sums to VaR and component ES to ES; incremental
VaR does not sum to VaR. Systematic plus idiosyncratic variance equals the
in-sample variance of portfolio P&L. Factor exposure is currency P&L per
1.00 factor return.

Parametric results assume normal P&L with zero mean; call them normal VaR
and do not mix them with `risk_tail` figures without naming both methods.
A covariance flagged not positive definite was not repaired; offer
Ledoit-Wolf instead of altering it. When historical ES is degraded for a
tied tail boundary, the total is sound but the split depends on input
order. R squared and betas are in-sample, not forecasts. None of this is
regulatory capital, a validated model or advice.

Before sending user data, establish that the user is permitted to share
it with a hosted service. Existing permission in the conversation is
sufficient. `data_mode` records their declaration; it is not a rights
certificate and the service does not check it.

Counterparty XVA is not available here. It needs a trusted local ORE
project directory, which a remote endpoint cannot read. Point the user at
the local `risk-desk` plugin for that.
