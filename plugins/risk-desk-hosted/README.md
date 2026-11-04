# risk-desk-hosted plugin

## The endpoint is live

`https://riskdesk.avidquant.com/mcp` answers and needs no login. Since
4 November 2026 it serves the 0.2 set in the table below. Call
`risk_desk_status` to see the tools and the hosted limits.

Every tool runs a synthetic example when no request is sent. It holds no
market data, places no order, and cannot run `risk_xva`, because that
reads an ORE project directory on the caller's own machine.

**[The local plugin](../risk-desk) remains the better choice for real
work**: it computes on your machine, sends nothing anywhere, and it is
the only one that can run `risk_xva`.

## Install in Claude Code

```sh
/plugin install risk-desk-hosted --marketplace Iman/agent-driven-risk-desk-and-skills
```

## What the 0.2 plugin carries

One remote MCP server, `https://riskdesk.avidquant.com/mcp`, carrying the
twelve skills in `skills/`. It is built from `openai-skills/` at the
repository root. Edit the sources there and rebuild with
`python scripts/package_plugin.py`, rather than editing the copies here.

Every local tool except `risk_xva`, under the same name, all read-only:

| Skill | Tools |
| --- | --- |
| (status) | `risk_desk_status`: availability, limits and reporting conventions |
| `risk-tail` | `risk_tail`, `risk_tail_models` |
| `risk-backtest` | `risk_backtest` |
| `risk-portfolio` | `risk_exposure` |
| `risk-stress` | `risk_stress`, `risk_stress_replay`, `risk_scenario_library`, `risk_reverse_stress`, `risk_scenario_scale` |
| `risk-derivatives` | `risk_derivatives_greeks`, `risk_derivatives_grid`, `risk_derivatives_historical` |
| `risk-attribution` | `risk_covariance`, `risk_var_attribution`, `risk_es_attribution`, `risk_factor_exposure` |
| `risk-limits` | `risk_limits`, `risk_what_if` |
| `risk-liquidity` | `risk_liquidity` |
| `risk-counterparty` | `risk_saccr`, `risk_exposure_profile` |
| `risk-credit` | `risk_credit_asrf`, `risk_credit_copula` |
| `risk-frtb` | `risk_frtb_imcc`, `risk_frtb_ima_capital`, `risk_frtb_pla`, `risk_frtb_backtest`, `risk_frtb_sbm_fx` |
| `risk-data-import` | none of its own: builds the request for the tools above |

The hosted service adds limits the local runtime does not have: a request
and response size bound, a cap on the GARCH sample and on FX currencies,
and a shared time budget for the slowest tools. `risk_desk_status` states
them.

The calculation tools also accept an omitted `request` for a shipped
synthetic example. Each skill calls status first and distinguishes that
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

The Codex manifest at `.codex-plugin/plugin.json` includes nine positive
test cases, three negative cases and release notes under
`extensions.com.openai`. Rebuild the upload with
`python scripts/package_plugin.py`. The hosted ZIP is
`dist/risk-desk-hosted-plugin.zip` at the repository root.

Uploaded cases are managed by the package. To change them, edit the
manifest and upload the rebuilt ZIP. Before submitting, run the prompts
through the connected plugin. Expected behaviour is not a record of a
completed conversation test.

The recording URL is omitted until a real walkthrough is available. Enter
its reviewer-accessible URL in the portal, or add `demo_recording_url`
under `extensions.com.openai.review` and rebuild. Countries and translations
are omitted so this upload preserves the portal's existing settings.

## What it will not do

`risk_xva` is deliberately absent. Counterparty XVA reads a
trusted local ORE project directory, and a remote endpoint cannot read
files on your machine. That work stays in the local plugin. Listing it
here puts a tool in the list that can never run.

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
