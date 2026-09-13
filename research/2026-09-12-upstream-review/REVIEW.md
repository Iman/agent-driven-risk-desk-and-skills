# Risk Desk: upstream reuse review

Research date: 2026-09-12. Project name: Risk Desk. Proposed repository and plugin name: `risk-desk`.

## UNKNOWN

This is a dependency shortlist, not an integration certification. No upstream package was installed or tested in this review. Numerical accuracy, supported instrument coverage, deployment compatibility, and complete dependency-license compatibility remain unverified. No implementation or project license has been created.

The first GitHub API metadata request succeeded for all 16 repositories at approximately 22:46 UTC. A later request saved pinned revisions and release metadata for nine repositories, then reached the unauthenticated API rate limit. The remaining license files were retrieved as branch snapshots, with retrieval times and content hashes. A missing latest GitHub release is not evidence of no package release.

## VERIFIED

Stars below are exact observations from the GitHub API this session, not rounded search-engine counts. Last push is repository activity, not proof of maintenance quality. None of these repositories was marked archived. License descriptions come from the retrieved upstream texts. Capability descriptions are upstream documentation claims, not locally tested behavior.

| Upstream | Stars | Last push, UTC date | License text | Proposed role |
|---|---:|---|---|---|
| [CCXT](https://github.com/ccxt/ccxt) | 43,968 | 2026-09-12 | MIT | Optional crypto data adapter; no order placement in Risk Desk |
| [PyMC](https://github.com/pymc-devs/pymc) | 9,749 | 2026-09-10 | Apache-2.0, with bundled MIT notice and historical notices | Optional Bayesian model inference |
| [Evidently](https://github.com/evidentlyai/evidently) | 7,912 | 2026-09-11 | Apache-2.0 | Optional data/model monitoring |
| [QuantStats](https://github.com/ranaroussi/quantstats) | 7,628 | 2026-07-20 | Apache-2.0 | Return analytics and report cross-checks |
| [QuantLib](https://github.com/lballabio/QuantLib) | 7,609 | 2026-09-11 | Modified BSD-style text; preserve full notice | Pricing, curves, calendars, cash flows and sensitivities |
| [PyPortfolioOpt](https://github.com/PyPortfolio/PyPortfolioOpt) | 6,020 | 2026-07-07 | MIT | Alternative portfolio backend and numerical benchmark |
| [Riskfolio-Lib](https://github.com/dcajasn/Riskfolio-Lib) | 4,494 | 2026-08-18 | BSD-3-Clause | Optional advanced risk measures and risk budgeting |
| [FinancePy](https://github.com/domokane/FinancePy) | 3,146 | 2026-09-12 | GPL-3.0 | Pricing candidate conditional on distribution-license decision |
| [skfolio](https://github.com/skfolio/skfolio) | 2,387 | 2026-09-12 | BSD-3-Clause | Preferred portfolio risk, allocation and scenario backend |
| [ArviZ](https://github.com/arviz-devs/arviz) | 1,853 | 2026-09-09 | Apache-2.0 | Bayesian diagnostics and model comparison |
| [arch](https://github.com/bashtage/arch) | 1,566 | 2026-08-10 | Custom permissive text with source/binary notice and non-endorsement conditions | Volatility models, bootstrap and statistical benchmarks |
| [Cvxportfolio](https://github.com/cvxgrp/cvxportfolio) | 1,285 | 2026-04-27 | GPL-3.0 | Cost-aware portfolio simulation; conditional on license decision |
| [OpenGamma Strata](https://github.com/OpenGamma/Strata) | 962 | 2026-09-07 | Apache-2.0 plus NOTICE | Java alternative for derivatives pricing and market risk |
| [Open Source Risk Engine](https://github.com/OpenSourceRisk/Engine) | 786 | 2026-09-11 | Modified BSD-style text | Preferred exposure, collateral and XVA backend |
| [pyextremes](https://github.com/georgebv/pyextremes) | 279 | 2026-02-19 | MIT | Optional extreme-value tail analysis |
| [transitionMatrix](https://github.com/open-risk/transitionMatrix) | 88 | 2026-02-27 | Apache-2.0 | Credit-rating migration research candidate |

The canonical PyPortfolioOpt repository has moved to PyPortfolio/PyPortfolioOpt. The earlier owner URL redirects there. GitHub returned NOASSERTION for ORE, QuantLib, arch and PyMC; their actual license files are available and were inspected. Do not interpret this metadata label as absence of a license.

ORE's saved latest GitHub release is v1.8.16.0, published 2026-05-21. QuantLib's is v1.43, published 2026-07-14. These observations do not establish that those versions can be combined: use the QuantLib revision supported by the chosen ORE release. Saved default-branch revisions are research references, not selected production dependencies. See [evidence.json](evidence.json).

## ASSUMPTIONS

Use a small permissive core with the selected PolyForm Noncommercial 1.0.0 project license. Proposed initial backends are ORE/its supported QuantLib, skfolio and arch. Add ArviZ for Bayesian outputs. Keep Riskfolio-Lib, PyMC, pyextremes, QuantStats and data connectors optional when a required feature justifies them.

The shortlist favors suitability over stars: CCXT is popular but supplies connectivity; ORE has fewer stars but is directly relevant to XVA. The overlapping portfolio libraries should not all become mandatory dependencies. Test skfolio first, then add another only for a named missing capability or independent comparison.

## PLAN / ANSWER

### Coverage of the proposed skills

Each row is a proposed integration boundary. A documented capability still needs a pinned-version example and regression test before being advertised by a skill.

| Skill | Reuse first | Work Risk Desk may need |
|---|---|---|
| Market risk | skfolio, arch, ORE | Portfolio P&L conventions, confidence/horizon labels, full revaluation adapter |
| Portfolio risk | skfolio; optional Riskfolio-Lib | Position aggregation, currency conversion, concentration limits |
| Drawdown | skfolio; QuantStats cross-check | Equity-path construction, cash-flow handling, recovery-time and capital-floor reporting |
| Sensitivities | ORE/QuantLib; optional Strata | Common units, position scaling and aggregation; verify higher-order coverage individually |
| Volatility | arch; optional PyMC | Model specification and calibration; surface dynamics require separate coverage checks |
| Stress | ORE and skfolio | Versioned scenario catalogue, combined shocks, reverse-stress objectives |
| Exposure | ORE | Trade import, counterparty/netting mappings, lifecycle and collateral configuration |
| XVA | ORE | Market inputs, conventions, allocation and result translation; benchmark against old illustrative engine |
| Counterparty | ORE | Counterparty data, limits and due diligence; verify the chosen wrong-way-risk model |
| Collateral | ORE | Agreement import, disputes and operational rules; validate margin methods and rights |
| Liquidity | Evaluate Cvxportfolio cost models if license-compatible | Venue depth, participation assumptions, liquidation schedule and stress calibration |
| Funding | ORE for trade funding adjustments | Treasury cash-flow ladder, funding facilities, liquidity survival and rollover scenarios |
| Rates | ORE/QuantLib; optional Strata | Instrument and curve mappings; banking-book behavioral models are separate |
| Credit | ORE/QuantLib for credit instruments; transitionMatrix for migration | PD/LGD/EAD data and loan-book model; migration library is not a complete credit-loss engine |
| Crypto | CCXT for supported data interfaces | Venue-specific liquidation, funding, collateral and custody exposure rules |
| Event | skfolio/PyMC for statistical building blocks | Dated evidence, scenario definitions and empirical validation of existing research |
| Validation | arch, ArviZ; optional Evidently | Forecast/outcome ledger, VaR/ES-specific validation, pricing benchmarks and model comparison |
| Monitoring | Optional Evidently; existing desk monitoring patterns | Reconciliation, missing prices, limit breaches and operational state |

ORE documents exposure and valuation adjustments, including collateral, dynamic initial margin/MVA and KVA. Confirm exact formulas, limitations and available interfaces against the selected release's [user guide](https://opensourcerisk.org/content/uploads/2026/04/userguide.pdf). Its repository includes Python interfaces, examples and tests; this review did not run them. ORE already builds on QuantLib, so avoid a second independent pricing implementation for the same products.

No complete suitable package was established here for treasury liquidity survival, broker-specific liquidation rules, counterparty governance or the common Risk Desk workflow. This is a search limitation, not proof that no implementation exists. Before writing a new mathematical component, search for that precise gap, document rejected alternatives, then implement against an independent benchmark. Integration code will still be needed for input contracts, provenance, units, CLI/MCP, skills and reporting.

Keep real-world loss forecasting distinct from risk-neutral valuation. Also distinguish positive counterparty exposure from signed mark-to-market quantiles, monetary losses from return quantiles, and compounded from uncompounded drawdown. An adapter must not silently equate similarly named fields from different libraries.

### License and credit requirements

The files under [upstream-notices](upstream-notices/) are preserved review evidence. Their hashes are in [notice-hashes.json](notice-hashes.json). They do not mean that every candidate is installed, selected or cleared for redistribution.

For the eventual distribution:

1. Pin the selected package versions and artifact hashes. Check the source release, wheel/container and dependency tree, including bundled native code and optional solvers.
2. Retain exact upstream copyright notices, license conditions, disclaimers and applicable NOTICE text. Do not replace upstream authors with the Risk Desk author.
3. Create a third-party notice register identifying each selected dependency, version, source, license, component used and modifications. Include it and the license texts in source archives, packages, containers and plugin distributions where required.
4. Mark modified upstream files, preserve their headers and record patch provenance. Prefer public APIs and upstream patches over copied implementations.
5. Add a visible acknowledgements page and cite upstream projects and requested publications in research reports. Attribution gives credit; it does not imply endorsement.
6. Run a dependency-license/SBOM check against the resolved build, and check that built artifacts actually contain the required notices. These checks are proposed, not implemented.
7. Review data, documentation, logos and methodology rights separately from software licenses. A connector's license does not grant rights to redistribute exchange data.

MIT requires preservation of the copyright and permission notice. BSD-style texts add their stated source/binary conditions and non-endorsement clauses. Apache-2.0 requires the license, applicable retained notices, notices of modified files, and relevant upstream NOTICE content. See the [Apache license, section 4](https://www.apache.org/licenses/LICENSE-2.0).

QuantLib's full notice includes third-party acknowledgements. Strata's NOTICE includes CERN and Martin Matula material. PyMC's license includes MIT-licensed AePPL material. Preserve these details instead of relying only on GitHub's top-level license badge.

FinancePy and Cvxportfolio are GPL candidates. If their integration forms a distributed combined work, an Apache-only or noncommercial-only license for that combined work is not a substitute for GPL compliance. A subprocess boundary alone does not settle this question. See [GPLv3](https://www.gnu.org/licenses/gpl-3.0.html) and the [GNU FAQ on combined works](https://www.gnu.org/licenses/gpl-faq.html#MereAggregation). Keep these candidates outside the default dependency plan until distribution terms and integration boundaries are decided.

ISDA separately licenses SIMM. An open-source implementation does not establish permission to use or redistribute the methodology and calibration material. [ISDA's SIMM page](https://www.isda.org/isda-solutions-infohub/isda-simm/) links its licensing process. The [OpenSIMM repository](https://github.com/OpenGamma/OpenSIMM) identifies itself as an implementation of the original proposed model; it is not evidence of current SIMM coverage. Use cleared materials or an explicitly labeled alternative margin model.

Decision recorded after the initial review: the project is Risk Desk (`risk-desk`), the measure is VaR, and the user selected PolyForm Noncommercial 1.0.0, matching Option Desk. Risk Desk should be described as source-available: a noncommercial restriction does not meet the [Open Source Definition, section 6](https://opensource.org/osd). This decision does not change upstream licenses. Reuse of existing project code must also respect its ownership and license provenance. FinancePy and Cvxportfolio remain outside the proposed default dependency set.

### Acceptance criteria before a backend becomes a skill capability

For each backend, run an upstream example on synthetic or permitted inputs; verify a published or hand-calculated benchmark; validate units, sign, dates and currency; compare with the existing model where relevant; exercise missing-input and unsupported-instrument paths. Save observed test counts and output. Check actual packaging notices and license compatibility for the selected dependency tree. Approve the concrete integration design before writing implementation code, as required by the project instructions.
