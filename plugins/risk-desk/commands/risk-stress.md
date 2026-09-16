---
description: Apply explicit shocks to every position and report the loss, the stressed NAV and the worst contributions
argument-hint: [INPUT_PATH]
arguments: [input]
---

Revalue the book in $input, or `examples/energy_stress.json` when no path
is given.

1. `riskdesk stress --input examples/energy_stress.json`. When a path was
   given, use `--input $input`.
2. State the sign convention before the first number. P&L is signed and
   loss is its negation, so a negative loss is a scenario the book gains
   in. A reader who meets "loss: -1,843,000.00 USD" without that sentence
   will read it as a gain of the wrong size or a loss of the wrong sign.
3. For each scenario report the name, the loss, and the stressed NAV.
4. Name the three positions that hurt most, from `contributions`, most
   negative first. The total says how much; the contributions say what to
   do about it.
5. Attach no probability to any scenario, and do not accept one offered.
   These are shocks somebody specified. A scenario named after a
   historical episode carries a shape somebody chose, not a fitted event,
   and it is not a forecast.
6. Every scenario names every asset explicitly, including a zero where
   nothing moves. If a caller wants an asset left out, that is a different
   book, not a missing shock.
7. The model is linear: each position moves by its own shock. It does not
   hold for options, for credit migration or for a nonlinear margin call,
   and it says nothing about being able to trade out at the shocked price.
8. Read `degraded` and report it first, whether or not it is set.
