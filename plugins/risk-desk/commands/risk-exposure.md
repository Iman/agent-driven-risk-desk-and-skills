---
description: Gross and net exposure, leverage against NAV, and the largest share of gross
argument-hint: [INPUT_PATH]
arguments: [input]
---

Aggregate the book in $input, or `examples/energy_book.json` when no path
is given.

1. `riskdesk exposure --input examples/energy_book.json`. When a path was
   given, use `--input $input`.
2. Report gross before net, in that order. They answer different
   questions and a reader given net first will anchor on the smaller
   number.
3. Say what gross is: absolute position values added before any
   offsetting. That is why a share of gross is never negative, and why
   gross exceeds net for any book holding both sides.
4. Give both leverage figures as multiples of the supplied NAV, and say
   supplied. The NAV came from the input; nothing here verified it.
5. Name the largest share of gross and its percentage, from
   `gross_shares`. Concentration is the thing a reader cannot get by
   glancing at the total.
6. A negative `net_by_asset` value is a short. Say so in words rather than
   leaving a reader to read the minus sign.
7. Read `degraded` and report it before the numbers, whether or not it is
   set.
8. Every value was already translated into the stated base currency before
   submission. Nothing here converts anything, so a book in two currencies
   that was not converted first will produce a confident and meaningless
   total.
9. Do not call any of this counterparty exposure at default, regulatory
   capital, or a margin requirement. It is none of them.
