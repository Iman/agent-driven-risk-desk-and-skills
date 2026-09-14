# Disclaimer and terms of use

Last updated 2026-09-15.

This document applies to the entire repository, to the runtime under
`src/riskdesk`, to the CLI, to the MCP server, to the plugin skills, to
every file any of them writes, and to every response produced by an AI
agent that invokes them. Using, copying or running this software means you
accept what follows. If you do not accept it, do not use the software.

## 1. This is software, not advice

This project is research and engineering software. It computes numbers
from inputs you choose. Nothing it produces is investment advice, a
personal recommendation, an inducement, an invitation, an offer, or a
solicitation to buy, sell or hold any security, derivative, contract,
commodity, currency or digital asset.

No output is tailored to any person's financial situation, objectives,
knowledge, experience, tax position or risk tolerance, and no output should
be read as if it were. The software cannot know those things and does not
ask.

The software is general in nature. Its output is not suitable or
appropriate for you, in the regulatory sense of those words, because no
assessment of suitability or appropriateness has been performed or is
possible.

## 2. No regulated status, and no regulated activity is carried on

The author and copyright holder is not authorised or regulated by the
Financial Conduct Authority. He is not registered with the United States
Securities and Exchange Commission, is not an investment adviser, is not a
broker or dealer, is not a commodity trading advisor, is not registered in
any equivalent capacity in any other jurisdiction, and does not hold
himself out as being so.

Nothing offered here constitutes, and nothing here is intended to
constitute:

- investment advice or a personal recommendation, within the meaning of the
  FCA Handbook or Article 53 of the Financial Services and Markets Act 2000
  (Regulated Activities) Order 2001, or advice within the meaning of the
  US Investment Advisers Act of 1940
- an offer, inducement or invitation to engage in investment activity, or a
  financial promotion within the meaning of section 21 of the Financial
  Services and Markets Act 2000
- dealing, arranging, managing, safeguarding or administering investments
  for any person
- an offer to sell or a solicitation of an offer to buy any security

No fiduciary, advisory, agency or client relationship of any kind is
created by your use of this software, by your reading of its documentation,
by any correspondence about it, or by any commercial licence granted for
it.

## 3. Your responsibility

You are solely responsible for every decision you make and every order you
place. You are solely responsible for determining whether your use of this
software is lawful where you are, for obtaining your own professional
advice before acting, and for complying with the rules of any venue,
broker or regulator you deal with.

Where local law makes any part of this software unlawful to use, it is your
responsibility not to use it.

## 4. A risk measure is not a prediction, and a scenario is not a forecast

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

Exposure figures are arithmetic over values you supplied. They are correct
about your input and say nothing about whether the input is correct.

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
whether you may store it, redistribute it, or use it commercially. Reading
and honouring those terms is your responsibility, not the author's.

Market-data rights and methodology rights are separate from software
licences. This software distributes no ISDA SIMM material and claims no
rights to your market data.

## 6. No warranty

The software is provided "as is", without warranty of any kind, express or
implied, including but not limited to the warranties of merchantability,
fitness for a particular purpose, accuracy, and non-infringement. The
author does not warrant that the software is free of defects, that
calculations are correct, that it will run without interruption, or that
any output is suitable for any purpose.

Financial models embed assumptions. The assumptions in this software are
documented where practical, and they are still assumptions. They can be
wrong, and they can be wrong in ways that are not obvious from the output.

## 7. Limitation of liability

To the maximum extent permitted by law, the author shall not be liable for
any trading loss, lost profit, lost opportunity, loss of data, business
interruption, regulatory penalty, or any direct, indirect, incidental,
special, exemplary, punitive or consequential damages arising out of or in
connection with the software or its use, whether in contract, tort
including negligence, strict liability or otherwise, and whether or not the
author was advised of the possibility of such damages.

Nothing in this document excludes or limits liability for death or personal
injury caused by negligence, for fraud or fraudulent misrepresentation, or
for any other liability that cannot lawfully be excluded or limited.

## 8. Indemnity

To the extent permitted by law, you agree to indemnify and hold the author
harmless from any claim, demand, loss, liability, cost or expense,
including reasonable legal fees, arising from your use of the software,
from any output you distribute or act on, from any decision you or a third
party takes in connection with it, from your breach of these terms or of
the licence, from your breach of any data provider's terms, or from your
breach of any law or regulation.

## 9. No reliance

You must not rely on anything this software produces. Any decision you take
is yours alone, taken on your own judgement and on your own information,
and the copyright holder has no responsibility for it.

## 10. Automated and agent use

This software is designed to be invoked by AI agents. An agent's summary of
an output is not a substitute for the output, and neither is advice. Any
agent integration must preserve the substance of this disclaimer where
results are presented to a person, must report the degraded flag and the
sign convention before the numbers, and must not present a historical loss
measure as a valuation or a regression value as model validation.

Automated execution against a live account is outside the scope of this
project. If you build it, you own the consequences entirely. Nothing in
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
make him responsible for how you use the software.

## 12. Not a substitute for professional advice

Nothing here is legal, tax, accounting or financial advice. Consult a
qualified professional in your jurisdiction before acting on anything this
software produces.

## 13. Governing law

These terms are governed by the laws of England and Wales, and the courts
of England and Wales have exclusive jurisdiction, without prejudice to any
mandatory consumer protection rights available to you locally.

If any provision is held unenforceable, the remainder stays in force.
