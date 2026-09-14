import asyncio
import json
import subprocess
import sys
import pytest
from riskdesk.server import server

pytestmark = pytest.mark.integration


def test_mcp_lists_typed_tools_and_calculates_tail():
    async def check():
        tools=await server.list_tools()
        assert {t.name for t in tools}=={'risk_tail','risk_exposure','risk_stress','risk_xva'}
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
