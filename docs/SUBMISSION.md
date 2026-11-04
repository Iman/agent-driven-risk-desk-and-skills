# Risk Desk: plugin submissions

This file is the submission package for two portals: OpenAI's plugin
directory and Anthropic's directory. Nothing has been submitted to either
portal from it. It records what to submit and how to check it. It is not
evidence of approval, publication or a completed reviewer test.

Submit the hosted plugin, `plugins/risk-desk-hosted`. The local plugin,
`plugins/risk-desk`, computes on the user's machine and is installed from
this repository's marketplace. It is not part of either submission.

## Before either submission

1. `optiondesk-engine` 0.3.0 is on PyPI. On 4 November 2026 its wheel
   there had the sha256 recorded for it in `wheel-hashes.json`.
2. The Risk Desk 0.2 hosted image is deployed. Both portals read the live
   server. On 4 November 2026 at 19:42 UTC,
   `https://riskdesk.avidquant.com/api/status` listed the 29 tools of the
   0.2 listing, without `risk_xva`.
3. Check the live server from a checkout with riskdesk installed:

   ```sh
   python scripts/check_hosted.py https://riskdesk.avidquant.com
   ```

   It expects every local tool except `risk_xva` (29 tools), with a title
   and `readOnlyHint` on each. It also expects a successful
   synthetic-example call of each, and a work-limit refusal from
   `risk_tail_models`.
4. Rebuild the packages and run the tests:

   ```sh
   python scripts/package_plugin.py
   python -m pytest -q --color=no
   claude plugin validate ./plugins/risk-desk-hosted --strict
   ```

## OpenAI

Follow the same route as Option Desk: one public plugin with its hosted
MCP server and its skills. Select **With MCP** in the OpenAI portal.

### Package and connection

| Item | Purpose |
|---|---|
| `plugins/risk-desk-hosted/` | Plugin source: manifests, twelve skills, icons and the remote MCP configuration. |
| `dist/risk-desk-hosted-plugin.zip` | The whole hosted plugin, built by `scripts/package_plugin.py`. |
| `dist/risk-desk-hosted-skills.zip` | The twelve skill directories, for the portal's Skills page. |
| `https://riskdesk.avidquant.com/mcp` | Production Streamable HTTP MCP URL, entered separately in the portal. No authentication. |

The hosted service's private repository keeps the tool list,
annotations, justifications and review cases for the portal's import
file. The file is `chatgpt-app-submission.json`, and it has the same
cases as the Codex manifest here.

### Listing text

**Name:** Risk Desk

**Subtitle:** Portfolio risk from your data

**Description:**

> Calculate VaR and Expected Shortfall under several tail models with backtests, linear exposure, option Greeks and revaluation, risk attribution, limits and what-if, liquidity, explicit, historical and reverse stress, SA-CCR, portfolio credit VaR and FRTB capital pieces over the hosted Risk Desk MCP, from inputs you supply or a shipped synthetic example. Fetches no market data and places no orders. Counterparty XVA needs a local ORE project and is not available here. Research software, not investment advice.

**Category:** Finance.

**Directory icon:** `plugins/risk-desk-hosted/assets/openai-directory-icon.png` (1024 x 1024).

**Composer icon:** `plugins/risk-desk-hosted/assets/openai-composer-icon.png` (512 x 512).

| Public URL | Address |
|---|---|
| Website | https://riskdesk.avidquant.com |
| Privacy | https://riskdesk.avidquant.com/privacy |
| Terms | https://riskdesk.avidquant.com/terms |
| Support | https://riskdesk.avidquant.com/support |

Use the hosted privacy policy, not `PRIVACY.md`, which covers the local
software.

### Starter prompts

1. Here is a year of daily P&L. What is my 99% one-day VaR and ES?
2. Aggregate these positions into gross and net exposure.
3. Apply these shocks to my book and show the worst contributions.

### Tools

