---
description: Morning risk pack on the caller's files: exposure, tail models, backtest status, stress and limits, written to one report page
argument-hint: [OUTPUT_PATH]
arguments: [output]
---

Build the morning risk pack and write its page to $output. When no path
is given, write it to `artifacts/daily.html`. When the caller has their
own files, use them throughout. The examples named below are the
fallback, and every figure from them is synthetic and must be labelled so.

1. Exposure: `riskdesk exposure --input examples/energy_book.json`, or the
   caller's book.
2. Tail: `riskdesk tail-models --input examples/energy_tail.json`, or the
   caller's P&L. Quote the `historical` row first, then the model rows
   beside it. The spread between them is the model risk, not noise.
3. Backtest status: `riskdesk backtest --input
   examples/var_backtest_energy.json`, or the caller's forecast record.
   Give exceptions against expected. When the Basel zone is available,
   give it too.
4. Stress: `riskdesk stress --input examples/energy_stress.json`, or the
   caller's scenarios.
5. Limits: `riskdesk limits --input LIMITS.json`. The request holds the
   caller's limits and, as `results`, the exposure, tail and stress
   envelopes printed in steps 1, 2 and 4. For step 2, the `historical` row
   is not an envelope: use `riskdesk tail` on the same P&L. With no caller
   limits, `riskdesk limits --input examples/limits_check.json` grades the
   example's own embedded results, not today's. Say that in those words.
6. Page: `riskdesk report --input examples/energy_stress.json --tail
   examples/energy_tail.json --exposure examples/energy_book.json --output
   artifacts/daily.html`, with the caller's files in place of the
   examples. When a path was given, use `--output $output`. The page draws
   exposure, tail and stress only. Give the backtest and limits in the
   reply.
7. Lead the reply with every `degraded` result and its reason, then any
   limit breach, then the backtest zone, then the figures. Give currency,
   as-of date and horizon with each, and say which inputs were the
   caller's and which were the synthetic fallback.
8. Inputs with different `as_of` dates or currencies do not make one pack.
   Say so and report them separately rather than combining them.
