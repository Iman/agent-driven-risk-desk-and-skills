# Connect Risk Desk

The public service is live. The settings below connect to it. For work on
real positions, prefer the local plugin, which computes on your machine.

The public report is at https://riskdesk.avidquant.com/.
The Streamable HTTP MCP endpoint is `https://riskdesk.avidquant.com/mcp`.
It requires no login. The public report uses synthetic data.

The hosted service provides four tools: `risk_desk_status`, `risk_tail`,
`risk_exposure` and `risk_stress`. Call status first. The three calculation
tools accept a `request` object; omitting it selects the synthetic demo.
Discover the current input schema through MCP before supplying data.
Counterparty XVA requires the local plugin and a trusted ORE project.

## ChatGPT

Use ChatGPT's developer-mode connection flow to add the MCP URL above.
Choose no authentication. Availability depends on your account and
workspace settings. Refresh the tool list after connecting, then ask:

> Check Risk Desk status, then explain the synthetic energy book's tail
> risk. State the currency, horizon, loss signs and degraded status first.

The hosted plugin includes three skills in `plugins/risk-desk-hosted`.
The skills guide reporting and distinguish demo data from supplied data.
Connecting the MCP endpoint alone does not install those skill files.
MCP prompts are also available, but a client need not expose them; the
shared reporting instructions are included in MCP initialization.

See the official [connection and testing guide](https://developers.openai.com/plugins/deploy/connect-chatgpt)
and [skill guide](https://learn.chatgpt.com/docs/build-skills).
This repository does not claim publication in the ChatGPT directory.

## Codex

Add the hosted server:

```sh
codex mcp add riskdesk-hosted --url https://riskdesk.avidquant.com/mcp
codex mcp get riskdesk-hosted
```

For local skill discovery, copy the three directories from `openai-skills/`
into `.agents/skills/` in the project where you want to use them. Preserve
each skill's `agents/openai.yaml`, which declares the hosted MCP dependency.
Use `$risk-tail`, `$risk-portfolio` or `$risk-stress` in a prompt.

Alternatively, install the packaged hosted plugin through a configured
Codex plugin marketplace. Its `.codex-plugin/plugin.json` points to both
the skills and `.mcp.json`. Avoid configuring the same hosted server twice.
Use either the hosted or local Risk Desk plugin in a session: their
calculation tools share names.

See the official [Codex MCP configuration guide](https://learn.chatgpt.com/docs/extend/mcp?surface=cli).

## OpenAI Responses API

Include this object in the `tools` array of a Responses API request:

```json
{
  "type": "mcp",
  "server_label": "riskdesk",
  "server_url": "https://riskdesk.avidquant.com/mcp",
  "allowed_tools": [
    "risk_desk_status", "risk_tail", "risk_exposure", "risk_stress"
  ],
  "require_approval": "always"
}
```

Your OpenAI API credential authenticates the request to OpenAI. Risk Desk
does not need that credential; do not send it to the MCP endpoint.
When the response contains `mcp_approval_request`, inspect its tool and
arguments before submitting an `mcp_approval_response` in the next turn.
Follow the official [Responses MCP guide](https://developers.openai.com/api/docs/guides/tools-connectors-mcp)
for the request and approval flow.

Use the same reporting instructions in API or agent workflows: call status
first, preserve currency and horizon, state loss signs and degraded status,
and label synthetic results. Do not assume that an API request loads local
`SKILL.md` files. Supply these instructions explicitly or configure skills
through the API's supported skill workflow.

Before sending a real portfolio, establish permission to share it with
both services. The public endpoint has no hosted XVA, market-data feed,
broker connection or order-placement tool.
