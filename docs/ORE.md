# Reproducing the pinned ORE example

Risk Desk's XVA command is an adapter. It runs a trusted local ORE project
in a separate process, refuses a summary when ORE reports errors, and
preserves ORE's report levels, column names, currency and unavailable
values. It adds no model of its own.

The figures below are a numerical regression result: the same inputs
produced the same numbers. They are not independent verification of ORE's
financial models, and they say nothing about calibration quality or
regulatory approval.

## What is pinned

| Item | Value |
| --- | --- |
| Release | ORE v1.8.16.0 |
| Revision | `b1f239332fdd51e5c514dd6de34a665fe0ff8326` |
| Simulation | 1000 simulation samples and seed 42 |
| Exposure grid | 82 netting-set exposure dates |
| CVA | CVA 42600.768114722014 EUR |
| DVA | DVA 62036.0247267215 EUR |
| Data provenance | `upstream-example` |
| First observed | 2026-09-13, recorded in [IMPLEMENTATION.md](IMPLEMENTATION.md) |

The XVA report has two overlapping rows, one at netting-set level and one
at trade level. Do not add them together. A zero in a column whose
adjustment was not requested is a disabled calculation, not a result, and
ORE's `nullDouble()` sentinel is emitted as JSON null rather than a number.

## Running it

The example inputs are not distributed with Risk Desk. Obtain an ORE
checkout at the revision above, with its `Examples/Input` and
`Examples/ORE-Python/Input` directories, then run:

```sh
.venv/bin/python scripts/ore_smoke.py --upstream ORE_CHECKOUT --work NEW_WORK_DIRECTORY
```

The script verifies the revision before copying anything. It builds a
self-contained input copy, retains the sample count and the seed above, and
removes two security curves that the example's swap does not use and whose
spreads were missing. Those fixture edits are local to the copy; no ORE
library file is modified. The adapter still refuses any remaining ORE
error.

## Running your own project

```sh
.venv/bin/riskdesk xva --project INPUT_BUNDLE --config Input/ore.xml --output NEW_OUTPUT --data-mode user-licensed
```

The project must be a trusted, inspected directory. Every referenced input
must resolve inside it, the output directory must be new and outside it,
symlinks are refused, and both the `simulation` and `xva` analytics must be
active, so a stale cube cannot be reused. The adapter forces
`continueOnError=false` and records a SHA-256 for every input file.

This process boundary is not a sandbox. It keeps a normal run isolated; it
does not make a hostile XML configuration safe. Read an unfamiliar project
before running it.

## What this does not establish

The ORE extra is optional and its wheel is published for a limited set of
Python and platform combinations. Version 1.8.16.0 was tested on CPython
3.13, macOS ARM64. A clean run establishes that the adapter and the
configuration are consistent. It does not establish forecast skill,
wrong-way-risk calibration, liquidity survival, SIMM permissions, or
coverage of every instrument ORE supports.