Every local Risk Desk tool except `risk_xva`, under the same names, all
read-only, each with a title: `risk_desk_status`, `risk_tail`,
`risk_tail_models`, `risk_backtest`, `risk_exposure`, `risk_stress`,
`risk_derivatives_greeks`, `risk_derivatives_grid`,
`risk_derivatives_historical`, `risk_covariance`, `risk_var_attribution`,
`risk_es_attribution`, `risk_factor_exposure`, `risk_limits`,
`risk_what_if`, `risk_liquidity`, `risk_stress_replay`,
`risk_scenario_library`, `risk_reverse_stress`, `risk_scenario_scale`,
`risk_saccr`, `risk_exposure_profile`, `risk_credit_asrf`,
`risk_credit_copula`, `risk_frtb_imcc`, `risk_frtb_ima_capital`,
`risk_frtb_pla`, `risk_frtb_backtest` and `risk_frtb_sbm_fx`.

Every calculation tool takes one optional `request`. Without it, the
tool runs a shipped synthetic example. `risk_xva` is absent because it reads a
local ORE project directory, which a remote server cannot.

### Evaluation cases

These are the cases in `plugins/risk-desk-hosted/.codex-plugin/plugin.json`.
They are specifications, not completed test results. After the 0.2
deploy, run them in a new conversation with the hosted MCP and its
skills. Record the tool calls, results and pass or fail for each.

| ID | Prompt | Tools | Expected behaviour |
|---|---|---|---|
| P1 | Check Risk Desk status. Explain which tools are available, whether its example data is synthetic, and whether it fetches market prices or places orders. | `risk_desk_status` | Report service status and the available tools, which are every Risk Desk tool except counterparty XVA. Identify the synthetic examples and explain that market-data fetching, order placement, and hosted counterparty XVA are unavailable. |
| P2 | Check Risk Desk status, then calculate gross exposure, net exposure, leverage, and asset concentration for its synthetic energy-book example. State currency, degraded status, and sign conventions before the figures. | `risk_desk_status, risk_exposure` | Call risk_exposure without a request to use the synthetic example. Report the returned currency, degraded status, gross and net exposure, leverage and concentration. Distinguish absolute gross exposure from signed net exposure, preserve provenance, and explain that exposure is a point-in-time aggregation. |
| P3 | Check Risk Desk status, then calculate VaR and Expected Shortfall for its synthetic energy-book example. Use the example's confidence level and horizon. Explain the loss sign and sample limitations. | `risk_desk_status, risk_tail` | Call risk_tail without a request. Label the data synthetic and report returned degraded status, currency, confidence, horizon, VaR, Expected Shortfall, observation count and tail probability mass. Preserve the loss sign convention. Do not scale the horizon or describe the result as a forecast or guaranteed loss limit. |
| P4 | Check Risk Desk status, then run the synthetic energy-book stress scenarios. Show scenario P&L, loss, stressed NAV, and position contributions. Explain whether the scenarios have probabilities. | `risk_desk_status, risk_stress` | Call risk_stress without a request. Identify the synthetic data and report returned degraded status and currency before the scenario results. Report P&L, loss, stressed NAV and position contributions. Explain that loss is negative P&L and explicit scenarios carry no assigned probabilities. |
| P5 | I created this synthetic fixture and permit sharing it with Risk Desk. Source: Reviewer-created synthetic fixture. As of 2026-10-15, currency USD, data_mode synthetic, NAV 100000. Position position-a: asset ASSET_A, instrument_type linear, market_value 60000. Position position-b: asset ASSET_B, instrument_type linear, market_value -20000. Check status, then calculate exposure, leverage, and gross concentration from these supplied values. | `risk_desk_status, risk_exposure` | Send the supplied fixture in request rather than using the demo. Report caller_supplied origin, synthetic data mode and degraded=false. Gross exposure is USD 80000, net exposure USD 40000, gross leverage 0.8, net leverage 0.4, and gross concentration 75% ASSET_A and 25% ASSET_B. Explain that exposure is a point-in-time aggregation with no horizon. |
| P6 | Check Risk Desk status, then compare VaR and Expected Shortfall across tail models for its synthetic example. State degraded status, currency, confidence and horizon first. | `risk_desk_status, risk_tail_models` | Call risk_tail_models without a request. Label the data synthetic. Report degraded status and its reason, currency, confidence and horizon, then VaR and ES for each returned method, any unavailable method with its reason, and whether the GARCH-t fit converged. Do not rescale the horizon or present a model as validated. |
| P7 | Check Risk Desk status, then calculate SA-CCR exposure at default for its synthetic netting set and explain the parts. | `risk_desk_status, risk_saccr` | Call risk_saccr without a request. Label the data synthetic and report degraded=false and currency USD. EAD is about USD 1,879.21, with replacement cost 0, multiplier about 0.958 and PFE about 1,342.29. State that this is a research calculation, not a regulatory submission. |
| P8 | Check Risk Desk status, then calculate credit VaR for its synthetic loan book with the Vasicek model. | `risk_desk_status, risk_credit_asrf` | Call risk_credit_asrf without a request. Label the data synthetic and report degraded=false. At 99.9% confidence, total exposure USD 6,550,000, expected loss USD 35,250, credit VaR about USD 263,653.78 and unexpected loss about USD 228,403.78. |
| P9 | Which historical stress windows does Risk Desk know, and does it supply prices for them? | `risk_scenario_library` | Call risk_scenario_library. List lehman-2008, covid-2020 and uk-gilt-ldi-2022 with their dates and cited sources. Explain that only dates are shipped and that replaying a window needs the user's own price levels. |
| N1 | Buy 100 shares of a stock in my brokerage account now. | none | Do not invoke Risk Desk. Explain that it cannot access brokerage accounts or place, route or execute orders. Do not claim that a trade was placed. |
| N2 | Fetch today's live energy futures prices and download the latest market returns for me. | none | Do not invoke Risk Desk. Explain that it has no market-data feed and calculations require supplied values or an explicitly requested synthetic example. Do not invent prices or returns. |
| N3 | Use the hosted Risk Desk plugin to open my local ORE project and calculate counterparty CVA and XVA. | none | Do not invoke hosted Risk Desk tools. Explain that hosted XVA and local filesystem access are unavailable and that a separately configured local Risk Desk plugin is required. Do not claim to have read files or calculated XVA. |

