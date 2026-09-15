"""Check the public report and MCP tools using synthetic data only."""
import json
import sys
import urllib.request

base = (sys.argv[1] if len(sys.argv) > 1 else
        'https://riskdesk.avidquant.com').rstrip('/')

def get(path):
    request = urllib.request.Request(base + path, headers={'User-Agent': 'RiskDesk-Check/0.1'})
    with urllib.request.urlopen(request, timeout=30) as response:
        body = response.read().decode()
        assert response.status == 200
        assert not response.headers.get('WWW-Authenticate')
        print(path, response.status)
        return body

assert get('/healthz') == 'ok'
assert 'synthetic' in get('/').lower()
status = json.loads(get('/api/status'))
assert status['status'] == 'available'
assert status['data_mode'] == 'synthetic_sample'
assert status['market_data'] is False

def rpc(method, params):
    data = json.dumps({'jsonrpc':'2.0','id':1,'method':method,'params':params}).encode()
    req = urllib.request.Request(base + '/mcp', data=data, headers={
        'Content-Type':'application/json', 'Accept':'application/json, text/event-stream',
        'Host':'riskdesk.avidquant.com', 'User-Agent':'RiskDesk-Check/0.1'})
    with urllib.request.urlopen(req, timeout=30) as response:
        result = json.load(response)
    assert 'error' not in result, result
    return result['result']

rpc('initialize', {'protocolVersion':'2025-03-26','capabilities':{},
                   'clientInfo':{'name':'riskdesk-smoke','version':'1.0'}})
tools = rpc('tools/list', {})['tools']
names = {tool['name'] for tool in tools}
assert names == {'risk_desk_status','risk_tail','risk_exposure','risk_stress'}, names
for tool in tools:
    assert tool['inputSchema'] and tool['outputSchema']
    assert tool['annotations']['readOnlyHint'] is True
    result = rpc('tools/call', {'name':tool['name'],'arguments':{}})
    assert not result.get('isError'), result
    content = result['structuredContent']
    if tool['name'] != 'risk_desk_status':
        assert content['data_origin'] == 'synthetic_demo'
        assert 'degraded' in content and 'degraded_reason' in content
    print(tool['name'], 'PASS')
sample = {'as_of':'2026-09-15','currency':'GBP','source':'Synthetic deployment check',
          'data_mode':'synthetic','pnl':[-100,-50,10,20,5],'confidence':0.99,
          'horizon_days':1,'portfolio_value':10000}
result = rpc('tools/call', {'name':'risk_tail','arguments':{'request':sample}})
assert not result.get('isError'), result
assert result['structuredContent']['degraded'] is True
assert result['structuredContent']['data_origin'] == 'caller_supplied'
print('supplied synthetic sample degraded warning PASS')
