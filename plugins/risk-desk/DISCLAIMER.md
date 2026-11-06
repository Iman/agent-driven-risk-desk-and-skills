# Disclaimer and terms of use

Last updated 2026-11-06.

This document applies to the entire repository, to the runtime under
`src/riskdesk`, to the CLI, to the MCP server, to the plugin skills, to
every file any of them writes, and to every response produced by an AI
agent that invokes them. Using, copying or running this software means you
accept what follows. If you do not accept it, do not use the software.

The separate hosted service has its own [terms](https://riskdesk.avidquant.com/terms)
and [privacy notice](https://riskdesk.avidquant.com/privacy). Those terms govern use of
that service; this document applies to the software here.

## 1. Research purpose and decisions

This project provides software for research, education and evaluation of
calculations from selected inputs. It does not assess whether an investment,
strategy, position size or level of risk is suitable or appropriate for you.

A calculation, ranking, comparison or illustration must not be treated as a
personal recommendation, an instruction to trade or an assurance that an
investment is safe. Obtain independent professional advice where needed.

## 2. Regulatory boundaries

Access to this software is not regulatory approval of a model, result,
investment or use. It does not grant you any authorisation or registration.
Research labels, disclaimers and a software licence do not determine whether
a particular activity is regulated. Applicable duties depend on the actual
service, communications, operator, users and jurisdictions.

The project is not offered as an advisory, brokerage or execution service.
Do not present its outputs as suitable for a particular person's circumstances
or as satisfying FCA, SEC, CFTC or other regulatory requirements. Nothing in
this document removes duties imposed by applicable law.

## 3. Your responsibility

You remain responsible for selecting inputs, checking assumptions and deciding
whether and how to use results, subject to any duties the law places on the
software provider. Check the rules applicable to your use and obtain qualified
professional advice where needed. Do not use the software unlawfully.

## 4. A risk measure is not a prediction, and a scenario is not a forecast

Algorithms, software and third-party components can contain defects. Inputs
can be incomplete, inaccurate, stale or unsuitable for a model. Results depend
on assumptions, calibration, conventions and limitations. Reproducibility and
successful tests do not establish fitness for a purpose or regulatory approval.
A risk estimate is not a maximum possible loss.

Historical VaR and Expected Shortfall are descriptions of a sample you
supplied. They are not forecasts, they are not bounds, and they do not
become more reliable because the sample is large. The small-sample warning
this software emits is a reporting threshold, not a confidence interval and
not a validation of anything.

A stress scenario is a set of shocks you specified. This software attaches
no probability to any scenario and no probability should be inferred from
one. Linear revaluation assumes exposure is linear in the shocked asset,
which for real books is an approximation that fails exactly when it matters
most.

Exposure figures are arithmetic over values you supplied. They can contain
calculation errors and do not establish whether the input is correct.

Risk-neutral exposure and XVA from ORE are valuation-model output under
that model's calibration and conventions. They are not real-world loss
forecasts, and a run that reports no error is not evidence that the model
is calibrated, appropriate or approved. A numerical result that reproduces
is a regression result, not model validation.

Any figure, chart or report this software writes is hypothetical. No
representation is made that any account will or is likely to achieve
profits or losses resembling anything shown.

## 5. Data comes from you, and from third parties

This software fetches no market data. It reads the files you give it and
the ORE project you point it at. `data_mode` records what you declared
about your rights to those inputs; it is a declaration, not a rights
certificate and not a check.

A licence to this software conveys no rights whatsoever to any data. Each
data provider's terms govern what you may do with what you hold, including
whether you may store it, redistribute it, or use it commercially.
You must comply with those terms. This does not remove the provider's own
applicable data-protection or security duties.

Market-data rights and methodology rights are separate from software
licences. This software distributes no ISDA SIMM material and claims no
rights to your market data.

You retain whatever rights you hold in supplied inputs. Before using a hosted
service or remote client, confirm permission for upload, processing, temporary
storage where used and output delivery through that client. Grant only the
permission needed for that processing. A confirmation does not override a
provider agreement or create rights you do not hold. Software access grants no
market-data, exchange, methodology, display or redistribution rights; derived
outputs can remain restricted. Do not send credentials, personal account
identifiers or confidential data you are not permitted to disclose.

## 6. Warranty limits

To the extent permitted by applicable law, the software and its outputs are
provided as is and as available, without warranties of accuracy, completeness,
availability, fitness for a particular purpose or achievement of any financial
result. No model or result is guaranteed to prevent a loss, identify every risk
or comply with a particular regulatory reporting regime. Mandatory rights and
any licence already granted remain unaffected.

## 7. Liability and mandatory rights

For business users, and only to the extent permitted by applicable law, the
provider excludes liability for trading losses, lost profits, lost opportunities
and indirect or consequential loss arising from use of the software or reliance
on its outputs. This business exclusion does not apply to consumers.

Nothing excludes or limits liability for fraud, fraudulent misrepresentation,
death or personal injury caused by negligence, or any other liability that
cannot lawfully be excluded or limited. Nothing waives mandatory consumer or
data-protection rights. These terms do not prevent complaints to a competent
regulator or court.

## 8. Software ownership and licences

Rights in original software remain with its rights holders. Third-party
software, algorithms, methodologies and data retain their respective rights
and licence terms. Access or input processing does not transfer those rights.
Inclusion of a component is not a guarantee of its accuracy or fitness.

Nothing here changes a licence already granted or permits removal of required
notices. See the repository's `LICENSE`, `LICENSES.md` and applicable
upstream notices.

## 9. Independent verification

Independently verify material inputs and results before relying on them in
financial, valuation, risk, accounting or regulatory processes. Check source,
timestamp, currency, horizon, assumptions and warnings. A modelled price is
not an executable quote. Historical and simulated performance do not guarantee
future performance.

## 10. Automated and agent use

This software is designed to be invoked by AI agents. An agent's summary of
an output is not a substitute for the output, and neither is advice. Any
agent integration must preserve the substance of this disclaimer where
results are presented to a person, must report the degraded flag and the
sign convention before the numbers, and must not present a historical loss
measure as a valuation or a regression value as model validation.

Automated execution against a live account is outside the scope of this
project. If you build it, you must assess its separate legal and operational requirements. Nothing in
this repository places, routes or executes an order, opens a broker
connection, or is a path to one.

## 11. Where you may not use it

You are responsible for determining whether use of this software is lawful
where you are, and for complying with all applicable law, including
sanctions, export control, market abuse and financial promotion rules.

Do not use it where doing so would require an authorisation you do not
hold, and do not present its output to another person in a way that would
constitute advice, a personal recommendation or a financial promotion
unless you are authorised to make one.

Commercial use of any kind requires a separate written agreement; the
source-available licence in `LICENSE` is PolyForm Noncommercial 1.0.0.
Obtaining such an agreement does not make the copyright holder your
adviser, does not transfer any regulatory permission to you, and does not
remove either party's applicable legal duties.

## 12. Not a substitute for professional advice

Nothing here is legal, tax, accounting or financial advice. Consult a
qualified professional in your jurisdiction before acting on anything this
software produces.

## 13. Governing law

These terms are governed by the laws of England and Wales, and the courts
of England and Wales have exclusive jurisdiction, without prejudice to any
mandatory consumer protection rights available to you locally.

If any provision is held unenforceable, the remainder stays in force.