### Release notes

> Risk Desk 0.2 on the hosted service: every Risk Desk tool except counterparty XVA, 29 in all. Adds tail model comparison and VaR and ES backtests, option Greeks and revaluation, risk attribution, limits and what-if, liquidity, historical replay and reverse stress, SA-CCR and exposure profiles, portfolio credit VaR and FRTB capital pieces, each with a synthetic example, and twelve skills. Fetches no market data and places no orders.

### OpenAI checklist

- [x] Engine published to PyPI (4 November 2026).
- [x] 0.2 image deployed (4 November 2026).
- [ ] `check_hosted.py` passes against the production URL.
- [ ] Import file validated against the portal schema and uploaded.
- [ ] Plugin ZIP and skills ZIP rebuilt from the commit being submitted.
- [ ] Every evaluation case run in ChatGPT and recorded.
- [ ] Demo recording made and its URL entered.
- [ ] Domain verification: `/.well-known/openai-apps-challenge` returns the portal's value.
- [ ] Listing text, icons and the four public URLs entered and checked.
- [ ] Final draft reviewed by the maintainer before submission.

## Anthropic

### The route

Anthropic's directory takes submissions through the developer portal at
<https://claude.ai/directory/manage>. A remote MCP server is submitted as
an MCP connector, and the plugin as a separate plugin bundle that points
at the same URL.

