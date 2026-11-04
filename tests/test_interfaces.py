import asyncio
import json
import subprocess
import sys
import pytest
from riskdesk.server import server
from test_cli import TOOLS

pytestmark = pytest.mark.integration


def test_mcp_lists_typed_tools_and_calculates_tail():
    async def check():
        tools=await server.list_tools()
        assert {'risk_tail','risk_exposure','risk_stress','risk_xva','risk_desk_status'} <= {t.name for t in tools}
        assert len(tools)==30
        value=await server.call_tool('risk_tail',{'request':dict(as_of='2026-09-12',currency='USD',
            source='test',data_mode='synthetic',pnl=[-100,-50,0,50],confidence=.625,horizon_days=1,portfolio_value=1000)})
        assert '83.333' in str(value)
    asyncio.run(check())


def test_cli_failure_is_json_and_nonzero(tmp_path):
    p=tmp_path/'bad.json';p.write_text('{}')
    proc=subprocess.run([sys.executable,'-m','riskdesk.cli','tail','--input',str(p)],capture_output=True,text=True)
    assert proc.returncode==1
    assert json.loads(proc.stdout)['error']=='ValidationError'


def test_real_mcp_stdio_process_returns_typed_risk_result():
    from mcp import ClientSession, StdioServerParameters
    from mcp.client.stdio import stdio_client
    async def check():
        parameters=StdioServerParameters(command=sys.executable,args=['-m','riskdesk.server'])
        async with stdio_client(parameters) as (reader,writer):
            async with ClientSession(reader,writer) as session:
                await session.initialize()
                result=await session.call_tool('risk_tail',{'request':dict(as_of='2026-09-12',currency='USD',
                    source='process test',data_mode='synthetic',pnl=list(range(-20,0)),confidence=.95,
                    horizon_days=1,portfolio_value=1000)})
                assert not result.isError
                payload=json.loads(result.content[0].text)
                assert payload['var']==20
                assert payload['currency']=='USD'
                bad=await session.call_tool('risk_tail',{'request':{}})
                assert bad.isError
    asyncio.run(check())


def registered_tools():
    return {t.name: t for t in asyncio.run(server.list_tools())}


def test_every_tool_is_registered_and_only_xva_writes():
    tools = registered_tools()
    assert set(tools) == set(TOOLS) | {"risk_scenario_library", "risk_desk_status", "risk_xva"}
    for name, tool in tools.items():
        hints = tool.annotations
        assert hints.readOnlyHint is (name != "risk_xva"), name
        assert hints.destructiveHint is False and hints.openWorldHint is False, name
        assert hints.idempotentHint is (name != "risk_xva"), name
        assert tool.description, name


def test_the_status_tool_lists_every_tool_and_the_conventions():
    from riskdesk import __version__
    from riskdesk.server import risk_desk_status
    status = asyncio.run(risk_desk_status())
    assert status["status"] == "available" and status["market_data"] is False
    assert status["riskdesk_version"] == __version__
    assert status["tools"] == sorted(registered_tools())
    assert status["data_modes"] == ["synthetic", "user-licensed"]
    assert status["xva_data_modes"] == ["synthetic", "user-licensed", "upstream-example"]
    assert any("Loss is positive" in line for line in status["conventions"])


def test_the_setup_doctor_gets_an_answer_from_a_real_server():
    """The doctor's own stdio round trip, through the riskdesk-mcp beside this interpreter."""
    from pathlib import Path
    doctor = Path(__file__).resolve().parent.parent / "plugins/risk-desk/skills/risk-setup/scripts/check_artifact.py"
    env = {"PATH": str(Path(sys.executable).parent), "HOME": str(Path.home())}
    proc = subprocess.run([sys.executable, str(doctor)], capture_output=True, text=True, timeout=120, env=env)
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert proc.stdout.split()[0] == "OK"
    assert "risk_desk_status through" in proc.stdout and "available" in proc.stdout
