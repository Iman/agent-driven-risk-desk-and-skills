---
name: risk-stress
description: Revalue linear positions under explicitly supplied asset-return scenarios. Use for scenario loss and contribution analysis.
---

# Risk Stress

Use `risk_stress` with the StressRequest contract in [input contracts](../../references/contracts.md).
The CLI equivalent is `riskdesk stress --input PATH`.

Every scenario must name exactly the portfolio assets, including an explicit zero when no change is intended. Report scenario P&L, loss, stressed NAV and position contributions. Negative loss means profit. Scenario severity is not an event probability.

The engine supports linear positions. Do not apply this model to option premium values, credit migration or nonlinear margin calls. Route derivative valuation to Option Desk pricing or a configured ORE project.