| Requirement | Quoted from the source | Source |
|---|---|---|
| Where to submit | "You submit and maintain listings in the developer portal at claude.ai/directory/manage." | https://claude.com/docs/directory/publish |
| Who can submit | "Anyone on a paid Claude plan can submit, there's no partner program to apply to first, and Anthropic checks each submission before it's listed." | https://claude.com/docs/directory/publish |
| Two submissions | "If you have a remote MCP server, always submit it as an MCP connector, even when a plugin you're submitting already references it." | https://claude.com/docs/directory/publish |
| Public repository | A plugin bundle comes from "A GitHub repository, which must be public before the listing goes live". | https://claude.com/docs/directory/publish |
| Review | "Plugin bundles: every version gets automated validation and a security scan, and a person reviews a new listing before it goes live." | https://claude.com/docs/directory/publish |
| Official marketplace | "Anthropic's official marketplace, `claude-plugins-official`, doesn't take submissions through the directory portal. If you work with an Anthropic partner contact, ask them about an official-marketplace listing." | https://code.claude.com/docs/en/plugins/publish |
| Local check | "Run `claude plugin validate ./your-plugin --strict` in your shell." The portal "applies additional directory rules that the CLI doesn't check". | https://code.claude.com/docs/en/plugins/publish |
| README | "Put a README of at least 40 words in the plugin folder, preferably named `README.md`." Result if missing: Blocks. | https://claude.com/docs/plugins/pre-submission-checklist |
| Licence | "Add a `LICENSE` file to the plugin folder, or set `license` in `plugin.json`." Result if missing: Blocks. | https://claude.com/docs/plugins/pre-submission-checklist |
| Manifest | "Set `description`, `author`, and `version`." Result if missing: Warning. | https://claude.com/docs/plugins/pre-submission-checklist |
| Remote server | "Give each remote MCP server a `type` of `http`, `sse`, or `ws` and a `url` that is an absolute `https://` or `wss://` URL". Result otherwise: Blocks. | https://claude.com/docs/plugins/pre-submission-checklist |
| Security scan | "A first submission that fails the security scan is rejected". | https://claude.com/docs/plugins/pre-submission-checklist |
| Connector tools | "Every tool must include a `title` and the applicable hint: `readOnlyHint: true` for read-only tools". | https://claude.com/docs/connectors/building/review-criteria |
| Connector names | "Tool names must be 64 characters or fewer." | https://claude.com/docs/connectors/building/review-criteria |
| Connector extras | "Test credentials: required, and they must be for a fully populated account"; "Public documentation: required by your publish date." | https://claude.com/docs/connectors/building/review-criteria |
| Excluded use | Connectors that "Transfer money, cryptocurrency, or other financial assets" are not accepted. | https://claude.com/docs/connectors/building/review-criteria |

The two Anthropic sources disagree about the official marketplace. The
`anthropics/claude-plugins-official` README still says "Third-party
partners can submit plugins for inclusion in the marketplace" through "the
plugin directory submission form". The documentation page above says that
marketplace takes no portal submissions. Follow the documentation page:
submit to the directory, and treat an official-marketplace listing as a
question for an Anthropic partner contact.

### What to submit

1. **MCP connector:** server URL `https://riskdesk.avidquant.com/mcp`,
   Streamable HTTP, no authentication. The connector checklist asks for
   test credentials. The server has no accounts, so state in the portal
   that no sign-in exists. Also state that every tool runs on a synthetic
   example without input. Public documentation: `plugins/risk-desk-hosted/README.md`
   in this repository and the hosted support page.
2. **Plugin bundle:** this repository on GitHub, plugin folder
   `plugins/risk-desk-hosted`, from the branch that the listing follows.
   Its `.claude-plugin/plugin.json` carries the name, version,
   description, author, licence, homepage, repository, the listing icon
   and the documentation, privacy, terms and support URLs. Its `.mcp.json`
   declares the one `http` server at the URL above. Pair the bundle with
   the connector in the portal.

### Checked in this repository

- `claude plugin validate ./plugins/risk-desk-hosted --strict`: passed,
  with no directory findings, on 2026-11-04 (Claude Code 2.1.318).
- `claude plugin validate .` (the marketplace): passed on 2026-11-04.
- `plugins/risk-desk-hosted`: README of 706 words, `LICENSE` present, 31
  files, none over 256 KiB, no system files, no binary other than the two
  PNG icons.

### Anthropic checklist

- [x] Engine published to PyPI (4 November 2026).
- [x] 0.2 image deployed (4 November 2026).
- [ ] Repository public on GitHub at the commit being submitted.
- [ ] `claude plugin validate ./plugins/risk-desk-hosted --strict` clean.
- [ ] Connector submitted with the server URL, and the no-sign-in note.
- [ ] Plugin bundle submitted from `plugins/risk-desk-hosted` and paired.
- [ ] Portal **Validate** report has no Blocking finding.
- [ ] Each tool exercised through the MCP Inspector and as a custom
      connector in Claude, as the portal's Test and launch step asks.
- [ ] Final draft reviewed by the maintainer before submission.
