---
description: Grade a limit set against Risk Desk exposure, tail and stress results, with every limit that could not be evaluated named
argument-hint: [INPUT_PATH]
arguments: [input]
---

Check the limits in $input, or `examples/limits_check.json` when no path
is given.

1. `riskdesk limits --input examples/limits_check.json`. When a path was
   given, use `--input $input`. The request carries `limits` and the
   `results` they are graded against: the envelopes `riskdesk exposure`,
   `riskdesk tail` and `riskdesk stress` printed, pasted unchanged.
2. Lead with `overall_status` and `status_counts`. A `breach` comes first,
   then `warning`, then `not_evaluated`, then `within`.
3. `not_evaluated` is not `within`. Name each such limit with its `reason`:
   a missing result, a currency or scenario mismatch, or an error envelope.
4. Read `degraded_reason`. A result dated differently from the limit set,
   or a degraded tail result, is graded anyway and reported there; say so
   beside the limit it affects.
5. Give `value`, `limit` and `utilisation` for each breach and warning, with
   the confidence and horizon from `basis` for a VaR or ES limit.
6. Limits are the caller's. This grades them; it does not propose new ones
   and it does not recommend a trade to cure a breach.
