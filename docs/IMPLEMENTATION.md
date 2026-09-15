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
- Python 3.11 and 3.12 were not exercised HERE. CI run 34963838757 is
  reported green on 3.11, 3.12 and 3.13; that is a report, not a log this
  session read. Locally only CPython 3.13.14 and, in containers, 3.13.15
  were run.
- No behaviour was observed on Windows. Linux is no longer unknown: see
  the container entries under VERIFIED, which were measured on
  linux/arm64 and linux/amd64.
- The mutation harness has no case over `report.py` or over the
  dashboard, so the sign handling in the exposure ladder and every
  dashboard view are guarded by unit tests only. Adding mutations there
  was outside the scope approved for those runs and is not claimed as
  done.
- The screenshots were taken by one Chromium build at one device scale.
  How the page renders in another browser was not observed.
- No CI log was read in this session. What is known about CI is reported:
  34911224128 green, then 34959651440 and 34960887423 red on `gates`, then
  34963838757 green on all four jobs after the container fix. No CI badge
  is claimed, because a badge would assert something this repository has
  not itself observed.

## VERIFIED

Observed on 2026-09-15 London time, for the README images:

- The four restyled images were re-rendered dark at 64 colours and
  measured, not carried over from the earlier pass: report-energy-stress
  252,296, dashboard-exposure 81,820, dashboard-overview 72,317,
  dashboard-tail 58,341, totalling 464,774 against the 500,000 cap. The
  figures matched the earlier measurement exactly.
- `report-energy-exposure.png` was deleted. It was a crop of the report's
  exposure section showing the same two charts and the same numbers as
  the dashboard exposure view, and once both surfaces shared one token
  set the dashboard view carried strictly more: the navigation, the state
  flags and the counts line.
- A second finding, and the larger one. `dashboard-overview.png` and
  `dashboard-tail.png` were referenced by NOTHING. They had been
  committed with the dashboard work while the README linked only the
  exposure view, so 130,658 bytes, 28 percent of the budget, shipped for
  no reader. The overview is now linked, because it is the only image
  showing the navigation and the per-view input state. The tail view was
  deleted, because its histogram is already visible in the full report
  page image.
- The shipped set is now 3 images, every one of them referenced:
  252,296 plus 72,317 plus 81,820, totalling 406,433, with 93,567 spare.
- The capture script's default view list was the cause and is fixed: it
  defaulted to three views while the README linked one.

Observed on 2026-09-15 London time, for the design system:

- The desk design tokens were COPIED into `src/riskdesk/design.py`, not
  imported: this repository is public, self-contained and adds no
  dependency. The module records where they came from and that the two
  must be kept in step.
- Both surfaces now read the tokens and neither writes a colour. Before
  this, `report.STYLE` carried 22 literal colours, 11 of them chart
  rules, and the dashboard inlines that same string, which is why one
  could not be restyled without the other.
- Contrast was measured here rather than inherited from the 50-pair
  result, which was measured on other markup: 32 pairs enforced across
  both modes, 0 failures. Two further pairs are recorded as decoration
  and not enforced: `--od-line` on `--od-ground` is 1.39 to 1 dark and
  1.48 to 1 light. Table rules are neither a control boundary nor a
  graphical object required to understand the content under WCAG 2.1 SC
  1.4.11, and no token that clears 3 to 1 against the ground would leave
  a dense table readable. The chart axis is enforced, not exempted, and
  passes at 4.34 and 3.43.
- `--od-stale` is declared and deliberately unpainted, with a test
  pinning that. This project has no freshness state; the only "stale" in
  the source is the ORE adapter's refusal to reuse an old cube.
- `data_mode == "synthetic"` gained its own flag. It was already on the
  page as grey prose and is a different fact from degraded.
- The colour guard caught a bug in itself on its first run: `re.VERBOSE`
  collapsed its alternation into a branch that matched the empty string,
  so it reported a literal in files that had none. Found by the mutation
  check written beside it.
- The captures were rendering the LIGHT mode of a dark-first system,
  because headless Chromium defaults to light. Both capture paths now set
  the scheme and default to dark.
- Tests: 257 collected before, 267 tests collected after, all passing and
  none skipped. Unit coverage 778 of 906 lines before, 788 of 916 lines
  after, 86.03 percent.

