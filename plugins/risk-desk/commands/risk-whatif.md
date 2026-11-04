---
description: Apply proposed trades to a book and compare exposure, stress, tail and limits before and after, without placing anything
argument-hint: [INPUT_PATH]
arguments: [input]
---

Run the pre-trade what-if in $input. When no path is given, use
`examples/limits_what_if.json`.

1. `riskdesk what-if --input examples/limits_what_if.json`. When a path was
   given, use `--input $input`. The request is a book plus `trades`, each a
   signed change in market value in the book's currency. It can also hold
   `scenarios`, `asset_returns` with `confidence` and `horizon_days`, and
   `limits`.
2. Read `degraded` and quote `degraded_reason` before any figure.
3. Report `before`, `after` and `change` side by side for every section
   that was computed. A section absent from `after` was not computed
   because its input was not supplied. Say so rather than calling it zero.
4. A tail figure after the trades is the historical VaR and ES of the new
   weights over the supplied return history. It is not a forecast, and it
   assumes the trades fill at the stated market values.
5. Report `limits_after` as `/risk-limits` does: breaches first, and every
   `not_evaluated` limit named with its reason.
6. Nothing is placed or sent. This is a calculation on a copy of the book,
   and it is not a recommendation to trade.
