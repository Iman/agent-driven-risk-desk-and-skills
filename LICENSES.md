# Licensing

One licence covers this repository's own code: the
[PolyForm Noncommercial License 1.0.0](https://polyformproject.org/licenses/noncommercial/1.0.0).
The full text is in `LICENSE` at the root, and it travels in the wheel,
the source archive and the plugin package.

Upstream software keeps its own licence. See
[THIRD-PARTY.md](THIRD-PARTY.md) for the credits and
[notices/](notices/) for the notices themselves, which are retained
unchanged.

## What you may do without asking

Any noncommercial purpose. The licence names these explicitly: research,
experiment and testing for the benefit of public knowledge, personal
study, private entertainment, hobby projects, amateur pursuits, and
religious observance, in each case without an anticipated commercial
application.

Use by a charitable organisation, an educational institution, a public
research organisation, a public safety or health organisation, an
environmental protection organisation, or a government institution is
permitted regardless of how that organisation is funded.

You may modify it, build on it, and pass it on, provided whoever receives
it also receives these terms.

## What requires a written agreement first

Anything for commercial advantage or private monetary compensation. In
this project's terms, and without limiting the licence itself, that
includes:

- using it inside a fund, a bank, a trading desk, a proprietary trading
  operation, an energy or commodity trading business, or any organisation
  that manages money or runs a book
- selling it, or selling access to it, or bundling it into a paid product
  or a subscription
- offering paid consulting, risk reporting, model validation or analysis
  produced with it
- raising investment, grant money, donations or crowdfunding on the basis
  of it, whether or not the software itself is distributed
- using it in a course, programme or service that charges a fee

If you want to do any of that, contact the copyright holder. Terms are
negotiable. The answer to a polite request is not automatically no.

This matters more here than it would for a toy. The readers most likely
to find this useful are the ones the noncommercial clause excludes, and
that is a deliberate choice rather than an oversight.

## Why this rather than an open source licence

This is deliberate and it is not open source in the OSI sense. The cost is
real: fewer people will use it, some package indexes and directories treat
noncommercial licences as unfree, and it will attract fewer contributors.
That trade was made knowingly, so that a commercial arrangement stays
possible rather than being given away by default.

Unlike its sibling project, this repository has never carried another
licence. It was published under PolyForm Noncommercial and has stayed
there, so there is no earlier grant to honour.

Contributions are covered by [CLA.md](CLA.md), which grants the copyright
holder a licence broad enough to make a commercial agreement possible.
Without it, one contribution with no assignment would block one.

## Third-party components

The tested dependency tree contains 47 upstream distributions. Every one
had a locatable notice, and 79 notice files are retained unchanged in
`notices/`, with hashes in `wheel-hashes.json` and the resolved tree in
`dependency-inventory.json`.

The four components the project depends on most directly, each checked
against the notice file on disk rather than against a package index:

| Component | Licence, as stated in its own notice |
| --- | --- |
| skfolio | BSD 3-Clause |
| MCP Python SDK | MIT |
| Pydantic | MIT |
| Open Source Risk Engine | Quaternion Risk Management and Acadia copyright, full bundled notice retained |

The remaining distributions are not listed here with a licence name,
deliberately. Restating a licence this document has not verified against
the file on disk is exactly the kind of unchecked claim the rest of this
repository refuses to make. `dependency-inventory.json` records what each
distribution declared, `notices/` holds what each one shipped, and where
those two disagree the notice is authoritative.

Note what the inventory does not settle: 16 of the 48 entries declare no
licence expression in their metadata at all and carry only a licence file.
That is why the notice on disk, and not the metadata, is the thing this
project treats as the answer.

## What the licence does not do

It does not make this software fit for any purpose, and it does not make
its output advice. [DISCLAIMER.md](DISCLAIMER.md) is the document that
matters there, and the licence's own No Liability section is not a
substitute for reading it.

It does not grant any rights in third-party components, and it does not
grant any rights in market data. Market-data rights and methodology rights
are separate from software licences. This project distributes no ISDA SIMM
material and claims no rights to your data. `data_mode` records what you
declared about your rights to an input; it is a declaration, not a rights
certificate, and nothing here checks it.