Observed on 2026-09-15 London time, for the dashboard:

- A local web view over the four tools, five modules under
  `src/riskdesk/dashboard`: `maths` is display arithmetic, `data` shapes,
  `page` renders, `server` owns the socket, `app` wires and reports
  failures. No dependency was added: a validation test parses every
  dashboard module and asserts each import is standard library or
  `riskdesk`.
- One charting path, enforced rather than intended. The four SVG functions
  in `report.py` became public and the dashboard imports them; a test
  asserts no dashboard module contains `<svg` and that none of the four is
  redefined. A second test compares the dashboard payload field by field
  against `report_payload` for the same inputs, so the served page and the
  saved page cannot disagree about a number.
- It binds a loopback address and refuses anything else. `0.0.0.0`, `::`,
  `8.8.8.8` and `example.invalid` are all refused with exit 64 before a
  socket exists, and a name that merely resolves to loopback is not
  trusted. Every failure has its own exit code and one sentence on stderr:
  64 not loopback, 66 missing input, 67 input fails its contract, 73 port
  in use. All four were run and observed.
- The request cannot name a file. The routing table is fixed, so
  `../../etc/passwd`, `%2e%2e%2fetc%2fpasswd` and `examples` are all 404
  with a readable page. Responses carry a content security policy of
  `default-src 'none'`, and no view contains `http://`, `https://`,
  `<script` or `<img`.
- The unit and integration split is enforced from the syntax tree, not
  from prose. An earlier version of that check matched the word socket
  anywhere in a file and failed on a docstring reading "no socket", which
  tested prose rather than behaviour; it now walks the AST for imports and
  names. 154 unit tests bind nothing.
- `docs/images/dashboard-{overview,exposure,tail}.png` were captured from
  a server this repository started and stopped, at scale 1.25 and 32
  colours: 66,982, 73,945 and 52,105 bytes, 193,032 in total. That is
  above the 144,000 I estimated and inside the 220,293 available, so
  nothing was degraded and the two existing images were not touched.
  Images now total 472,739 of the 500,000 budget, 27,261 spare.
- Tests: 148 collected before, 257 after, all passing and none skipped,
  in 93.51s. By marker: 154 unit, 58 integration, 45
  validation, 11 docker.
- Unit line coverage 472 of 539 lines before, 778 of 906 lines after,
  85.87 percent, still above the 80 percent gate. `dashboard/server.py` is
  31.82 percent under the unit marker because its handler body only runs
  when a socket serves, which is integration; that is visible rather than
  averaged away, as `ore_worker.py` already was.

Observed on 2026-09-15 London time, for the CI failure and its fix:

- CI went red on `gates` for the first run that ever exercised the docker
  split, runs 34959651440 and 34960887423. The three pytest matrix jobs
  succeeded; only the container step failed, `1 failed, 5 passed, 1
  skipped`, on `docker run ... demo` returning 1 with an empty stderr and
  stdout stopping at the report step.
- REPRODUCED here before anything was changed, which took two attempts.
  A named volume did not reproduce it: Docker chowns an empty volume to
  the container user, so the write succeeded and the run exited 0. A
  volume populated first and then chowned to uid 1001 did reproduce it
  exactly: `EXIT=1`, stderr 0 bytes, stdout stopping at the same line as
  CI.
- The cause, measured by running the same command without the redirect:
  `PermissionError: [Errno 13] Permission denied: '/artifacts/report.html'`.
  The image runs as uid 10001 and a Linux bind mount keeps the host's
  ownership, so it cannot write a directory owned by the runner. Docker
  Desktop on macOS remaps that ownership, which is why the same test was
  green here and red there.
- A second defect made it unreadable and is CLOSED on its own terms. The
  CLI printed its error envelope to stdout only, and `demo.sh` sends that
  command's stdout to `/dev/null`, so the diagnosis was discarded while
  the exit code survived. The JSON envelope stays on stdout, which is the
  tested contract, and a human line now also goes to stderr.
- The fix keeps every guard. The entrypoint now refuses an unwritable
  mount with exit 65 before running anything, naming the uid and the
  `--user` flag; exit 64 for no mount and 69 for no ORE backend are
  unchanged; the image still runs as uid 10001 and was not made root.
