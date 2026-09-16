---
description: Run a trusted local ORE project for counterparty exposure and XVA, refusing rather than quoting when it errors
argument-hint: PROJECT_DIR CONFIG_PATH OUTPUT_DIR
arguments: [project, config, output]
---

Run the ORE project at $project.

1. Confirm before running: $project is a directory the user trusts and has
   inspected, $config resolves inside it, and $output does not exist yet
   and is outside $project. The adapter enforces all three and refuses
   otherwise, but a caller who learns this from an error has already
   waited for it.
2. `riskdesk xva --project $project --config $config --output $output
   --data-mode user-licensed`. Use `--data-mode synthetic` when the inputs
   are synthetic. The value records the caller's declaration about their
   rights to the data; it is not a rights certificate and nothing checks
   it.
3. Read the error level first. The adapter refuses to return a summary
   when ORE reports any error, so a result in your hands means no error
   was reported. If the command failed, say so and quote nothing. Do not
   reach into the output directory for a partial report.
4. Report the currency, the as-of date and the requested adjustment flags
   before any figure. A zero in a column whose adjustment was not
   requested is a disabled calculation, not a result.
5. Netting-set rows and trade rows overlap. Never add them together, and
   say which level each figure comes from.
6. A null is an unavailable value, not a zero.
7. This is risk-neutral valuation under the model and calibration that
   project specifies. It is not a real-world loss forecast, and it is not
   the same kind of number as the historical VaR from `risk-tail`. Do not
   put them in one table without saying so.
8. A clean run establishes that the adapter and the configuration are
   consistent. It does not establish calibration quality, wrong-way-risk
   treatment, or regulatory approval.
9. If the command reports that the ORE backend is missing, the optional
   extra is not installed in this environment. Say that rather than
   describing the risk as zero.
