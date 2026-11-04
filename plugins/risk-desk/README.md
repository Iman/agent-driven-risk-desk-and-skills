# risk-desk plugin

The local Risk Desk plugin: 30 MCP tools, 14 skills, commands and agents for
portfolio risk that an agent can drive from data the caller supplies. It
covers historical and model VaR and Expected Shortfall with backtests,
exposure and leverage, Greeks and full revaluation of European options,
risk attribution, limits and pre-trade what-if, liquidity-adjusted VaR,
explicit, historical and reverse stress, SA-CCR and exposure profiles,
portfolio credit VaR, FRTB capital pieces, and XVA through a local Open
Source Risk Engine project.

The MCP server entry expects `riskdesk-mcp` on PATH, which `install.sh` at
the repository root puts there. Without it the skills remain instructions
and cannot compute numbers. Every computation runs on your machine; nothing
is sent anywhere. For a remote server with no install, use the
`risk-desk-hosted` plugin, which serves every tool except `risk_xva`.

The skills, commands and agents in this folder are the sources: edit them
here. Results are research output, not investment advice, and they are not
a regulatory submission. See DISCLAIMER.md at the repository root, and
LICENSE in this folder (PolyForm Noncommercial 1.0.0).
