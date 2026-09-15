# Changelog

This file records what changed and what was observed, with the date of the
observation. A figure that appears here was measured; one that was not
measured is named as not measured.

## 0.1.0, unreleased

First working scope: historical VaR and Expected Shortfall, linear
portfolio exposure, explicit stress scenarios, and an Open Source Risk
Engine exposure and XVA adapter. One runtime under `src/riskdesk`, called
by both the CLI and the MCP server. Five plugin skills.

### Added on 2026-09-15, local dashboard

- `riskdesk dashboard`, a local web view over the four tools: overview,
  exposure, stress, tail risk and counterparty XVA. Five modules, standard
  library only, no new dependency and nothing added to `notices/`,
  `wheel-hashes.json` or the lock.
- The charts are the ones `report.py` already draws, now public, so the
  served page and the saved page come from one implementation. A
  validation test fails the build if a dashboard module grows an SVG of
  its own.
- It serves the synthetic energy book by default, binds a loopback address
  and refuses any other host, makes no outbound request, and reads no path
  from the request. Every view prints the sign convention and the degraded
  flag whether or not the flag is set, and an absent input says so in
  words that do not imply a zero.
- Every failure is one sentence on stderr with its own exit code: 64 not
  loopback, 66 missing input, 67 input fails its contract, 73 port in use.
  That shape is deliberate, and it comes from the container defect fixed
  earlier the same day, which arrived as a bare exit code and an empty
  stderr.
- `scripts/screenshot_report.py` gained a dashboard capture that starts the
  real server on an ephemeral port, photographs it, and stops it.

### Measured on 2026-09-15, local dashboard

- 148 tests before, 257 after, none skipped: 154 unit, 58 integration, 45
  validation, 11 docker.
- Unit line coverage 87.57 percent before, 85.87 percent after, against a
  gate of 80 percent.
- Three captures at scale 1.25 and 32 colours: 66,982, 73,945 and 52,105
  bytes, 193,032 in total, inside the 220,293 available. Images total
  472,739 of 500,000.

### Fixed on 2026-09-15, container writes on Linux

- The container could not write a bind mount it did not own. The image
  runs as a fixed non-root uid, and on Linux a bind mount keeps the host's
  ownership, so the demo died at its first writing step. Docker Desktop on
  macOS remaps that ownership, so it was green on a laptop and red on the
  first CI run that ever built the image. The entrypoint now refuses an
  unwritable mount with exit 65 before running anything, names the uid and
  prints the `--user` flag that fixes it. The image was not made root.
- A failing command said nothing on stderr. The CLI printed its error
  envelope to stdout only, and `demo.sh` sends that command's stdout to
  `/dev/null`, so the diagnosis was discarded while the exit code
  survived. That is what made the CI failure unreadable. The JSON envelope
  stays on stdout for machine callers; a human line now also goes to
  stderr.
- A container test skipped in CI and hid the branch CI runs. The ORE wheel
  resolves on linux/amd64 and not on linux/arm64, so the xva refusal test
  skipped on the platform that matters. It now asserts the correct
  behaviour for whichever scope the image has, and nothing skips.

### Measured on 2026-09-15, container writes on Linux

- Reproduced before fixing: exit 1, stderr 0 bytes, stdout stopping at the
  same line as CI, then `PermissionError: [Errno 13] Permission denied`
  once the redirect was removed.
- 144 tests before, 147 after, none skipped. Container tests 7 to 10.
- Unit line coverage 87.55 percent before, 87.57 percent after.
- The linux/amd64 image reports `ORE extra: installed: 1.8.16.0` and is
  953,676,718 bytes; the linux/arm64 image is 643,894,733 bytes.

### Added on 2026-09-15, exposure charts

- `riskdesk report --exposure PATH`, an optional third input beside the
  stress and tail inputs. An absent exposure input is reported as absent,
  in words that do not imply the exposure is zero, exactly as an absent
  tail input already was.
- Two inline SVG charts in the report page, in the same standard-library
  style as the existing two. A signed net-by-asset ladder that puts longs
  and shorts on opposite sides of a zero line, and an ordered
  share-of-gross concentration chart. Both name the base currency, and the
  exposure section carries the sign convention, the degraded flag, its own
  input source and its own input SHA-256.
