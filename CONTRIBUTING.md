# Contributing

Issues and pull requests are welcome. This document says what the project
expects, so a contribution is not sent back for something you could not
have known.

Start with AGENTS.md. It is short, it is the repository's own statement of
scope, and it is binding on a pull request as much as on a maintainer.

## Before you write code

Say what you measured. The project's rule, and the reason most of its
documents read the way they do, is that a claim carries its evidence: the
command you ran, the output you saw, the file and the line. An issue that
opens with a reproduction is worth more than one that opens with a
diagnosis.

Validate the premise before building on it. More than one change in this
repository's history was written, tested and then reverted because nobody
measured the problem first. If you are fixing something, show it failing.

## The scope, which is deliberately narrow

The approved scope is historical VaR and Expected Shortfall, signed linear
exposure, explicit stress scenarios, and counterparty exposure and XVA
through a local Open Source Risk Engine project.

A pull request that adds a risk model, a market-data client or broker
connectivity will be declined however good it is, not because it is
unwelcome but because it changes what this project claims to be. Open an
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

Run the suite before you open anything:

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

New behaviour needs a test that fails before your change and passes after.
If you cannot make it fail first, say so in the pull request; that is
useful information, not a black mark.

## The gates a change has to pass

```sh
.venv/bin/python scripts/evidence.py check     # documents match the repository
.venv/bin/python -m coverage run -m pytest -q --color=no -m unit
.venv/bin/python -m coverage json -q
.venv/bin/python scripts/check_unit_coverage.py artifacts/coverage/unit.json
.venv/bin/python scripts/mutate.py             # break it, check it is noticed
.venv/bin/python scripts/contrast.py           # colour contrast, both modes
```

If you change a figure a document quotes, re-record it:

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
  unless a dependency genuinely changed.
- Every example is synthetic and says so in its own `source` field. Keep
  it that way; see CLA.md for why.

## What will be sent back

A claim with no measurement behind it. A number in a document that no
command produces. A test that cannot fail. A new dependency added
quietly. Prose that describes a capability the code does not have, which
is the specific failure `scripts/evidence.py` and the validation tests
exist to catch.

## Licensing and your rights

Contributions are licensed under PolyForm Noncommercial 1.0.0 and require
the agreement in CLA.md, which you record by adding your name to
CONTRIBUTORS.md in the same pull request. You keep your copyright. See
LICENSES.md for what the licence permits and what needs a written
agreement.

## Privacy

Opening an issue or a pull request means what you write is public and
permanent. Do not paste a real position file, a real P&L series, or
anything derived from a licensed data feed. PRIVACY.md says what this
software does and does not do with data; the same discipline applies to
the issue tracker.
