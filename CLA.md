# Contributor licence agreement

This project is licensed under the PolyForm Noncommercial License 1.0.0,
in every part: `src/riskdesk`, `scripts/`, `plugins/`, `tests/` and
everything around them. Opening a pull request means you agree your
contribution is licensed under those terms.

Contributions also require this agreement, because commercial use of this
software needs a separate written agreement with the copyright holder, and
that is only possible while he holds sufficient rights over every line.

By submitting a contribution you confirm:

1. The contribution is your original work, or you have the right to submit
   it under these terms.
2. You grant Iman Samizadeh a perpetual, worldwide, non-exclusive,
   royalty-free, irrevocable licence to use, reproduce, modify, distribute
   and sublicense your contribution, including the right to license it on
   terms other than PolyForm Noncommercial, and specifically including
   commercial licences.
3. You retain your own copyright and remain free to use your contribution
   elsewhere however you wish.
4. Your contribution contains no code taken from a source licensed under
   GPL, AGPL, or any licence with no stated terms, and no code you are not
   permitted to relicense.
5. Your contribution does not include confidential information, trade
   secrets or proprietary material belonging to an employer or any third
   party, or you have written permission to contribute it.

Point 2 is what makes a commercial licence possible. Without it a single
contribution with no assignment would leave the project unable to offer
one without tracking down its author.

## One thing specific to this project

Do not contribute market data, a real position file, or anything derived
from a licensed data feed. Every example in this repository is synthetic
and says so in its own `source` field, and that is deliberate: market-data
rights are separate from software licences, and a contributed fixture
carrying somebody's redistribution terms is a problem that outlives the
pull request. If you need a new example, generate one and record how, as
`examples/energy_tail.json` does.

Record your agreement by adding your name and the date to CONTRIBUTORS.md
in the same pull request.
