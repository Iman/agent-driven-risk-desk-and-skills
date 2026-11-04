---
name: risk-frtb
description: Compute Basel FRTB capital pieces from figures a bank has already produced, covering IMCC, aggregate IMA capital and RWA, the P&L attribution zone, VaR backtesting counts and FX SBM delta and vega capital, over the hosted Risk Desk MCP. Use for MAR21, MAR32 or MAR33 questions, not to estimate ES or VaR from market data.
---

# Risk FRTB, hosted

Call `risk_desk_status` first to check availability, input limits and
reporting conventions. Then use the connected hosted Risk Desk MCP.
Discover the input schema instead of guessing field names. If a tool is
not listed, say so; never produce a capital figure by hand.

- `risk_frtb_imcc`: liquidity-adjusted, stress-scaled ES and IMCC from
  10-day ES cascades per liquidity horizon (MAR33).
- `risk_frtb_ima_capital`: aggregate IMA capital with the multiplier, the
  amber-desk surcharge and RWA (MAR33, MAR32.9).
- `risk_frtb_pla`: P&L attribution Spearman and Kolmogorov-Smirnov metrics
  and the desk zone from 250 daily RTPL and HPL values (MAR32).
- `risk_frtb_backtest`: VaR exception counts over 250 days, as a desk
  verdict at 97.5% and 99% or a bank zone at 99% (MAR32).
- `risk_frtb_sbm_fx`: standardised FX delta and vega capital (MAR21).

For a requested demonstration, omit `request` to use the shipped synthetic
example. Label the result as synthetic; its `data_origin` is
`synthetic_demo`. For the user's own figures, pass them in `request`;
never substitute the demo when input is missing or invalid. Ask only for
missing required fields, and ask for the MAR21.88 specified-pair election
rather than assuming it.

Report degraded status and its reason first. The FX SBM result is degraded
whenever vega is supplied, because curvature capital is not computed. Then
give the verdict asked about with its rule (PLA zone, desk pass, bank zone
and multiplier, binding SBM scenario, or aggregate capital and RWA), the
currency, as-of date and horizon (10-day base ES for IMCC, one-day P&L for
the tests), and the figures that drove it. Preserve source and as-of.

Capital, ES, VaR, SES, DRC and standardised charges are positive amounts.
P&L is signed, positive is profit. An exception is a loss strictly greater
than VaR; a missing P&L or VaR counts as one. Sensitivities are signed and
netted per risk factor before weighting.

These are research calculations over supplied inputs, not a regulatory
submission. Model approval, risk factor eligibility, stress period choice
and desk structure are outside them. Not computed: ES itself, the
non-modellable stress capital and default risk model (both taken as
inputs), the 10% eligibility criterion, PLA zone transitions, SBM
curvature, risk classes other than FX, the standardised default risk
charge and the residual risk add-on. Do not call the FX SBM figure the
standardised approach capital. Two readings are interpretations and the
result says so: the MAR33.6 floor applied to each risk-class ratio, and
the MAR32.19 limits read as more than 12 and more than 30.

Before sending user data, establish that the user is permitted to share
it with a hosted service. Existing permission in the conversation is
sufficient. `data_mode` records their declaration; it is not a rights
certificate and the service does not check it.

Estimating ES, VaR or sensitivities from market data is not available
here. Counterparty XVA is also not available here; it needs a local ORE
project and the local `risk-desk` plugin.
