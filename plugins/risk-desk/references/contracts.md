# Risk Desk input contracts

All amounts are in the stated base currency. `as_of` is an ISO date. `source` must identify the input origin. `data_mode` is `synthetic` or `user-licensed`; it is the caller's declaration, not a rights certificate. Unknown fields and nonfinite numbers are rejected.

## TailRequest

Required fields: `as_of`, `currency` (three uppercase letters), `source`, `data_mode`, `pnl` (at least two monetary profit/loss samples), `confidence` (strictly between zero and one), `horizon_days` (positive integer), `portfolio_value` (positive).
Each sample spans the entire stated horizon. Positive P&L is profit. No dates are inferred for samples, no scaling is performed, and missing observations are not dropped.

## PortfolioRequest

Required provenance fields as above, `nav` (positive), and `positions`. Each position requires unique `id`, `asset`, signed `market_value`, and `instrument_type: linear`. Aggregate same-asset positions by their provided identifiers. Currency conversion must be completed before submission.

## StressRequest

PortfolioRequest plus `scenarios`. Each scenario has a unique `name` and a `shocks` mapping naming exactly every asset. Values are simple returns, such as -0.10 for a 10% fall. Returns below -1 are rejected.

## ORE project

A trusted local directory contains an ORE XML config and all referenced input files. `inputPath` and file references must resolve inside that directory. `simulation` and `xva` analytics must be active. The output directory must be new and outside the input directory. Symlinks are refused. The adapter forces `continueOnError=false` and records input hashes.

This is a local integration, not a security sandbox for hostile XML. Review unfamiliar projects before running them. ORE's report fields and requested flags are retained. Null values indicate unavailable report fields. Do not infer enabled calculations from zeros in disabled columns.
