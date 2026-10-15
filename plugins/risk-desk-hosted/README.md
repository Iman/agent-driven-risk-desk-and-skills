# risk-desk-hosted plugin

## The endpoint is live

`https://riskdesk.avidquant.com/mcp` answers and advertises `risk_tail`,
`risk_exposure`, `risk_stress` and `risk_desk_status`. It needs no login.

It serves a synthetic energy book. It holds no market data, places no
order, and cannot run `risk_xva`, because that reads an ORE project
directory on the caller's own machine.

**[The local plugin](../risk-desk) remains the better choice for real
work**: it computes on your machine, sends nothing anywhere, and it is
the only one that can run `risk_xva`.

## What it will be

One remote MCP server, `https://riskdesk.avidquant.com/mcp`, carrying the
three skills in `skills/`. It is built from `openai-skills/` at the
repository root; edit the sources there and rebuild with
`python scripts/package_plugin.py` rather than editing the copies here.

| Tool | What it does |
| --- | --- |
| `risk_desk_status` | Availability, synthetic demo, limits and reporting conventions |
| `risk_tail` | Historical VaR and Expected Shortfall over P&L you supply |
| `risk_exposure` | Gross and net exposure, leverage, concentration |
| `risk_stress` | Explicit shocks applied to linear positions |

The calculation tools also accept an omitted `request` for the synthetic
energy-book demo. Each skill calls status first and distinguishes that
demo from data the user supplies.

For ChatGPT, Codex and Responses API setup, see the
[connection guide](https://github.com/Iman/agent-driven-risk-desk-and-skills/blob/main/docs/OPENAI.md).

## Hosted privacy and support

Read the [hosted privacy policy](https://riskdesk.avidquant.com/privacy)
before sending data. It covers supplied inputs, service providers,
retention, diagnostics and deletion. The repository's local-software
privacy statement does not replace it.

An MCP calculation does not create a stored browser report. The separate
browser upload feature holds reports in memory, expires access after
one hour and offers early deletion. Your chat provider handles messages
and tool results under its own policy.

[Terms of service](https://riskdesk.avidquant.com/terms) and
[support](https://riskdesk.avidquant.com/support) apply to the hosted
service. Use these public URLs when submitting the plugin.

## Submission review data

The Codex manifest at `.codex-plugin/plugin.json` includes five positive
test cases, three negative cases and release notes under
`extensions.com.openai`. Rebuild the upload with
`python scripts/package_plugin.py`; the hosted ZIP is
`dist/risk-desk-hosted-plugin.zip` at the repository root.

Uploaded cases are managed by the package. To change them, edit the
manifest and upload the rebuilt ZIP. Run the prompts through the connected
plugin before submitting; expected behavior is not a record of a completed
conversation test.

The recording URL is omitted until a real walkthrough is available. Enter
its reviewer-accessible URL in the portal, or add `demo_recording_url`
under `extensions.com.openai.review` and rebuild. Countries and translations
are omitted so this upload preserves the portal's existing settings.

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
