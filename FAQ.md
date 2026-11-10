# Questions about Risk Desk

The questions are weighted towards what the software does not do. In an
evaluation for a desk, those answers decide the outcome.

## Scope and limits

### What is it, in short

Risk Desk is a small, auditable risk calculator over supplied files. It
computes VaR
and Expected Shortfall with backtests, signed linear exposure and Greeks
for European options. It also covers attribution, limits, liquidity,
stress scenarios, SA-CCR, credit VaR and FRTB capital pieces. It exposes
the same functions to an agent over MCP, and adapts a local Open Source
Risk Engine project for counterparty exposure and XVA.

### Is this a risk system

No. It has no position store, no market-data connection, no end-of-day
process and no entitlements. It has no audit trail beyond the input hash
it records, and no notion of a book that persists between runs. It
computes over the supplied file and prints the result.

It is useful as a component and as a reference for how to label a
result. An agent can also drive it and return each result with its labels
attached. It is not a replacement for anything a bank runs.

### What does it deliberately not do

- No market data. It fetches none, and there is no provider to configure.
- No orders. It opens no broker connection and has no path to one.
- No option pricing beyond European calls and puts with one flat vol each:
  no American or exotic options, no implied volatility solving, no
  volatility surface. The linear tools refuse options rather than
  approximating them. `risk_derivatives_*` values the European ones.
- No credit migration and no nonlinear margin. Liquidity is a spread cost
  and a participation-rate schedule, not market impact.
- No forecast. Everything it produces describes a sample you supplied or
  a scenario you specified.

### Can I use it at work

Only under a separate written agreement. The licence is PolyForm
Noncommercial, and use inside a fund, a bank, a trading desk or any
business that runs a book is exactly what that excludes. See
[LICENSES.md](LICENSES.md). A request for such an agreement is considered
on its merits.

## The numbers

### What does a positive VaR mean here

A loss. The convention is stated on every result and on every page: a
positive VaR or Expected Shortfall is a loss, a negative one is a gain,
and neither is floored at zero. Stress P&L is signed and loss is its
negation, so a negative loss is a scenario the book gains in.

For example, a scenario that shows a loss of -1,843,000 is a scenario in
which the book gains.

### Does it scale my daily numbers to a ten-day horizon

No. Each supplied P&L observation must already span the stated horizon.
No square-root-of-time scaling is applied anywhere, because the
dependence of the sample is not tested.

### Why does it refuse a scenario that omits an asset

An omitted shock and a zero shock are different statements, and a guess
between them changes the result. Every scenario must name
exactly the assets in the book, including an explicit zero where nothing
moves.

### What is the degraded flag

It means the result was computed with something the project considers
insufficient. For historical tail risk the one cause is fewer than 20
observations of tail probability mass. The v0.2 tools add their own
causes, for example a GARCH-t fit that did not converge or an exposure
grid with no one-year date. `degraded_reason` names each one. It is a
reporting flag, not a confidence test and not a statement that the
number is wrong.

It is printed on every surface, whether or not it is set. A page that
mentions degradation only when degraded teaches a reader to stop looking
for it.

### Are the example numbers real

No. Every file in `examples/` is synthetic and says so in its own `source`
field. The energy book is hand-written. Its P&L series is a drawn sample
from a heavy-tailed distribution, and the file records the exact recipe
so that the series can be regenerated. The scenario shapes are hand-chosen, not fitted to
any dated episode, and carry no probability.

### Are the ORE figures validated

No. They are a numerical regression, in which the same fixed inputs
produce the same numbers. A regression is not model validation, does not
establish calibration quality, and does not imply regulatory approval.
The figures in the documents come from one run against one upstream
checkout, recorded with the date it was observed.

## Running it

### Do I need the ORE extra

Only for `riskdesk xva`. Its wheel does not exist for every platform: it
resolves on macOS ARM64 and on linux/amd64 under CPython 3.13, and not on
linux/arm64. The installer attempts it and reports the outcome.
Without it, every other command and tool still works.

### The plugin is installed but the agent lists no tools

Almost always because the plugin was installed without the runtime, or
because `riskdesk-mcp` is not on the `PATH` the agent launches with.
Installing a plugin does not install the software. See
[INSTALL.md](INSTALL.md), which ends with a one-line check.

### Can I expose the dashboard to my team

No. It binds a loopback address and rejects any other host with a
non-zero exit, because it has no authentication of any kind. Putting a risk book on a network must be a deliberate act with a
login in front of it, not a flag.

### Is there a hosted version

Yes, at `riskdesk.avidquant.com`, with every local tool except
`risk_xva`, 29 in all, no login, and synthetic examples. It cannot run
`risk_xva`, because that tool reads an ORE project directory on the local
machine. For real positions the local install is the better choice,
because it computes locally and sends nothing anywhere. See
[PRIVACY.md](PRIVACY.md).

## Trusting it

### How do I know the documentation is true

Because the build fails when it is not. `scripts/evidence.py` records
every figure the documents quote, with where it came from. A test runs
the check, so the suite goes red when the prose and the repository
disagree. Figures measured in the checkout are marked `measured`. The ORE
values came from a run against an upstream checkout that is not in this
repository. They are marked `pinned`, with the date.

A changed digit in a README badge makes the suite fail.

### How do you know the tests can fail

`scripts/mutate.py` applies 33 deliberate faults to the analytics and
requires the tests to detect each one. The faults cover sign flips, the
quantile boundary, gross counted as net, the leverage divisor, the
degraded flag and every validation rule. Two of the 33 are recorded as
equivalent, with the measurement that supports that classification.

### What has actually been measured, and what has not

`docs/IMPLEMENTATION.md` is the evidence ledger, kept in VERIFIED,
UNKNOWN, ASSUMPTIONS and PLAN sections. Read the UNKNOWN section first.
It names what was not measured. One example is which Python versions were
exercised locally and which were only reported by CI.

### Can I run this on a loop or a schedule

There is nothing to poll. This software fetches no data, so nothing
changes between two runs unless an input file changes. A scheduled run
recomputes the same result from the same input.

The 10 commands are single-shot by design: each one runs, reports, and
ends. There is no goal-based loop because there is no completion criterion
to check. A number changes only when the book changes, and that change
occurs in the systems that hold the book.

### Who wrote this

One person. There is no team, no support contract and no roadmap
commitment. Issues get an answer. See [SECURITY.md](SECURITY.md) for how
to report something privately, and [CONTRIBUTING.md](CONTRIBUTING.md) for
what a pull request needs.
