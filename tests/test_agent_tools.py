"""riskdesk-agent tools are the FastMCP registry, not a second list.

Building a tool calls nothing. The tests that invoke one run a real Risk
Desk function in process, through server.call_tool, on a shipped example.
"""
import ast
import json
from pathlib import Path

import pytest
from langchain_core.tools import StructuredTool
from mcp.server.fastmcp import FastMCP

from riskdesk import scenarios, server as server_module
from riskdesk.cli import HANDLERS
from riskdesk.models import TailRequest
from riskdesk_agent import tools as tools_module
from riskdesk_agent.tools import desk_tools, read_only_names, tool_specs

ROOT = Path(__file__).resolve().parent.parent
pytestmark = pytest.mark.unit


def registered_in_source():
    """Names of the functions decorated @server.tool in server.py, read from its syntax tree."""
    tree = ast.parse((ROOT / "src" / "riskdesk" / "server.py").read_text(encoding="utf-8"))
    return sorted(node.name for node in ast.walk(tree)
                  if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
                  and any("server.tool" in ast.unparse(d) for d in node.decorator_list))


def example(name):
    return json.loads((ROOT / "examples" / name).read_text(encoding="utf-8"))


def test_the_tools_are_exactly_the_functions_the_server_registers():
    """Catches a tool missing from the agent, or one the server does not have."""
    tools = desk_tools()
    assert all(isinstance(tool, StructuredTool) for tool in tools)
    assert sorted(tool.name for tool in tools) == registered_in_source()
    assert len(registered_in_source()) == len({tool.name for tool in tools})


def test_a_tool_registered_on_the_server_appears_without_an_edit(monkeypatch):
    """Catches a hand-written list: a new registration must reach the agent by itself."""
    fresh = FastMCP("probe")

    @fresh.tool()
    def probe_tool(value: int) -> dict:
        """A probe."""
        return {"value": value}

    monkeypatch.setattr(server_module, "server", fresh)
    tools = desk_tools()
    assert [tool.name for tool in tools] == ["probe_tool"]
    assert tools[0].invoke({"value": 3}) == {"value": 3}


def test_descriptions_and_schemas_are_the_registry_s_own():
    """Catches a schema rebuilt by hand, which would drift from the pydantic model."""
    specs = {spec["name"]: spec for spec in tool_specs()}
    for tool in desk_tools():
        assert tool.description == specs[tool.name]["description"]
        assert tool.args_schema == specs[tool.name]["parameters"]
    request = specs["risk_tail"]["parameters"]["$defs"]["TailRequest"]["properties"]
    assert set(request) == set(TailRequest.model_fields)


def test_only_the_ore_runner_is_marked_as_writing():
    """Catches the read-only set losing its source, the server's annotations."""
    names = {spec["name"] for spec in tool_specs()}
    assert names - set(read_only_names()) == {"risk_xva"}


def test_include_narrows_and_fails_closed():
    """Catches include being ignored, or a typo returning the whole desk."""
    assert [t.name for t in desk_tools(include=["risk_tail"])] == ["risk_tail"]
    assert desk_tools(include=["risk_not_a_tool"]) == []
    assert desk_tools(include=[]) == []


def test_a_tool_returns_what_the_cli_handler_returns():
    """Catches the agent path and the CLI path giving different answers."""
    request = example("tail.json")
    via_agent = desk_tools(include=["risk_tail"])[0].invoke({"request": request})
    assert via_agent == json.loads(json.dumps(HANDLERS["tail"](request)))
    assert via_agent["degraded"] is True


def test_a_tool_without_arguments_returns_its_function_s_result():
    library = desk_tools(include=["risk_scenario_library"])[0].invoke({})
    assert library == json.loads(json.dumps(scenarios.scenario_library()))


def test_invalid_arguments_are_refused_by_the_server_s_validation():
    """Catches the agent bypassing the pydantic models the MCP path enforces."""
    with pytest.raises(Exception) as caught:
        desk_tools(include=["risk_tail"])[0].invoke({"request": {"pnl": [1.0]}})
    assert "validation error" in str(caught.value)


def test_the_status_tool_states_the_conventions_the_prompt_uses():
    status = desk_tools(include=["risk_desk_status"])[0].invoke({})
    assert status["conventions"] == list(server_module.CONVENTIONS)
    assert sorted(status["tools"]) == registered_in_source()


def test_tool_specs_needs_no_langchain_object():
    specs = tool_specs()
    assert all(set(spec) == {"name", "description", "parameters", "read_only"} for spec in specs)
    assert tools_module.tool_specs is tool_specs
