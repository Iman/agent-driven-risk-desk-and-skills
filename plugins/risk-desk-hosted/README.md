# risk-desk-hosted plugin

## The endpoint is not live yet

`https://riskdesk.avidquant.com` does not resolve and nothing is deployed
behind it. This plugin is the client side, written and checked ahead of
the service so that the manifests, the skills and the tool names are
settled before anything is published to a directory. Installing it today
gives you a plugin whose MCP server will not answer. That is expected, and
it is not a fault in your setup.

**Use [the local plugin](../risk-desk) instead**, which works now, computes
on your machine, and sends nothing anywhere.

## What it will be

One remote MCP server, `https://riskdesk.avidquant.com/mcp`, carrying the
three skills in `skills/`. It is built from `openai-skills/` at the
repository root; edit the sources there and rebuild with
`python scripts/package_plugin.py` rather than editing the copies here.

| Tool | What it does |
| --- | --- |
| `risk_tail` | Historical VaR and Expected Shortfall over P&L you supply |
| `risk_exposure` | Gross and net exposure, leverage, concentration |
| `risk_stress` | Explicit shocks applied to linear positions |

## What it will not do

`risk_xva` is deliberately absent. Counterparty exposure and XVA read a
trusted local ORE project directory, and a remote endpoint cannot read
files on your machine. That work stays in the local plugin, and pretending
otherwise would put a tool in the list that could never run.

No market data is fetched, no order is placed, and nothing is stored on
your behalf that you did not send. `data_mode` records your declaration
about your rights to the data you send; it is a declaration, not a rights
certificate, and the service does not check it. Do not send a position
file you are not permitted to share with a third-party service.

Do not install this alongside the local `risk-desk` plugin. They expose
tools with the same names.

Research software, not investment advice. See
[DISCLAIMER.md](../../DISCLAIMER.md) and
[LICENSE](../../LICENSE).
