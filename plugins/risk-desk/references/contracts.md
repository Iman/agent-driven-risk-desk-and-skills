# Risk Desk input contracts

All amounts are in the stated base currency. `as_of` is an ISO date. `source` must identify the input origin. `data_mode` is `synthetic` or `user-licensed` (the ORE tools, `risk_xva` and `risk_exposure_profile`, also take `upstream-example` for ORE's own example inputs). It is the caller's declaration, not a rights certificate. Unknown fields and nonfinite numbers are rejected.

## TailRequest

Required fields: `as_of`, `currency` (three uppercase letters), `source`, `data_mode`, `pnl` (at least two monetary profit/loss samples), `confidence` (strictly between zero and one), `horizon_days` (positive integer), `portfolio_value` (positive).
Each sample spans the entire stated horizon. Positive P&L is profit. No dates are inferred for samples, no scaling is performed, and missing observations are not dropped.
`risk_tail_models` takes the same contract. For it, the P&L must be in time order, oldest first, because the GARCH models depend on order.

## PortfolioRequest

Required provenance fields as above, `nav` (positive), and `positions`. Each position requires unique `id`, `asset`, signed `market_value`, and `instrument_type: linear`. Aggregate same-asset positions by their provided identifiers. Currency conversion must be completed before submission.

## StressRequest

PortfolioRequest plus `scenarios`. Each scenario has a unique `name` and a `shocks` mapping naming exactly every asset. Values are simple returns, such as -0.10 for a 10% fall. Returns below -1 are rejected.

Each model below carries the provenance fields `as_of`, `currency`, `source` and `data_mode` unless it says otherwise, and a model built on PortfolioRequest also carries `nav` and `positions` (linear, unique ids). "List[n..m]" gives the accepted length. Rules after a table are cross-field checks the tool refuses with a plain message.

## BacktestRequest (risk_backtest)

| field | type and constraint | meaning |
| --- | --- | --- |
| `pnl` | list of numbers, 2..10,000 | realised horizon P&L, oldest first; positive is profit |
| `var` | list of numbers, 2..10,000 | VaR forecast for each row, made before its P&L; positive is a loss |
| `expected_shortfall` | list of numbers, 2..10,000, optional | ES forecast for each row |
| `confidence` | number, 0 < c < 1 | VaR coverage, such as 0.99 |
| `horizon_days` | integer, 1..3650 | horizon every row spans |
| `es_null` | `normal` or `student-t`, optional | location-scale null for the simulated Z2 p-value |
| `es_null_dof` | number, 1 < v <= 1000, optional | degrees of freedom for `student-t` |
| `seed` | integer >= 0, default 0 | seed of the Z2 simulation |

Rules:

- `var`, `pnl` and `expected_shortfall` have one length.
- `expected_shortfall` and `es_null` come together.
- `es_null_dof` is given for, and only for, `student-t`.
- Each ES is positive and above its VaR.

## DerivativesBookRequest (risk_derivatives_greeks)

Kept separate from PortfolioRequest on purpose: an option position is a quantity of contracts, not a market value.

| field | type and constraint | meaning |
| --- | --- | --- |
| `underlyings` | mapping name to Underlying, at least one | prices the book is valued at |
| `underlyings.*.price` | number > 0 | spot price, or futures price |
| `underlyings.*.price_type` | `spot` or `future` | Black-Scholes-Merton for spot, Black-76 for a future |
| `positions` | list of BookPosition, 1..10,000 | the book |
| `positions.*.id` | text, unique | position identifier |
| `positions.*.underlying` | text | a key of `underlyings` |
| `positions.*.instrument_type` | `linear` or `option` | |
| `positions.*.quantity` | number, signed | units or contracts; negative is short |
| `positions.*.multiplier` | number > 0 | units of underlying per contract |
| `positions.*.kind` | `call` or `put` | options only |
| `positions.*.strike` | number > 0 | options only |
| `positions.*.expiry` or `year_fraction` | date, or number > 0 | exactly one, options only; a date is converted ACT/365 from `as_of` |
| `positions.*.implied_vol` | number > 0, decimal | one flat vol per option, 0.25 for 25% |
| `positions.*.rate` | number | continuously compounded rate |
| `positions.*.carry_yield` | number | continuous carry or dividend yield; required on spot (0 if none), refused on a future |

Rules:

- A linear position carries no option terms.
- An option needs `kind`, `strike`, `implied_vol` and `rate`.
- Every `underlying` is known.
- An option must expire after `as_of`.

## ScenarioGridRequest (risk_derivatives_grid)

DerivativesBookRequest plus `spot_shocks` (list of 1..101 simple returns, each above -1) and `vol_shocks` (list of 1..101 additive changes to every implied vol, 0.05 for five points).

## HistoricalPnlRequest (risk_derivatives_historical)

DerivativesBookRequest plus:

| field | type and constraint | meaning |
| --- | --- | --- |
| `scenarios` | list, 2..100,000 | one historical move per row |
| `scenarios.*.spot_returns` | mapping underlying to number | simple return of every book underlying, above -1 |
| `scenarios.*.vol_changes` | mapping underlying to number, optional | additive vol change of every book underlying |
| `horizon_days` | integer, 1..3650 | horizon each move spans |
| `time_mode` | `fixed` or `decay` | `decay` lets the horizon pass (theta included) |
| `confidence` | number, 0 < c < 1 | VaR and ES level |
| `portfolio_value` | number > 0 | value the tail is scaled by |

## CovarianceRequest (risk_covariance)

| field | type and constraint | meaning |
| --- | --- | --- |
| `assets` | list of unique text, 1..1000 | column names of `returns` |
| `returns` | rows of numbers, 2..100,000 rows | one row per period, one value per asset, each at least -1 |
| `horizon_days` | integer, 1..3650 | period each row spans; nothing is rescaled |
| `method` | `sample`, `ewma` or `ledoit_wolf` | estimator |
| `decay` | number, 0 < d < 1 | EWMA decay; required for `ewma`, refused otherwise |

## ParametricRequest (risk_var_attribution)

PortfolioRequest plus `assets` (unique text, 1..1000), `covariance` (square, symmetric, positive semidefinite, one row and column per asset, of simple returns over the horizon), `confidence` (0.5 < c < 1, so VaR is a loss) and `horizon_days` (1..3650).

## HistoricalRequest (risk_es_attribution)

PortfolioRequest plus the `assets`, `returns` and `horizon_days` of CovarianceRequest, and `confidence` (0 < c < 1).

## FactorRequest (risk_factor_exposure)

PortfolioRequest plus the `assets`, `returns` and `horizon_days` of CovarianceRequest, `factors` (unique text, 1..100) and `factor_returns` (one row per return row, one value per factor). There must be more rows than factors plus one.

## LimitRequest (risk_limits)

| field | type and constraint | meaning |
| --- | --- | --- |
| `limits` | list of Limit, 1..1000, unique names | the caller's limit set |
| `limits.*.metric` | `gross_exposure`, `net_exposure`, `gross_leverage`, `net_leverage`, `gross_share`, `var`, `expected_shortfall` or `stress_loss` | what is limited |
| `limits.*.asset` | text | required for `gross_share`, refused otherwise |
| `limits.*.scenario` | text | required for `stress_loss`, refused otherwise |
| `limits.*.direction` | `max` or `min` | which side is a breach |
| `limits.*.limit` | number | hard limit |
| `limits.*.warning` | number, optional | warning level, on the safe side of `limit` |
| `results` | mapping of `exposure`, `tail`, `stress` to a result envelope | Risk Desk results to grade, unchanged; finite numbers only |

A result in another currency is not evaluated. A result dated differently is evaluated and reported in `degraded_reason`.

## WhatIfRequest (risk_what_if)

PortfolioRequest plus:

| field | type and constraint | meaning |
| --- | --- | --- |
| `trades` | list, 1..10,000 | proposed changes |
| `trades.*.asset` | text | asset traded |
| `trades.*.market_value_change` | number, signed | change in linear market value at as-of prices |
| `trades.*.position_id` | text, optional | position changed; required when the asset is held in several |
| `scenarios` | list of Scenario, optional | stress scenarios, as StressRequest |
| `asset_returns` | mapping asset to list of numbers, optional | horizon returns for the tail, one series per asset held before or after |
| `confidence`, `horizon_days` | as TailRequest | given with `asset_returns`, or not at all |
| `limits` | list of Limit, optional | graded on the book after the trades |

## LiquidityRequest (risk_liquidity)

PortfolioRequest plus:

| field | type and constraint | meaning |
| --- | --- | --- |
| `participation_rate` | number, 0 < r <= 1 | share of average daily traded value sold per day |
| `spread_multiplier` | number >= 0 | multiple of spread volatility added to the mean spread |
| `liquidity` | mapping asset to AssetLiquidity, exactly the book's assets | |
| `liquidity.*.average_daily_value` | number > 0 | average daily traded value, in the stated currency |
| `liquidity.*.mean_relative_spread` | number >= 0 | mean bid-ask spread as a fraction of mid |
| `liquidity.*.spread_volatility` | number >= 0 | standard deviation of that relative spread |
| `pnl`, `confidence`, `horizon_days` | as TailRequest, optional | given together for liquidity-adjusted VaR |

## ReplayRequest (risk_stress_replay)

PortfolioRequest plus `scenario_name` (text), `prices` (mapping series name to a mapping of ISO date to positive price level), `start` and `end` (dates, start before end, both present in every series used), `measure` (`end_over_start`, the default, or `worst_peak_to_trough`) and `proxies` (mapping a book asset to the series that stands in for it). Prices are the caller's. Risk Desk ships none.

## ReverseStressRequest (risk_reverse_stress)

PortfolioRequest plus `target_loss` (number > 0, in the stated currency), `horizon_days` (1..3650), `assets` (each book asset exactly once), `covariance` (square, ordered like `assets`, horizon returns) and `floors` (mapping asset to the lowest return allowed, at least -1, and every asset is floored at -1 regardless).

## ScaleRequest (risk_scenario_scale)

PortfolioRequest plus `scenario` (one Scenario, as StressRequest) and `target_loss` (number > 0): the multiple of the scenario that loses exactly that amount.

## Scenario library (risk_scenario_library)

No input. Returns dated windows with their published sources, and no prices.

## SaccrRequest (risk_saccr)

| field | type and constraint | meaning |
| --- | --- | --- |
| `netting_set` | text | netting set name |
| `trades` | list of SaccrTrade, 1..100,000, unique ids | |
| `trades.*.asset_class` | `interest_rate`, `fx`, `credit`, `equity`, `commodity` | |
| `trades.*.notional` | number > 0 | trade notional for interest rate and credit; foreign leg in the stated currency for fx (CRE52.35); price times units for equity and commodity (CRE52.36) |
| `trades.*.market_value` | number, signed | value to the bank, part of V |
| `trades.*.maturity` | number, 0 < M <= 100 | years (CRE52.31) |
| `trades.*.position` | `long` or `short` | long is bought, for an option (CRE52.39 to 52.40) |
| `trades.*.hedging_set` | text | currency for interest rate, a pair such as `EUR/USD` for fx, `energy`, `metals`, `agricultural` or `other` for commodity |
| `trades.*.reference` | text | credit or equity entity or index, or commodity type |
| `trades.*.start`, `end` | numbers in years | S and E; required for interest rate and credit, end after start |
| `trades.*.rating` | `AAA` to `CCC`, or `IG`, `SG` with `index` | credit only |
| `trades.*.index` | boolean | credit or equity index |
| `trades.*.electricity` | boolean | commodity electricity, energy hedging set only |
| `trades.*.option` | `call` or `put`, optional | with `underlying_price`, `strike` and `exercise` (years, not after maturity) |
| `trades.*.shift` | number >= 0 | lambda for interest rate options only |
| `collateral` | number, default 0 | haircut value of net collateral held, C |
| `margined` | boolean, default false | |
| `threshold`, `minimum_transfer_amount`, `nica`, `remargining_period_business_days`, `mpor_business_days` | numbers; the day counts are integers 1..250 | margin terms; all required when margined, refused otherwise; MPOR at least the CRE52.50 floor |

FX and equity add-ons are partially verified: constants checked against CRE52.72, with no published worked example.

## ExposureProfileRequest (risk_exposure_profile)

`rows`: 2..100,000 rows of one ORE netting-set exposure report, ORE's column names: `NettingSet`, `Date`, `Time` (years, 0..200, strictly increasing, first row 0), `EPE`, `ENE`, `PFE`, `ExpectedCollateral`, `BaselEE`, `BaselEEE`, `TimeWeightedBaselEPE`, `TimeWeightedBaselEEPE`. `BaselEE` and `PFE` are required and non-negative on every row. All rows share one netting set.

## AsrfRequest (risk_credit_asrf) and CopulaRequest (risk_credit_copula)

| field | type and constraint | meaning |
| --- | --- | --- |
| `confidence` | number, 0 < c < 1 | credit VaR level |
| `horizon_days` | integer, 1..3650 | horizon the PDs apply to |
| `obligors` | list, unique ids; up to 1,000,000 for ASRF, 100,000 for the copula | |
| `obligors.*.exposure` | number > 0 | exposure at default, stated currency |
| `obligors.*.pd` | number, 0 < p < 1 | default probability over the horizon |
| `obligors.*.lgd` | number, 0..1 | loss given default |
| `obligors.*.correlation` | number, 0 < r < 1 | ASRF asset correlation |
| `obligors.*.factor_loading` | number, -1 < b < 1 | copula loading on the one factor |
| `scenarios` | integer, 1000..1,000,000 | copula only; scenarios times obligors is capped |
| `seed` | integer >= 0 | copula only |

## FRTB requests

| model | fields |
| --- | --- |
| ImccRequest (risk_frtb_imcc) | `base_horizon_days` (must be 10); `portfolio` and `risk_classes` (`interest_rate`, `equity`, `fx`, `commodity`, `credit_spread`), each an EsSet of `reduced_stressed`, `full_current` and `reduced_current`: five non-negative 10-day ES values, ES_T(P, j) for j = 1 to 5 (MAR33.4) |
| ImaCapitalRequest (risk_frtb_ima_capital) | non-negative `imcc_latest`, `imcc_average_60d`, `ses_latest`, `ses_average_60d`, `drc_latest`, `drc_average_12w`, `qualitative_addon`, `sa_green_amber`, `sa_out_of_scope`, `sa_all_desks`; `bankwide_backtesting_exceptions` (integer 0..250); `desks` (unique `desk`, `pla_zone` `green` or `amber`, non-negative `sa`) |
| PlaRequest (risk_frtb_pla) | `desk`; `rtpl` and `hpl`, exactly 250 daily values each, oldest first |
| frtb BacktestRequest (risk_frtb_backtest) | `level` (`desk` or `bank`); `apl`, `hpl`, `var_99` and, for a desk only, `var_975`: exactly 250 values each, null allowed and counted as an exception; VaR non-negative |
| FxSbmRequest (risk_frtb_sbm_fx) | `currency` is the reporting currency; `apply_specified_pair_reduction` (boolean, no default: the bank's MAR21.88 election); `delta` (each `currency`, `sensitivity`) and `vega` (each `currency`, `option_maturity_years` of 0.5, 1, 3, 5 or 10, `sensitivity`), at least one entry in all, none to the reporting currency |

## ORE project

A trusted local directory contains an ORE XML config and all referenced input files. `inputPath` and file references must resolve inside that directory. `simulation` and `xva` analytics must be active. The output directory must be new and outside the input directory. Symlinks are refused. The adapter forces `continueOnError=false` and records input hashes.

This is a local integration, not a security sandbox for hostile XML. Review unfamiliar projects before running them. ORE's report fields and requested flags are retained. Null values indicate unavailable report fields. Do not infer enabled calculations from zeros in disabled columns.
