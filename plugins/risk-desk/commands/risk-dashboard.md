---
description: Serve the results in a browser on a loopback address, and explain the refusal if it will not start
argument-hint: [PORT]
arguments: [port]
---

Start the dashboard on $port, or 8899 when no port is given.

1. `riskdesk dashboard`. When a port was given, add `--port $port`. The
   defaults read the synthetic energy book from `examples/`; pass
   `--input`, `--tail`, `--exposure` or `--xva` to serve the caller's own
   files.
2. Give the URL it printed, and say it is loopback only. It binds a
   loopback address and refuses any other host, because it has no
   authentication of any kind. Do not offer `--host` as a way to share it
   with a colleague; that is what the refusal exists to prevent.
3. It makes no outbound request and reads no path from the request. Every
   view prints the sign convention and the degraded flag whether or not
   the flag is set.
4. If it did not start, read the exit code and say which it was:

   - 64, the host given was not a loopback address.
   - 66, an input file was not found.
   - 67, an input file did not meet its contract.
   - 73, the port is already in use, so suggest another.

   Each prints one sentence on stderr naming what went wrong. Quote it
   rather than guessing.
5. Stop it with ctrl-c. It writes nothing and leaves nothing behind.
6. The counterparty XVA view never runs ORE. It reprints a result the
   adapter already wrote, or explains what is missing, because ORE needs a
   local project directory and a separate process.
