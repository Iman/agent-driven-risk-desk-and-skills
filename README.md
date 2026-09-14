# Risk Desk

Risk Desk measures the loss side of a book and shows its working. It
calculates historical VaR and Expected Shortfall from supplied P&L,
gross and net exposure for signed linear positions, explicit stress
scenarios that carry no probability, and counterparty exposure and XVA
through a local Open Source Risk Engine project. The CLI and 4 local MCP
tools call the same runtime functions, so an agent and a person get the
same numbers with the same provenance, units, assumptions and degraded
flag attached. 5 plugin skills cover these tasks and setup.

[![Tests](https://img.shields.io/badge/tests-72%20collected-blue)](docs/IMPLEMENTATION.md)
[![Python](https://img.shields.io/badge/python-3.13%20tested-blue)](#get-started)
[![License](https://img.shields.io/badge/license-PolyForm%20Noncommercial-blue)](LICENSE)

## See the desk

![Stress contributions and a P&L distribution with VaR and Expected Shortfall marked, drawn from synthetic example inputs](docs/images/report-energy-stress.png)

One page, written by `riskdesk report`, from the synthetic energy book in
`examples/`. Synthetic example inputs, not market data and not a record of
any position. The page states its sign convention, prints its degraded
flag whether or not it is set, and embeds its own styling and charts, so it
opens with no network.

## Get started

Requirements: Git, and a Python the project supports. `pyproject.toml`
declares 3.11 or later; the pinned dependency set and the ORE wheel were
tested on CPython 3.13, macOS ARM64.

```sh
git clone https://github.com/Iman/agent-driven-risk-desk-and-skills-.git
cd agent-driven-risk-desk-and-skills-
./install.sh
./demo.sh
```

`install.sh` creates `.venv`, installs the package with its development
extra, attempts the optional ORE extra and says plainly whether that
worked, then runs the tests. `demo.sh` runs every command over the 6
example input files and prints what each result means. Neither script
prints colour, neither reaches the network beyond pip, and both exit
non-zero on any failure.

The plugin is [plugins/risk-desk](plugins/risk-desk). It starts
`riskdesk-mcp` through PATH, so either activate the environment in the
client's launch environment or configure the client with the absolute path
to the installed executable. Installing the plugin does not install the
runtime. The server speaks stdio and makes no market-data or broker
requests.

## Ask your agent

With the plugin installed, these are things a person types.

| Ask this | Skill | Tool it calls |
| --- | --- | --- |
| "Here is a year of daily P&L in GBP. What is my 99% one-day VaR and Expected Shortfall, and is the sample big enough to say?" | `risk-tail` | `risk_tail` |
| "Take `examples/energy_book.json`. What is my gross and net exposure, my leverage against NAV, and which asset is the biggest share of gross?" | `risk-portfolio` | `risk_exposure` |
| "Apply the two shapes in `examples/energy_stress.json` and tell me the loss, the stressed NAV, and the three positions that hurt most in each." | `risk-stress` | `risk_stress` |
| "Run this ORE project and give me the CVA and DVA. Tell me first whether ORE reported any error and which adjustments were actually enabled." | `risk-xva` | `risk_xva` |

Each skill states the sign convention and the degraded status before the
numbers, because a loss figure without them is unreadable.

## What it computes

The input contracts are in
[plugins/risk-desk/references/contracts.md](plugins/risk-desk/references/contracts.md).
The Pydantic models in `src/riskdesk/models.py` are the executable version;
unknown fields and nonfinite numbers are rejected.

- **Tail risk** consumes monetary P&L observations that already span the
  stated horizon. It uses skfolio's empirical quantile and fractional-tail
  Expected Shortfall. Positive VaR and ES mean loss; negative values are
  preserved as gains and are not floored at zero. No square-root-of-time
  scaling is applied and no observation is dropped.
- **Exposure** requires signed linear-position market values already
  translated into one base currency. Gross counts absolute values before
  offsetting; net does not. Leverage divides by the supplied NAV.
- **Stress** requires an explicit return shock for every asset in every
  scenario. It reports P&L, loss, stressed NAV and per-position
  contributions. It attaches no probability to a scenario.
- **ORE exposure and XVA** preserves upstream column names, currency,
  requested adjustment flags and unavailable values. Netting-set and trade
  rows overlap, so they are never summed, and a zero in a disabled column
  is not a result. See [docs/ORE.md](docs/ORE.md) for the pinned
  reproduction, what it does and does not establish, and the rules for
  running your own project. Version 1.8.16.0 was tested on CPython 3.13,
  macOS ARM64; install `.` without the extra for everything else.

Every core result carries provenance, a SHA-256 of its input, its currency,
its assumptions and a degraded flag. A small tail sample raises a warning.
That warning is a reporting threshold, not a confidence interval and not
forecast validation.

## What it does not claim

This is research tooling. It reads files you give it, writes files, and
places no orders; it opens no broker connection and fetches no market data.

The scope is historical VaR and Expected Shortfall, linear exposure,
explicit stress, and the ORE adapter. It does not establish regulatory
compliance, forecast skill, wrong-way-risk calibration, liquidity survival,
SIMM permissions, or coverage of every instrument ORE supports. A
historical loss measure is not risk-neutral valuation, and a regression
value that reproduces is not model validation. Options, nonlinear margin
and credit migration do not fit the linear contract; use a configured
valuation model for those, not this one.

## Development

```sh
.venv/bin/python -m pytest -q --color=no          # 72 tests, none skipped
.venv/bin/python scripts/evidence.py check        # documents match the record
.venv/bin/python -m build
```

Tests are separated by marker: `-m unit` runs in process with no subprocess
and no socket, `-m integration` runs the real scripts and the real stdio
transport, and `-m validation` checks the repository and its documents.

`scripts/evidence.py` is the part worth a minute. Every figure quoted in
this README and in `docs/IMPLEMENTATION.md` is recorded in
`docs/evidence.json` with where it came from, and `check` fails when a
document and the record disagree. A validation test runs that check, so
the suite goes red when the prose drifts from the repository. Figures the
recorder counted here are marked `measured`; the ORE regression values,
which came from a run against an upstream checkout that is not part of this
repository, are marked `pinned` with the date they were observed.

`scripts/screenshot_report.py` regenerates the image above from a page it
writes in the same run. It needs Playwright, which is not a project
dependency, so the image is committed and regenerating it is deliberate.

## Licensing

Risk Desk's own code is source-available under
[PolyForm Noncommercial 1.0.0](LICENSE). Upstream software keeps its own
licence, copyright notice and disclaimer: 79 upstream notice files from 47
distributions are retained unchanged in [notices/](notices/) and travel in
the wheel, the source archive and the plugin package. See
[THIRD-PARTY.md](THIRD-PARTY.md) for the credits, and note that market-data
rights and methodology rights are separate from software licences.