- An exposure table beside the charts: NAV, gross exposure, net exposure
  and both leverage figures. For `examples/energy_book.json` that is
  gross 14,100,000.00 USD and net 6,000,000.00 USD on NAV 12,000,000.00
  USD.
- `docs/images/report-energy-exposure.png`, clipped to the exposure
  section, and `--section` in `scripts/screenshot_report.py` to take such
  a clip from the live DOM rather than a guessed rectangle.

### Measured on 2026-09-15, exposure charts

- 103 tests before, 117 after, all passing, none skipped.
- Unit line coverage 85.65 percent before, 87.55 percent after.
- Mutation harness unchanged: 31 of 33 detected, 2 equivalent, 0 survived.
- Image budget: 216,280 plus 63,427 bytes, 279,707 of 300,000.

### Added on 2026-09-15, first pass

- `install.sh` and `demo.sh`, both POSIX sh, no colour, non-zero on any
  failure. install.sh creates the environment, installs the development
  extra, attempts the optional ORE extra and reports plainly whether it
  succeeded, then runs the tests.
- `riskdesk report`, which writes one self-contained HTML page from a
  stress result and, optionally, a tail result: contribution bars per
  scenario, the supplied P&L distribution with VaR and Expected Shortfall
  marked, the sign convention and the degraded flag. Charts are inline SVG
  from the standard library, so no plotting dependency was added and the
  page loads nothing from anywhere.
- `examples/energy_book.json`, `examples/energy_stress.json` and
  `examples/energy_tail.json`: a synthetic six-leg energy book with two
  hand-chosen scenario shapes, one the book gains in and one it loses in.
  Neither shape is fitted to a dated episode and neither carries a
  probability.
- `scripts/evidence.py`, which records every figure the documents quote
  with its provenance and fails when a document and the record disagree.
  Measured figures are counted in the checkout; the ORE regression values
  are marked pinned, with the date they were observed.
- `scripts/check_unit_coverage.py`, an 80 percent line-coverage gate over
  `src/riskdesk` measured from the unit suite alone, which refuses a
  report that is missing a production file.
- `scripts/mutate.py`, 33 mutations over `analytics.py` and `models.py`:
  sign flips, the quantile boundary, gross against net, the leverage
  divisor, the degraded flag and every validation rule.
- `docs/ORE.md`, the pinned reproduction and what a clean run does and does
  not establish, moved out of README.md.
- `.github/workflows/tests.yml`, pytest on 3.11, 3.12 and 3.13 with a junit
  artifact, plus the evidence check and the coverage gate. Core scope only,
  no ORE extra, no secrets. Not yet observed running, because nothing has
  been pushed.
- `SECURITY.md`, `DISCLAIMER.md` and this file.

### Changed on 2026-09-15, first pass

- README.md rewritten. Every quoted figure is now recorded in
  `docs/evidence.json` and checked by the suite. The stray repository-name
  heading at the end of the file is gone.
- Tests are separated by marker. Unit tests start no subprocess and open no
  socket.
- `coverage` added to the development extra. No runtime dependency changed,
  so `notices/`, `wheel-hashes.json` and the requirements lock are
  untouched.

### Fixed on 2026-09-15, first pass

- The notice count was being taken from every file under `notices/`,
  including a stray `.DS_Store`, which would have put 80 into README.md for
  79 notices.
- Four mutations survived the first mutation run, each a real gap: the
  overflow guard, the net leverage divisor, non-finite numbers and a zero
  portfolio value. Tests were added or tightened until each was killed.
  Two further mutations at the quantile boundary are recorded as
  equivalent, with the measurement that justifies it.

### Measured on 2026-09-15, first pass

- 103 tests collected, all passing, none skipped: 69 unit, 16 integration,
  18 validation.
- Unit line coverage of `src/riskdesk`: 400 of 467 lines, 85.65 percent,
  against a gate of 80 percent.
- Mutation run: 31 of 33 detected by the test file named for them, 2
  equivalent, 0 survived, 0 skipped.
- `./install.sh && ./demo.sh` from a fresh clone into a new directory, with
  no pre-existing environment: both succeeded.

### Not measured

The ORE example was not re-run on 2026-09-15; its figures carry the
2026-09-13 observation. Only CPython 3.13 was exercised, and only on macOS
ARM64. See `docs/IMPLEMENTATION.md` for the full list.
