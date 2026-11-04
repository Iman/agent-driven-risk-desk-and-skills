---
name: risk-data-import
description: Turn a CSV, spreadsheet or JSON file the user attaches into a Risk Desk request, repairing clear format and unit errors and reporting each repair, then pass it to the hosted Risk Desk MCP. Use when a user attaches data and asks for a risk figure, asks how to format it, or a tool refused the input.
---

# Risk data import, hosted

Use the connected hosted Risk Desk MCP. Do not run a local command. Call
`risk_desk_status` first to check availability, input limits and
reporting conventions. Build the request as JSON in the conversation from
the attached file, and pass it in the tool's `request` argument. Discover
the tool's input schema for every field name and type; do not guess them.

## Safety boundary

- Use only the file the user supplied. Never fetch prices, rates, FX or
  other market data, and never fill a gap from memory.
- Never invent a market value, price, P&L observation, date, currency,
  NAV, `source` or `data_mode`. Ask for a missing value by row and column.
- `data_mode` is the user's declaration (`synthetic` or `user-licensed`).
  Ask for it; do not infer it. It is not a rights certificate and the
  service does not check it.
- Before sending anything, establish that the user is permitted to share
  the data with a hosted service, and point them to the privacy policy at
  https://riskdesk.avidquant.com/privacy. Existing permission in the
  conversation is sufficient.
- Never send the synthetic demo in place of a file that failed to map.

## Which tool

| the file holds | tool |
|---|---|
| positions with market values | `risk_exposure` |
| positions plus scenario shocks | `risk_stress` |
| a P&L series | `risk_tail`, `risk_tail_models` |
| VaR forecasts beside realised P&L | `risk_backtest` |
| dated price levels per asset | `risk_stress_replay` |
| asset returns, one row per period | `risk_covariance` |
| options and futures with strikes and vols | `risk_derivatives_greeks` |
| simulated exposure by date | `risk_exposure_profile` |
| derivative trades in one netting set | `risk_saccr` |
| obligors with exposure, PD and LGD | `risk_credit_asrf` |

If the file fits none, say so and stop. If it exceeds the limits that
`risk_desk_status` states, say so; do not drop or sample rows to fit.

## Repairs you may make, and must report

Repair only where a value has one reading. Report each as row, column,
value found, value written and why.

- Thousands separators and currency symbols, when the currency matches.
- Accounting negatives: `(4,200)` to `-4200`.
- Percent text to a fraction: `-10%` to `-0.10`. A bare `-10` in a shock
  column is ambiguous; ask.
- Dates to `YYYY-MM-DD` only when day and month cannot be swapped.
- Unambiguous short names to the schema's literals, such as `Call` to
  `call`.
- Trailing blank rows and a repeated header, with the count dropped.
- A P&L column with losses positive, negated only when the user confirms.

Never repair a blank market value, price, P&L, PD, LGD or exposure (no
zero, no carry forward), values in another currency, an option premium
used as a linear market value, daily P&L offered for a longer horizon, or
duplicate ids. Ask instead.

## Workflow

1. Pick the tool, map columns to fields and list every required field
   with no column.
2. Ask once for each missing value and for `as_of`, `currency`, `source`
   and `data_mode` if the file does not state them.
3. Apply only permitted repairs, list them, and send the request.
4. If the tool refuses the input, quote its message, map it to the row
   and column, and ask for the corrected value. Do not loosen the request.
5. Report as that tool's skill says: degraded status and reason first,
   then the figures with currency, horizon and sign convention.

Reading files on the user's machine is not available here: the service
sees only the request you send. Counterparty XVA is also not available
here; it needs a local ORE project and the local `risk-desk` plugin.
