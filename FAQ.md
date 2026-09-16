# Questions about Risk Desk

Weighted deliberately toward what this does not do. If you are evaluating
it for a desk, those are the answers that decide it, and they are cheaper
to read here than to discover in a week.

## Scope and limits

### What is it, in one sentence

A small, auditable risk calculator that computes historical VaR and
Expected Shortfall, signed linear exposure and explicit stress scenarios
over files you supply, exposes the same functions to an agent over MCP,
and adapts a local Open Source Risk Engine project for counterparty
exposure and XVA.

### Is this a risk system

No, and it is worth being blunt about it. It has no position store, no
market-data connection, no end-of-day process, no entitlements, no audit
trail beyond the input hash it records, and no notion of a book that
persists between runs. It computes over the file you hand it and prints
the answer.

It is useful as a component, as a reference for how a result should be
labelled, and as something an agent can drive without lying to you. It is
not a replacement for anything a bank runs.

### What does it deliberately not do

- No market data. It fetches none, and there is no provider to configure.
- No orders. It opens no broker connection and has no path to one.
- No option pricing, no Greeks, no volatility surface. Those do not fit
  the linear contract and are refused rather than approximated.
- No credit migration, no nonlinear margin, no liquidity modelling.
- No forecast. Everything it produces describes a sample you supplied or
  a scenario you specified.

### Can I use it at work

Only under a separate written agreement. The licence is PolyForm
Noncommercial, and use inside a fund, a bank, a trading desk or any
business that runs a book is exactly what that excludes. See
[LICENSES.md](LICENSES.md). The answer to a polite request is not
automatically no.

## The numbers

### What does a positive VaR mean here

A loss. The convention is stated on every result and on every page: a
positive VaR or Expected Shortfall is a loss, a negative one is a gain,
and neither is floored at zero. Stress P&L is signed and loss is its
negation, so a negative loss is a scenario the book gains in.

That last one catches people. A scenario showing a loss of -1,843,000 is a
scenario you make money in.

### Does it scale my daily numbers to a ten-day horizon

No. Each P&L observation you supply must already span the horizon you
state. There is no square-root-of-time scaling anywhere, because applying
it silently to a sample whose dependence nobody checked is how a number
stops meaning anything.

### Why does it refuse a scenario that omits an asset

Because an omitted shock and a zero shock are different statements, and
guessing which you meant would change the answer. Every scenario must name
exactly the assets in the book, including an explicit zero where nothing
moves.

### What is the degraded flag

It means the result was computed with something the project considers
insufficient. Today it has exactly one cause: fewer than 20 observations
of tail probability mass. It is a reporting threshold, not a confidence
test and not a statement that the number is wrong.

It is printed whether or not it is set, on every surface, because a page
that mentions degradation only when degraded teaches a reader to stop
looking for it.

### Are the example numbers real

No. Every file in `examples/` is synthetic and says so in its own `source`
field. The energy book is hand-written; its P&L series is a drawn sample
from a heavy-tailed distribution and the file records the exact recipe so
you can regenerate it. The scenario shapes are hand-chosen, not fitted to
any dated episode, and carry no probability.

### Are the ORE figures validated

No. They are a numerical regression: the same pinned inputs produce the
same numbers. That is worth having and it is not model validation, does
not establish calibration quality, and does not imply regulatory approval.
The figures in the documents come from one run against one upstream
checkout, recorded with the date it was observed.

## Running it

### Do I need the ORE extra

Only for `riskdesk xva`. Its wheel does not exist for every platform: it
resolves on macOS ARM64 and on linux/amd64 under CPython 3.13, and not on
linux/arm64. The installer attempts it and says plainly what happened.
Without it you still have tail risk, exposure and stress.

### The plugin is installed but the agent lists no tools

Almost always because the plugin was installed without the runtime, or
because `riskdesk-mcp` is not on the `PATH` the agent launches with.
Installing a plugin does not install the software. See
[INSTALL.md](INSTALL.md), which ends with a one-line check.

### Can I expose the dashboard to my team

No, and it refuses to let you. It binds a loopback address and rejects any
other host with a non-zero exit, because it has no authentication of any
kind. Putting a risk book on a network should be a deliberate act with a
login in front of it, not a flag.

### Is there a hosted version

Yes, at `riskdesk.avidquant.com`, with three calculation tools and a
status tool, no login, and a synthetic demo book. It cannot run
`risk_xva`, because that reads an ORE project directory on your own
machine. For real positions the local install is the better choice: it
computes on your machine and sends nothing anywhere. See
[PRIVACY.md](PRIVACY.md).

## Trusting it

### How do I know the documentation is true

Because the build fails when it is not. `scripts/evidence.py` records
every figure the documents quote, with where it came from, and a test runs
the check, so the suite goes red when the prose and the repository
disagree. Figures measured in the checkout are marked `measured`; the ORE
values, which came from a run against an upstream checkout that is not in
this repository, are marked `pinned` with the date.

Change a digit in a README badge and the suite fails. That is the single
feature this project would most like you to look at.

### How do you know the tests can fail

`scripts/mutate.py` breaks the analytics on purpose, 33 ways, and requires
the tests to notice: sign flips, the quantile boundary, gross counted as
net, the leverage divisor, the degraded flag and every validation rule.
Two of the 33 are recorded as equivalent, with the measurement that
justifies calling them that rather than an argument.

### What has actually been measured, and what has not

`docs/IMPLEMENTATION.md` is the honest ledger, kept in VERIFIED, UNKNOWN,
ASSUMPTIONS and PLAN sections. Read the UNKNOWN section first. It names
what was not measured, including things it would be convenient to imply,
such as which Python versions were exercised locally and which were only
reported by CI.

### Can I run this on a loop or a schedule

There is nothing to poll. This software fetches no data, so nothing
changes between two runs unless you change a file, and a scheduled run
would recompute the same answer from the same input and report it as news.

The six commands are single-shot by design: each one runs, reports, and
ends. There is no goal-based loop because there is no completion criterion
to check. If a number matters enough to watch, the thing that changes is
your book, and that change happens in your systems rather than here.

### Who wrote this

One person. There is no team, no support contract and no roadmap
commitment. Issues get an answer; see [SECURITY.md](SECURITY.md) for how
to report something privately and [CONTRIBUTING.md](CONTRIBUTING.md) for
what a pull request needs.
