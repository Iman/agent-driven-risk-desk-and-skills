#!/usr/bin/env python3
"""Print the MCP tools the local server exposes, with their first line.

The server object is asked in this process rather than a stdio session
being opened, so the demo lists what the code registers and not what a
transport happened to answer. The real stdio round trip is covered by the
integration tests instead.
"""
import asyncio


def tool_lines():
    from riskdesk.server import server

    async def collect():
        return await server.list_tools()

    rows = []
    for tool in sorted(asyncio.run(collect()), key=lambda t: t.name):
        first = (tool.description or "").strip().split("\n")[0]
        rows.append("  {:<16} {}".format(tool.name, first))
    return rows


def main():
    rows = tool_lines()
    print("  {} MCP tools, served over stdio, no network calls".format(
        len(rows)))
    for row in rows:
        print(row)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
