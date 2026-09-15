"""A local web view over the same functions the CLI and MCP tools call.

Five modules, so the reviewer who knows Option Desk's dashboard recognises
the split: `maths` is display arithmetic, `data` shapes results, `page`
renders HTML, `server` owns the socket and what it refuses to bind, and
`app` wires them together and turns every foreseeable failure into a
sentence on stderr rather than a traceback or a silence.

Nothing here computes risk, adds a dependency, or reaches the network.
"""
