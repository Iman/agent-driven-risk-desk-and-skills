# Initial implementation evidence

## UNKNOWN

No licensed production portfolio or historical option dataset was supplied.
The initial integration does not establish forecast accuracy, regulatory
compliance, wrong-way-risk calibration or coverage of all ORE instruments.
The pinned dependency lock is for CPython 3.13 on macOS ARM64 only.

## VERIFIED

Observed on 2026-09-13 London time:

- Risk Desk: 25 tests passed. They cover monetary signs, fractional-tail
  weighting, exact quantile boundaries, validation failures, short-position
  stress, duplicate identifiers, stale-cube refusal, error handling, CLI
  failure output and a real MCP stdio request/response.
- Quantile regression: at 95% confidence with P&L -20 through -1, skfolio's
  direct binary boundary selected VaR 19. A test observed that failure.
  The adapter now selects VaR 20 and ES 20. It computes the intended tail
  mass in decimal arithmetic and moves the backend confidence one float
  toward one only when an integral boundary was rounded upward. Both risk
  measures still come from skfolio. `backend_confidence` records the value
  actually passed to the backend.
- ORE 1.8.16.0: the pinned 1,000-sample, seed-42 upstream example produced
  82 netting-set exposure dates, two overlapping XVA rows, CVA
  42600.768114722014 EUR and DVA 62036.0247267215 EUR, with no reported errors.
  These are numerical regression values, not independent model validation.
- The first ORE example reported missing spreads on two security curves
  unused by its swap. The reproducible fixture removes those two curves.
  The adapter refuses any remaining ORE error.
- ORE's `nullDouble()` sentinel was observed in disabled trade-level
  adjustments. The worker now emits JSON null for that exact sentinel;
  unavailable MVA was checked in the real rerun.
- All five Risk Desk skills and its plugin manifest passed their validators.
- The tested dependency tree contains 47 upstream distributions. All had
  located notices. The wheel includes all 79 copied notice files. Exact
  hashes for the 47 downloaded wheels are in `wheel-hashes.json` and the
  platform-specific requirements lock.

Commands:

```sh
python -m pytest -q --color=no --junitxml=artifacts/tests.xml
python scripts/ore_smoke.py --upstream ORE_CHECKOUT --work NEW_WORK_DIRECTORY
python -m build
python scripts/package_plugin.py
```

The source checkout for the ORE test was release v1.8.16.0, commit
`b1f239332fdd51e5c514dd6de34a665fe0ff8326`. The test script verifies this
revision before copying example inputs. The external example data is not
part of the Risk Desk distribution.

## ASSUMPTIONS

Users supply complete, consistently dated and currency-converted inputs.
`data_mode` records their declaration. Core historical observations already
span the requested horizon. Linear scenarios are specified shocks, not
estimated probabilities. The ORE project determines models and conventions.

## PLAN

Extend only against a named instrument, data source or model requirement.
Next validation candidates include discrete dividends, assignment,
collateral agreements, calibration checks and a licensed historical dataset.
Do not treat every capability in the earlier research shortlist as shipped.