- Verified on linux/amd64, the platform CI uses, which also closes an
  earlier UNKNOWN: that image reports `ORE extra: installed: 1.8.16.0`,
  so the wheel does resolve there and the Dockerfile's platform logic is
  correct on both architectures. It is 953,676,718 bytes against the
  arm64 image's 643,894,733.
- The refusal was checked against the fix it recommends: the same run with
  `--user 1001:1001` exits 0 and writes a 14,778 byte page owned by 1001.
  The CI shape itself, amd64 with a bind mount and `--user`, exits 0 with
  an empty stderr.
- The `1 skipped` is accounted for and no longer exists. It was
  `test_xva_without_a_backend_is_refused_before_anything_runs`, which
  skipped because the amd64 image does have the ORE extra, leaving the
  branch CI actually runs untested. That test now asserts the correct
  behaviour for whichever scope the image has, so both platforms are
  covered and nothing skips.
- Tests: 144 collected before, 148 after, all passing and none skipped. Container tests 7 before, 11 after, 0 skipped.
  The eleventh separates a missing artifacts directory, exit 66, from
  an unwritable one, exit 65, because pointing a reader at --user
  for a path that does not exist would not help them.
  Unit coverage 471 of 538 lines before, 472 of 539 lines after, 87.57
  percent.

Observed on 2026-09-15 London time, for the hosted plugin, code only:

- Nothing was deployed, no DNS record was created or read, no registry or
  directory was contacted, and no credential was written. The endpoint
  `https://riskdesk.avidquant.com` does not resolve today; it is written
  into the manifests as the documented target and both the plugin's own
  README and the root README say it is not live.
- `plugins/risk-desk-hosted` carries a Claude Code manifest, a Codex
  manifest, an `.mcp.json` declaring one http server, a README and the
  licence. `glama.json` is at the repository root. The marketplace now
  lists 2 plugins.
- The hosted plugin carries 3 skills, not 5. `risk_xva` is deliberately
  absent because it reads a trusted local ORE project directory and a
  remote endpoint cannot read files on the caller's machine; offering it
  would put a tool in the list that could never run. Each hosted skill
  says so in its own text.
- The hosted skills are copies of `openai-skills/`, rebuilt by
  `scripts/package_plugin.py`. A validation test compares them byte for
  byte, because two hand-edited copies drift and the one nobody opens is
  the one that ships.
- Six new validation tests: the endpoint hostname is pinned in the
  `.mcp.json`, the Codex `websiteURL` and both descriptions; no other
  hostname and no credential-shaped string reaches the hosted directory,
  with the upstream PolyForm licence URL as the one allowance; the
  not-live wording is required in both READMEs; the absent tool is
  required to stay absent; the copies must match their sources; and
  `glama.json` carries a maintainer and nothing else.
- Tests: 138 collected before, 144 after, all passing and none skipped,
  in 55.73s. Unit coverage unchanged at 471 of 538 lines,
  87.55 percent, because the additions are JSON, Markdown and validation
  tests rather than package code.

Observed on 2026-09-15 London time, for the repository rename:

- The repository was renamed to drop a trailing hyphen. GitHub redirects,
  so nothing was broken on the day, which is exactly why a stale URL can
  sit in a manifest until a directory indexes it and republishes the dead
  name.
- The hand-written list of places to fix named 8 lines. A scan of every
  tracked file found 9 occurrences across 8 files-and-lines, and the one
  missing from the list was `Dockerfile` line 86, the OCI
  `org.opencontainers.image.source` label, which is the field a container
  index reads. All 9 were replaced.
- A validation test now scans every tracked file for the retired name and
  pins the repository URL in both manifests, the README clone command, the
  marketplace command and the image label. It builds the retired string
  from the current one rather than writing it out, so the test file does
  not trip its own check.
- Tests: 135 collected before, 138 after, all passing and none skipped,
  in 58.93s with the container tests included. Unit coverage
  unchanged at 471 of 538 lines, 87.55 percent. No evidence figure quotes
  the repository name, so none needed resyncing.

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
- Tests: 128 collected before, 135 after, all passing and none skipped,
  in 22.71s. By marker: 81 unit, 25 integration, 29 validation, of which 7 are the new
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
- Images. `docs/images/report-energy-exposure.png` is new (and was
  removed later the same day, see the README images entry above), clipped to the
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
