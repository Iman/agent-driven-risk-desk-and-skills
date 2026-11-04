---
name: risk-portfolio
description: Aggregate gross and net exposure, leverage and asset concentration for linear positions in one base currency.
---

# Risk Portfolio

Use `risk_exposure` with the PortfolioRequest contract in [input contracts](../../references/contracts.md).
The CLI equivalent is `riskdesk exposure --input PATH`.

Require signed market values already translated into the stated currency and an explicit NAV. Confirm that each position is a linear asset. Options require sensitivities or full revaluation; premium market value is not delta exposure. For a book with European options use `risk_derivatives_greeks`, `risk_derivatives_grid` and `risk_derivatives_historical` (the risk-derivatives skill), whose book contract is separate from this one.

Explain net versus gross exposure. Concentration uses absolute position values before offsetting; leverage uses NAV. Do not describe these amounts as counterparty EAD or regulated capital.
