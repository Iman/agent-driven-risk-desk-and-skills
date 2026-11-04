"""The Risk Desk MCP tools, as LangChain tools.

There is no tool list here. Names, descriptions, input schemas and the
read-only flag are read from the FastMCP server in riskdesk.server, and a
call goes through server.call_tool, so an agent gets the same pydantic
validation and the same result an MCP client does. A tool added to the
server appears here without an edit, and one removed disappears.

Tools never compute. They return the JSON envelope the server returns,
which carries the provenance and the degraded flag.
"""

import asyncio
import json

from riskdesk import server as server_module


def _registry():
    # shortcut: asyncio.run cannot be used inside a running event loop; await
    # server.list_tools() directly there.
    return asyncio.run(server_module.server.list_tools())


def _result(content):
    """The tool's JSON envelope from FastMCP's single text block."""
    return json.loads(content[0].text)


def tool_specs():
    """The registry as plain dicts, without requiring LangChain."""
    return [{"name": tool.name, "description": tool.description,
             "parameters": tool.inputSchema,
             "read_only": bool(tool.annotations
                               and tool.annotations.readOnlyHint)}
            for tool in _registry()]


def read_only_names():
    """Tools the registry marks read only; risk_xva writes an ORE output."""
    return [spec["name"] for spec in tool_specs() if spec["read_only"]]


def _callables(name):
    async def arun(**arguments):
        return _result(await server_module.server.call_tool(name, arguments))

    def run(**arguments):
        return asyncio.run(arun(**arguments))

    return run, arun


def desk_tools(include=None):
    """StructuredTools for the registry, optionally narrowed by name.

    An include list that names nothing real yields no tools rather than all
    of them: a caller who meant to narrow the surface must not get the whole
    desk because of a typo.
    """
    from langchain_core.tools import StructuredTool

    tools = []
    for spec in tool_specs():
        if include is not None and spec["name"] not in include:
            continue
        run, arun = _callables(spec["name"])
        tools.append(StructuredTool(
            name=spec["name"], description=spec["description"],
            args_schema=spec["parameters"], func=run, coroutine=arun))
    return tools
