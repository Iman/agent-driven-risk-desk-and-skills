---
description: Historical VaR and Expected Shortfall from supplied P&L, with the sample size read before the numbers
argument-hint: [INPUT_PATH]
arguments: [input]
---

Measure tail risk on $input, or `examples/energy_tail.json` when no path
is given.

1. `riskdesk tail --input examples/energy_tail.json`. When a path was
   given, use `--input $input` in place of the example. An omitted
   argument expands to nothing, and a bare `--input` is rejected before
   anything is read.
2. Read `observations` and `tail_probability_mass` first, before quoting
   VaR or ES. A 99 percent figure from a sample with two observations in
   the tail is arithmetic, not a measurement, and the two numbers are what
   tell a reader which one they have.
3. Read `degraded`. When it is true, say so plainly and in the first
   sentence, with `degraded_reason` quoted. The reason today is that fewer
   than 20 observations of tail probability mass were supplied.
4. That threshold is a reporting rule. Do not describe it as a confidence
   test, a significance test, or a statement that the number is wrong. It
   says the sample is small, and nothing more.
5. Quote VaR and ES with the sign convention attached: a positive value is
   a loss, a negative one is a gain, and neither is floored at zero. Give
   the confidence and the horizon with every figure.
6. Say that each observation was taken to already span the stated horizon.
   Nothing here scales a daily number to ten days, and if the caller
   supplied daily P&L and asked for a ten-day horizon, that is a problem
   with the input which no output will reveal.
7. These are empirical results over one supplied sample. They are not a
   forecast and their forecast accuracy has not been tested.
