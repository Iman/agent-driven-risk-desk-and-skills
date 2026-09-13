---
name: risk-xva
description: Run a trusted local ORE project for counterparty exposure and valuation adjustments. Use for ORE CVA, DVA and funding reports, not historical VaR.
---

# Risk Xva

Use `risk_xva` with an explicit local project directory, relative config path, new output directory outside the project, and data_mode of synthetic, user-licensed or upstream-example. Read [input contracts](../../references/contracts.md) for the supported ORE project boundary.
The CLI equivalent is `riskdesk xva --project PROJECT --config Input/ore.xml --output NEW_OUTPUT --data-mode synthetic`.

Run only a user-provided or inspected local project. The ORE configuration determines instruments, curves, counterparties, CSA/netting, simulation and requested adjustments. Do not invent these inputs. Both simulation and XVA must be active; an old cube is not reused.

Report any ORE error as a failed run. Preserve ORE column names and signs. Identify the base currency and requested adjustment flags. Disabled metrics, null values and zero results are distinct. Netting-set and trade rows overlap and must not be summed together.

Positive exposure is not signed mark-to-market, and risk-neutral XVA is not a real-world VaR forecast. The included upstream example validates execution and report translation only. It does not validate all models, regulatory capital, wrong-way risk, SIMM rights or a user's calibration.
