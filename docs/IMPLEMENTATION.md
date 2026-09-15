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
- The mutation harness has no case over `report.py`, so the sign handling
  in the new exposure ladder is guarded by unit tests only. Adding
  mutations there was outside the scope approved for this run and is not
  claimed as done.
- The screenshots were taken by one Chromium build at one device scale.
  How the page renders in another browser was not observed.
- `.github/workflows/tests.yml` is reported to have run for the first time
  and succeeded in 1m4s, run 34911224128. That is a report, not an
  observation made here: no CI log was read in this session, and the run
  predates the exposure charts. No CI badge is claimed.

## VERIFIED

Observed on 2026-09-15 London time, on macOS ARM64 (Darwin 25.6.0), for
the container image, with Docker 29.7.2:

- The ORE extra was measured on the image platform before the Dockerfile
  was written, not reasoned about. `docker run --rm python:3.13-slim pip
  index versions open-source-risk-engine` reports no matching distribution
  at linux/arm64 and `1.8.16.0, 1.8.15.0, 1.8.14.1, 1.8.14.0, 1.8.13.1,
  1.8.13.0` at linux/amd64. The arm64 image therefore ships the core
  scope, records that in `/opt/risk-desk/xva-status`, prints it, and
  refuses `xva` with exit 69 before anything runs.
- `docker build -t risk-desk:test .` succeeded in 32 seconds on this
  machine with a warm base image. The image is 643,894,733 bytes,
  linux/arm64. That figure is the image as Docker reports it, not a
  download size.
- `docker run --rm risk-desk:test` printed riskdesk 0.1.0 on CPython
  3.13.15 aarch64, with `ORE extra: not available for this image platform`.
- `docker run --rm -v DIR:/artifacts risk-desk:test demo` exited 0, ran
  both example books, listed 4 MCP tools, and left a 14,778 byte
  `report.html` in the mounted directory.
- The two guards fire with distinct codes: 64 for a writing command with
  no mount, 69 for `xva` with no ORE backend. `RISKDESK_ALLOW_EPHEMERAL=1`
  overrides the first and says on stderr that the output will be
  discarded.
- The image runs as uid 10001 `desk`, verified by
  `docker run --entrypoint id IMAGE -un`.
- Tests: 128 collected before, 135 tests collected after, all passing and
  none skipped, in 22.71s. By marker: 81 unit, 25 integration, 29 validation, of which 7 are the new
  `docker` marker. Unit coverage unchanged at 471 of 538 lines,
  87.55 percent, because the container tests are integration and the new
  files are not Python.
- The container tests skip rather than fail when no Docker binary or no
  answering daemon is present. They ran here; they were not skipped.

Observed on 2026-09-15 London time, on macOS ARM64 (Darwin 25.6.0), for
the plugin manifests:

- A live defect is CLOSED. README.md pointed at `plugins/risk-desk`, which
  had a Codex manifest and no Claude Code manifest, and the repository had
  no `.claude-plugin/marketplace.json`, so the install route the README
  implied did not exist for Claude Code. Both manifests are now present,
  both are listed, and a validation test fails the build if either stops
  matching the directories on disk.
- A second live defect was found while checking the first and is CLOSED in
  its own commit. `python scripts/package_plugin.py`, a command
  docs/IMPLEMENTATION.md tells a reader to run, failed with an
  AssertionError: it compared the notice files in the zip, which exclude
  `.DS_Store`, against every file under `notices/`, which includes one.
  Observed failing before the change and passing after.
- Tests: 117 collected before, 128 after, all passing and none skipped.
  By marker: 81 unit, 18 integration, 29 validation.
- Unit line coverage unchanged at 471 of 538 lines, 87.55 percent, because
  the new tests are validation rather than unit and the new files are JSON
  rather than Python.
- `evidence.py check` reports `18 figures checked, 0 problems`, up from 17.
  The new figure is the skill-directory count the manifests point at.
- The manifest tests found a real bug in their own first draft:
  `"./.mcp.json".lstrip("./")` is `"mcp.json"`, a different file, because
  `lstrip` removes characters and not a prefix. Observed failing, then
  fixed with `removeprefix` in all three path resolutions.

Observed on 2026-09-15 London time, on macOS ARM64 (Darwin 25.6.0), for
the exposure charts:

- Before this change: 103 tests collected, all passing, none skipped; unit
  line coverage 400 of 467 lines, 85.65 percent; `evidence.py check`
  reported `14 figures checked, 0 problems`.
- After this change: 117 tests collected, all passing, none skipped; unit
  line coverage 471 of 538 lines, 87.55 percent, so the change raised
  coverage rather than lowering it; `evidence.py check` reports
  `17 figures checked, 0 problems`. Per file after: `models.py` 100.00%,
  `report.py` 99.52%, `cli.py` 97.78%, `analytics.py` 94.64%,
  `summaries.py` 92.45%, `server.py` 87.50%, `ore.py` 77.61%,
  `ore_worker.py` 0.00%.
- Mutation harness re-run, unchanged: 33 mutations, 31 detected by the test
  file named for each, 0 detected only elsewhere, 2 equivalent, 0 survived,
  0 skipped. The harness targets `analytics.py` and `models.py`; it has no
  case over the new chart code, which is named under UNKNOWN below.
