# Risk Desk

Risk Desk calculates historical VaR and Expected Shortfall, linear portfolio
exposure, explicit stress scenarios, and counterparty exposure/XVA through
ORE. The CLI and four local MCP tools call the same runtime functions.
Five plugin skills cover these tasks and setup.

## Install

Use a separate Python environment for Risk Desk:

```sh
python3 -m venv .venv
.venv/bin/python -m pip install '.[xva]'
.venv/bin/riskdesk tail --input examples/tail.json
.venv/bin/riskdesk exposure --input examples/portfolio.json
.venv/bin/riskdesk stress --input examples/stress.json
```

The ORE extra requires an upstream wheel supported on your Python/platform
combination. Version 1.8.16.0 was tested on Python 3.13, macOS ARM64. Install
`.` without the extra if you need only historical and linear portfolio risk.

The plugin is [plugins/risk-desk](plugins/risk-desk). It starts
`riskdesk-mcp` through PATH. Activate the environment in the client launch
environment or configure the client to use the installed executable's
absolute path. Plugin files do not install the runtime automatically.
The MCP server uses stdio and makes no market-data or broker requests.

## Input and result conventions

See [input contracts](plugins/risk-desk/references/contracts.md).
The Python models in `src/riskdesk/models.py` are the executable contracts.

- Tail risk consumes monetary P&L observations that already span the stated
  horizon. It uses skfolio's empirical quantile and fractional-tail ES.
  Positive VaR/ES means loss; negative values are preserved as gains.
- Portfolio exposure requires signed linear-position market values already
  translated into one base currency. Gross exposure counts absolute values
  before offsetting. Leverage divides by the supplied NAV.
- Stress requires explicit return shocks for every asset. It reports P&L,
  loss, stressed NAV and position contributions. It assigns no probability.
- ORE reports preserve upstream column names, currency, requested adjustment
  flags and unavailable values. Netting-set and trade rows overlap. Do not
  sum them together or interpret disabled zero columns as enabled models.

Every core result includes provenance, an input hash, units through its
currency, assumptions and a degraded flag. Small tail samples receive a
warning. This warning is not a confidence interval or forecast validation.
Options, nonlinear margin and credit migration do not fit the linear
portfolio contract; use a configured valuation model for those exposures.

## ORE exposure and XVA

```sh
.venv/bin/riskdesk xva --project INPUT_BUNDLE --config Input/ore.xml --output NEW_OUTPUT --data-mode user-licensed
```

Replace the paths with a trusted, inspected ORE project. All referenced
inputs must be inside the bundle. Output must be new and outside it. Both
simulation and XVA must be active. The adapter uses a separate process,
forces `continueOnError=false`, and refuses a summary if ORE reports errors.
This process boundary is not a sandbox for hostile configurations.

To reproduce the upstream example, obtain ORE v1.8.16.0 with its
`Examples/Input` and `Examples/ORE-Python/Input` directories, then run:

```sh
.venv/bin/python scripts/ore_smoke.py --upstream ORE_CHECKOUT --work NEW_WORK_DIRECTORY
```

The script requires the pinned revision recorded in its source and credits.
It retains 1,000 simulation samples and seed 42, creates a self-contained
input copy, and removes two unused security curves with missing spreads.
Its data provenance is `upstream-example`. The observed report has 82
exposure dates and CVA 42600.768114722014 EUR. That is a pinned regression
result, not independent verification of ORE's financial models.

## Validation and limits

```sh
.venv/bin/python -m pip install '.[dev]'
.venv/bin/python -m pytest -q --color=no
.venv/bin/python -m build
```

See [implementation evidence](docs/IMPLEMENTATION.md) for observed checks.
The initial scope does not establish regulatory compliance, forecast skill,
wrong-way-risk calibration, liquidity survival, SIMM permissions, or coverage
of every instrument supported by ORE. No broker orders are submitted.

Risk Desk is source-available under [PolyForm Noncommercial 1.0.0](LICENSE),
matching Option Desk. [Credits and upstream notices](THIRD-PARTY.md) remain
under their original terms.

# agent-driven-risk-desk-and-skills-
