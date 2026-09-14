# Initial implementation evidence

## UNKNOWN

No licensed production portfolio or historical option dataset was supplied.
The initial integration does not establish forecast accuracy, regulatory
compliance, wrong-way-risk calibration or coverage of all ORE instruments.
The pinned dependency lock is for CPython 3.13 on macOS ARM64 only.

Not measured in the 2026-09-14/15 session, and therefore not claimed:

- The ORE example was not re-run. No upstream ORE checkout at revision
  `b1f239332fdd51e5c514dd6de34a665fe0ff8326` was present on the machine,
  and `scripts/ore_smoke.py` verifies that revision before copying inputs.
  The exposure, CVA and DVA figures below remain the 2026-09-13
  observation, carried forward and marked `pinned` in `docs/evidence.json`.
  The ORE wheel installed, which is a different and smaller claim.
- Python 3.11 and 3.12 were not exercised. `pyproject.toml` declares 3.11
  or later; only CPython 3.13.14 was run.
- No behaviour was observed on Linux or on Windows.
- Unit line coverage was not measured, so no coverage figure appears in
  README.md and there is no coverage gate.
- No mutation harness exists, so no mutation figure appears in README.md.

## VERIFIED

Observed overnight on 2026-09-14 into 2026-09-15 London time, on
macOS ARM64 (Darwin 25.6.0):

- Environment. CPython 3.13.14 at
  `/Users/iman/.local/share/uv/python/cpython-3.13-macos-aarch64-none/bin/python3.13`.
  The system default is 3.14.7, which the pinned stack was not tested on
  and which was not used. `python3.13 -m venv .venv` then
  `.venv/bin/python -m pip install '.[dev]'` installed 53 distributions,
  riskdesk itself included, and built `riskdesk-0.1.0-py3-none-any.whl`.
- Baseline before any change in this session:
  `.venv/bin/python -m pytest -q --color=no` reported `25 passed in
  18.39s`, with no failures and no skips.
- The optional ORE extra installed cleanly on this machine.
  `.venv/bin/python -m pip install '.[xva]'` installed
  `open_source_risk_engine-1.8.16.0-cp313-cp313-macosx_14_0_arm64.whl`
  (61.8 MB). The suite then reported `25 passed in 2.30s`.
- After this session's work the suite reports 72 tests collected, with no
  failures and no skips. By marker: 50 unit, 16 integration, 6 validation.
  The unit tests start no subprocess and open no socket.
- `scripts/evidence.py record` wrote 13 figures to `docs/evidence.json`:
  6 measured in this checkout (72 tests collected, 5 skills, 4 MCP tools,
  79 notice files, 47 notice distributions, 6 examples) and 7 pinned from
  the 2026-09-13 ORE run. `scripts/evidence.py check` then reported
  `13 figures checked, 0 problems`.
- The evidence check was observed failing before it was observed passing.
  While `docs/IMPLEMENTATION.md` still lacked the new count it reported
  `tests_collected: docs/IMPLEMENTATION.md no longer contains '72 tests
  collected'`. A validation test reproduces that failure mode by changing
  one digit of the recorded CVA in a copy of the documents and requiring
  the check to return 1.
- The notice count was wrong before it was right. A `.DS_Store` inside
  `notices/` was counted as an upstream notice, which would have put 80
  into README.md for 79 notices. The recorder now ignores dot files and a
  test pins that behaviour.
- `riskdesk report` wrote a self-contained page. From
  `examples/energy_stress.json` and `examples/energy_tail.json` it wrote
  8,898 bytes with `"degraded": false` and both scenarios listed; from
  `examples/stress.json` with no tail input it wrote 4,187 bytes and the
  page states that no tail result was supplied. The page contains no
  `http://`, no `https://` and no `<script`.
- The energy examples parse and are not degraded. `riskdesk exposure
  --input examples/energy_book.json` reported gross exposure 14,100,000.00
  USD, net exposure 6,000,000.00 USD and gross leverage 1.175 against NAV
  12,000,000.00 USD. `riskdesk stress --input examples/energy_stress.json`
  reported loss -1,843,000.00 USD for the supply-dislocation shape and
  2,058,500.00 USD for the demand-collapse shape. `riskdesk tail --input
  examples/energy_tail.json` reported VaR 511,773.00 USD and ES
  617,885.16 USD at 97.5% over one day, from 1000 observations with 25 in
  the tail, not degraded.
- `./demo.sh` ran both books end to end and exited 0, printing the method,
  the sign convention and the degraded flag before every number, and
  listing 4 MCP tools over stdio.
- `docs/images/report-energy-stress.png` was captured with Playwright's
  Chromium from a page written in the same run, at 1650 by 3233 pixels and
  158,998 bytes. Playwright is not a project dependency; the capture ran
  from a separate interpreter.

Observed on 2026-09-13 London time, and not re-measured since:

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
- ORE 1.8.16.0: the pinned 1000-sample, seed-42 upstream example produced
  82 netting-set exposure dates, two overlapping XVA rows, CVA
  42600.768114722014 EUR and DVA 62036.0247267215 EUR, with no reported
  errors. These are numerical regression values, not independent model
  validation.
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
./install.sh
./demo.sh
python -m pytest -q --color=no --junitxml=artifacts/tests.xml
python scripts/evidence.py check
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

The energy example is a hand-written synthetic book. Its two scenario
shapes were chosen by hand to be recognisable, not fitted to any dated
episode, and they carry no probability. `examples/energy_tail.json` is a
drawn sample from a heavy-tailed distribution, reproducible from the recipe
written into its own `source` field; it is not an observed history and it
says nothing about how any real energy book behaves.

## PLAN

Extend only against a named instrument, data source or model requirement.
Next validation candidates include discrete dividends, assignment,
collateral agreements, calibration checks and a licensed historical dataset.
Do not treat every capability in the earlier research shortlist as shipped.

Deliberately not done in the 2026-09-14/15 session, so that nothing
unmeasured reached README.md:

- No unit coverage gate and no coverage badge. The gate needs a measured
  figure per package and the figure was not measured.
- No mutation harness and no mutation badge.
- No GitHub Actions workflow.
- No CHANGELOG.md, SECURITY.md or DISCLAIMER.md.
- No Docker image, no registry or Smithery listing, no hosted sample.
  These need the owner's decision before any work starts.
- No new risk model, no market-data client and no broker connectivity. The
  report command reads results that already exist and draws them; it
  computes no risk of its own.
- `notices/`, `wheel-hashes.json` and the requirements lock were not
  touched, because no dependency changed. The report page is drawn with
  inline SVG from the standard library rather than a plotting package, so
  the dependency tree is the one that was already recorded.