- The exposure figures the charts draw, from
  `examples/energy_book.json`: NAV 12,000,000.00 USD, gross exposure
  14,100,000.00 USD at 1.175x NAV, net exposure 6,000,000.00 USD at 0.5x
  NAV, over 6 assets. Net by asset, as the ladder orders it:
  WTI_CRUDE_FUTURE 4,200,000.00, JKM_LNG 3,100,000.00, HENRY_HUB_GAS
  1,800,000.00, PJM_WEST_POWER 950,000.00, TTF_GAS -1,450,000.00,
  BRENT_CRUDE_FUTURE -2,600,000.00. Two of the six are negative and are
  drawn on the short side of the zero line. Share of gross, as the
  concentration chart orders it: 29.8%, 22.0%, 18.4%, 12.8%, 10.3%, 6.7%.
- `riskdesk report` with all three inputs wrote 14,778 bytes; with stress
  alone it wrote 4,795 bytes and the page states that no exposure result
  and no tail result were supplied. Both figures were first taken before
  the page title changed and were 20 bytes lower; they are re-measured
  here rather than carried forward.
- Images. `docs/images/report-energy-exposure.png` is new, clipped to the
  exposure section's own bounding box read from the live DOM, 63,427
  bytes. `docs/images/report-energy-stress.png` was regenerated, because
  the page it documents now carries an exposure section and the old
  capture no longer showed what that command writes; it is 216,280 bytes,
  up from 158,998. To stay inside the 300,000 byte budget its palette was
  reduced from 64 to 32 colours, which cost 22,836 bytes and left the text
  legible; nothing was cropped away. Total 279,707 bytes, 20,293 under
  budget.

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
- After this session's work the suite reports 103 tests collected, with no
  failures and no skips. By marker: 69 unit, 16 integration, 18 validation.
  The unit tests start no subprocess and open no socket.
- Unit line coverage of `src/riskdesk`, measured from the unit suite alone
  by `coverage run -m pytest -m unit` then `check_unit_coverage.py`: 400 of
  467 lines, 85.65 percent, against a gate of 80 percent, so the gate
  passes. Per file: `models.py` 100.00%, `report.py` 99.28%, `cli.py`
  97.67%, `analytics.py` 94.64%, `summaries.py` 92.45%, `server.py`
  87.50%, `ore.py` 77.61%, `ore_worker.py` 0.00%. `ore_worker.py` is zero
  because it only executes inside the ORE worker process; that is a real
  gap and it is visible rather than averaged away.
- Mutation run over `analytics.py` and `models.py`: 33 mutations, 31
  detected by the test file named for each, 0 detected only elsewhere, 0
  survived, 0 skipped, 2 recorded as equivalent.
- The mutation harness found four real gaps before it found none. The
  first run reported six survivors. Two were the quantile-boundary pair
  below. The other four were holes: the overflow guard could be removed
  because the test matched a substring that both error messages contain;
  `net_leverage` was computed but never asserted; and allowing non-finite
  numbers or a zero portfolio value still raised a ValueError further down
  the function, so a test asserting `ValueError` could not tell the
  contract from the arithmetic. Tests were tightened until each was
  killed, then the run was repeated.
- The two quantile-boundary mutants are recorded as equivalent, on a
  measurement rather than an argument. Over 199,500 (count, confidence)
  pairs, count 2 to 400 and confidence 0.500 to 0.999, neither mutation
  ever changed which observation VaR selects, and Expected Shortfall
  differed by at most 4.09e-16 and 4.43e-16 relative. Killing them would
  mean asserting a last-bit float. Note what that also says: on this grid
  the unconditional shift is indistinguishable from the guarded one. That
  is one grid, not a proof that the guard is redundant.
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
  10,230 bytes with `"degraded": false` and both scenarios listed; from
  `examples/stress.json` with no tail input it wrote 4,195 bytes and the
  page states that no tail result was supplied. A run against the
  four-sample `examples/tail.json` instead wrote 8,908 bytes and reported
  `"degraded": true`, which is the warning path. The page contains no
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
- `./install.sh && ./demo.sh` succeeded from a fresh clone into a new
  directory with no pre-existing environment. install.sh selected
  CPython 3.13.13 from PATH, reported `ORE extra: installed: 1.8.16.0`,
  and its test run reported `72 passed in 30.13s`. demo.sh then ran both
  books end to end and exited 0, printing the method, the sign convention
  and the degraded flag before every number, listing 4 MCP tools over
  stdio, and writing a 10,230 byte report page. Neither script emitted an
  escape byte.
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

- No mutation badge. Two of the 33 cases are equivalent rather than
  killed, and a badge would round that away.
- No CI badge. The workflow exists and has never run.
- No Docker image, no registry or Smithery listing, no hosted sample.
  These need the owner's decision before any work starts.
- No new risk model, no market-data client and no broker connectivity. The
  report command reads results that already exist and draws them; it
  computes no risk of its own.
- `notices/`, `wheel-hashes.json` and the requirements lock were not
  touched, because no dependency changed. The report page is drawn with
  inline SVG from the standard library rather than a plotting package, so
  the dependency tree is the one that was already recorded.
