# Security

## Reporting a vulnerability

Report privately, not as a public issue. Use GitHub's private vulnerability
reporting on this repository, under Security, Report a vulnerability.

Tell me what you did, what happened, and what you expected. A reproduction
is worth more than a description. I will confirm receipt, and I will tell
you plainly if I disagree that something is a vulnerability rather than
letting the report go quiet.

## What is in scope

The MCP server, because it accepts input from a model. The input models,
because they are the only thing standing between an untrusted document and
the arithmetic. The ORE adapter, because it reads an XML project from disk,
resolves paths out of it and starts a process. The installer, because it
creates an environment and installs packages. The report writer, because it
puts caller-supplied strings into an HTML page.

Two classes I care about in particular:

- Anything that makes the ORE adapter read or write outside the directories
  it declares. It requires every referenced input to resolve inside the
  project, requires the output directory to be new and outside it, refuses
  symlinks, refuses output parameters that are not simple filenames, and
  records a SHA-256 of every input file. A way past any of those is a
  vulnerability.
- Anything that makes a tool call reach outside its advertised arguments,
  or that gets markup or script into a written report from an input field.

The process boundary the ORE adapter uses is isolation, not a sandbox. It
is not intended to make a hostile ORE configuration safe, and a report that
a deliberately hostile project can misbehave is a statement of the
documented limit rather than a finding. Read an unfamiliar project before
running it.

## What is not in scope

Your input being wrong. This software computes over the files you give it,
records a hash of them, and reports what it did. It does not and cannot
check that your P&L series, your market values or your shocks are right.

Losing money. This is research software, it fetches no market data and it
places no orders. See DISCLAIMER.md.

The absence of authentication. Everything here runs locally as you. The MCP
server speaks stdio to a parent process and binds no socket. If you expose
it some other way, that is a decision you have made and its consequences
are yours.

## Reporting without identifying yourself

You do not need to tell me where you are or how you reach the internet to
report a bug or a vulnerability, and you should not be asked. A
reproduction that runs anywhere is worth more than a description of your
network, and every diagnostic question worth asking has a form that does
not require you to identify yourself.

## What this software does with your data

It reads the files you point it at and writes results where you tell it to.
It sends nothing about you or your usage anywhere. It opens no network
connection at runtime: no market-data request, no broker request, no
telemetry. The only network access in the project is pip, during install.

There are no credentials to store, because there is no service to
authenticate to.
