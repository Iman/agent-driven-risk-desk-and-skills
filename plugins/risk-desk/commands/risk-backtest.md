---
description: Backtest a VaR forecast series against realised P&L, with the exception count and the test verdicts read before any judgement
argument-hint: [INPUT_PATH]
arguments: [input]
---

Backtest the forecast record in $input, or `examples/var_backtest_energy.json`
when no path is given.

1. `riskdesk backtest --input examples/var_backtest_energy.json`. When a
   path was given, use `--input $input` in place of the example.
2. Read `degraded` first and quote `degraded_reason` in the first sentence
   when it is true.
3. Give `observations`, `exceptions` and `expected_exceptions` together.
   An exception count means nothing without the number it is compared with.
4. Report `kupiec_pof`, `christoffersen_independence` and
   `christoffersen_conditional_coverage` with their p-values. A high
   p-value means the record gave no evidence against the forecast. It does
   not prove the forecast right.
5. `basel_traffic_light` applies only to one-day 99 percent VaR over its
   own sample. When `basel_traffic_light_unavailable` is set, say why and
   do not compute a zone yourself.
6. When an ES series was supplied, report `es_backtest` with its seed: the
   p-value is simulated, and another seed gives a slightly different one.
7. Each P&L observation and each VaR forecast must cover the same stated
   horizon, and each forecast must have been made before its P&L was
   known. Nothing here can check either; ask when it is not stated.
8. Positive VaR is a loss. An exception is a loss larger than the VaR
   forecast for that day.
