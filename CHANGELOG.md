# Changelog

This file records what changed and what was observed, with the date of the
observation. A figure that appears here was measured; one that was not
measured is named as not measured.

## 0.1.0, unreleased

First working scope: historical VaR and Expected Shortfall, linear
portfolio exposure, explicit stress scenarios, and an Open Source Risk
Engine exposure and XVA adapter. One runtime under `src/riskdesk`, called
by both the CLI and the MCP server. Five plugin skills.

### Added on 2026-09-15

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

### Changed on 2026-09-15

- README.md rewritten. Every quoted figure is now recorded in
  `docs/evidence.json` and checked by the suite. The stray repository-name
  heading at the end of the file is gone.
- Tests are separated by marker. Unit tests start no subprocess and open no
  socket.
- `coverage` added to the development extra. No runtime dependency changed,
  so `notices/`, `wheel-hashes.json` and the requirements lock are
  untouched.

### Fixed on 2026-09-15

- The notice count was being taken from every file under `notices/`,
  including a stray `.DS_Store`, which would have put 80 into README.md for
  79 notices.
- Four mutations survived the first mutation run, each a real gap: the
  overflow guard, the net leverage divisor, non-finite numbers and a zero
  portfolio value. Tests were added or tightened until each was killed.
  Two further mutations at the quantile boundary are recorded as
  equivalent, with the measurement that justifies it.

### Measured on 2026-09-15

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
