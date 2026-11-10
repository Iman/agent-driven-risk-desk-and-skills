# Contributing

Issues and pull requests are welcome. This document states what the
project expects, so that no contribution is returned for an unstated rule.

Start with AGENTS.md. It is short, it is the repository's own statement of
scope, and it is binding on a pull request as much as on a maintainer.

## Before writing code

State what was measured. The rule of the project is that a claim carries
its evidence, namely the command, its output, the file and the line. An
issue that opens with a reproduction is worth more than one that opens
with a diagnosis.

Validate the premise before building on it. A change that fixes a defect
must first show the defect failing.

## The scope, which is deliberately narrow

The approved scope is historical and model VaR and Expected Shortfall
with backtests, signed linear exposure, European option Greeks and full
revaluation, VaR and ES attribution, limits and what-if, liquidity,
explicit, historical and reverse stress scenarios, SA-CCR and exposure
profiles, portfolio credit VaR, FRTB capital pieces, and counterparty
exposure and XVA through a local Open Source Risk Engine project.

A pull request that adds a risk model, a market-data client or broker
connectivity will be declined, because it changes what this project
claims to be. Open an
issue first and name the instrument, the data source or the requirement it
serves.

Two rules follow from that and are enforced by tests:

- **No new dependency** without a conversation first. The dashboard is
  standard library only and a test parses every import to keep it that
  way. A new runtime dependency also means `notices/`, the dependency
  inventory and the wheel hashes, which is a larger change than it looks.
- **One charting path.** Charts are drawn by the four functions in
  `src/riskdesk/report.py` and nowhere else, so a fix to a sign or an axis
  reaches the saved report page and the served dashboard together.

## Tests

Run the suite before opening an issue or a pull request:

```sh
./install.sh
.venv/bin/python -m pytest -q --color=no
```

Tests are separated by marker and the separation is checked, not merely
documented:

| Marker | What it may do |
| --- | --- |
| `unit` | In process. No subprocess, no socket. |
| `integration` | Real processes, real scripts, a real loopback socket. |
| `validation` | The repository, its documents and its packaging. |
| `docker` | Builds and runs the container image. |

A unit test that reaches a socket will fail a validation test that reads
the syntax tree looking for exactly that.

New behaviour needs a test that fails before the change and passes after
it. If the test cannot be made to fail first, say so in the pull request.

## The gates a change has to pass

```sh
.venv/bin/python scripts/evidence.py check     # documents match the repository
.venv/bin/python -m coverage run -m pytest -q --color=no -m unit
.venv/bin/python -m coverage json -q
.venv/bin/python scripts/check_unit_coverage.py artifacts/coverage/unit.json
.venv/bin/python scripts/mutate.py             # break it, check it is noticed
.venv/bin/python scripts/contrast.py           # colour contrast, both modes
```

If a change alters a figure that a document quotes, record the figure again:

```sh
.venv/bin/python scripts/evidence.py record
```

Never edit `docs/evidence.json` by hand to make the check pass. The point
of the file is that it is measured.

## House rules

- No ANSI escape codes, no emoji, and no em dashes, anywhere: source,
  documents, commit messages, generated files.
- Commit subjects are imperative and under 60 characters.
- No automated authorship. Commits carry the contributor's own identity
  and nothing else. A commit-message hook enforces this.
- Do not touch `notices/`, `wheel-hashes.json` or the requirements lock
  unless a dependency changed.
- Every example is synthetic and says so in its own `source` field. Keep
  it that way. CLA.md gives the reason.

## What will be sent back

A contribution with any of these is returned:

- A claim with no measurement behind it.
- A number in a document that no command produces.
- A test that cannot fail.
- A new dependency added without prior discussion.
- Prose that describes a capability the code does not have. This is the
  failure that `scripts/evidence.py` and the validation tests detect.

## Licensing and your rights

Contributions are licensed under PolyForm Noncommercial 1.0.0 and require
the agreement in CLA.md. Record the agreement by adding the name of the
contributor to CONTRIBUTORS.md in the same pull request. The contributor
keeps the copyright. LICENSES.md states what the licence permits and what
needs a written agreement.

## Privacy

The text of an issue or a pull request is public and permanent. Do not
paste a real position file, a real P&L series, or
anything derived from a licensed data feed. PRIVACY.md says what this
software does and does not do with data; the same discipline applies to
the issue tracker.
