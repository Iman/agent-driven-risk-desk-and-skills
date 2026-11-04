# Model inventory

Risk Desk v0.2, reviewed at commit c9e649e of feat/v0.2 (worktree feat/governance) on 4 November 2026.
Line references are to that commit, except that src/riskdesk/analytics.py (an overflow fix) and
src/riskdesk/derivatives.py (removal of the local Black-76 rho correction) changed afterwards on feat/v0.2.
Their hashes in [research/math-review/manifest.json](../../research/math-review/manifest.json) were
re-recorded after those changes, and the numerical review was rerun with 0 failures.

Status vocabulary:

- **verified**: the arithmetic is checked against an independent reference (a hand calculation, a closed form,
  brute force, numerical integration or a published figure), in the unit tests, the independent review
  under research/math-review, or both. Nothing material is UNPROVEN.
- **partially verified**: as above for part of the model. What is UNPROVEN is named.
- **not validated**: no independent check of the model's numbers exists in this repository.

Verified means the code computes the stated formula. It does not mean the model is fit for a given portfolio,
calibrated, or approved by a supervisor. The engineers transcribed regulatory constants and published tables
from bis.org (often from images). This review re-read only CRE99 Table 1. Every other transcription is
UNPROVEN by this review and is listed in the cards and in [ASSUMPTIONS.md](ASSUMPTIONS.md) Part B.

Assumptions per model are in [ASSUMPTIONS.md](ASSUMPTIONS.md): Part A rows carry the model id, Part B ids
(I01 to I25) are cited below.

## Summary

| Id | Model | Module and function | Method family | Status |
|---|---|---|---|---|
| M01 | Historical VaR and ES | `src/riskdesk/analytics.py` `tail_risk` (26-54) | historical simulation, empirical quantile | verified |
| M02 | Linear exposure and concentration | `src/riskdesk/analytics.py` `portfolio_exposure` (57-75) | aggregation | verified |
| M03 | Linear stress revaluation | `src/riskdesk/analytics.py` `stress_test` (78-92) | scenario revaluation | verified |
| M04 | Tail model comparison | `src/riskdesk/tail_models.py` `tail_models` (69-149) | parametric, EVT, GARCH filtered and Monte Carlo | partially verified |
| M05 | VaR and ES backtests | `src/riskdesk/backtest.py` `var_backtest` (111-136) | statistical tests | partially verified |
| M06 | Book Greeks | `src/riskdesk/derivatives.py` `book_greeks` (192-212) | closed-form option pricing (via Option Desk) | verified |
| M07 | Spot and vol scenario grid | `src/riskdesk/derivatives.py` `scenario_grid` (226-248) | full revaluation versus Taylor approximation | verified |
| M08 | Historical full-revaluation P&L | `src/riskdesk/derivatives.py` `historical_pnl` (251-272) | historical simulation, full revaluation | verified |
| M09 | Covariance estimation | `src/riskdesk/decomposition.py` `covariance_estimate` (106-146) | sample, EWMA, Ledoit-Wolf shrinkage | verified |
| M10 | Parametric VaR and ES with Euler allocation | `src/riskdesk/decomposition.py` `parametric_var` (149-188) | variance-covariance, Euler allocation | verified |
| M11 | Historical ES with Euler allocation | `src/riskdesk/decomposition.py` `historical_es` (191-226) | historical simulation, Euler allocation | verified |
| M12 | Factor exposure and variance split | `src/riskdesk/decomposition.py` `factor_exposure` (229-266) | OLS factor regression | verified |
| M13 | Limit checks | `src/riskdesk/limits.py` `check_limits` (128-138) | rule evaluation | verified |
| M14 | Pre-trade what-if | `src/riskdesk/limits.py` `what_if` (190-237) | revaluation of a modified book | verified |
| M15 | Liquidity horizon and L-VaR | `src/riskdesk/liquidity.py` `liquidity_risk` (39-95) | participation-rate liquidation, exogenous spread cost | partially verified |
| M16 | Historical replay | `src/riskdesk/scenarios.py` `historical_replay` (74-105) | historical scenario | verified |
| M17 | Dated scenario library | `src/riskdesk/scenarios.py` `scenario_library` (148-152) | reference data (dates and sources) | partially verified |
| M18 | Reverse stress | `src/riskdesk/scenarios.py` `reverse_stress` (178-233) | constrained quadratic minimisation | verified |
| M19 | Scenario scaling | `src/riskdesk/scenarios.py` `scale_scenario` (243-264) | linear scaling | verified |
| M20 | SA-CCR exposure at default | `src/riskdesk/counterparty.py` `saccr_ead` (257-285), `_netting_set` (159-254) | regulatory standardised formula (CRE52) | partially verified |
| M21 | Exposure profile summary | `src/riskdesk/counterparty.py` `exposure_profile_summary` (322-357) | regulatory averaging of a simulated profile (CRE50, CRE53) | verified |
| M22 | ASRF (Vasicek) credit VaR | `src/riskdesk/credit.py` `asrf_credit_var` (63-90) | one-factor analytic loss quantile | verified |
| M23 | Gaussian copula credit VaR | `src/riskdesk/credit.py` `copula_credit_var` (93-134) | one-factor Monte Carlo | verified |
| M24 | FRTB IMA liquidity-adjusted ES and IMCC | `src/riskdesk/frtb.py` `frtb_imcc` (98-114) | regulatory formula (MAR33) | partially verified |
| M25 | FRTB IMA capital aggregation | `src/riskdesk/frtb.py` `frtb_ima_capital` (153-177) | regulatory formula (MAR33, MAR32.9) | partially verified |
| M26 | FRTB P&L attribution test | `src/riskdesk/frtb.py` `frtb_pla` (201-218) | rank correlation and KS distance (MAR32) | verified |
| M27 | FRTB backtesting exception count | `src/riskdesk/frtb.py` `frtb_backtest` (249-266) | exception counting (MAR32) | partially verified |
| M28 | FRTB SA FX delta and vega | `src/riskdesk/frtb.py` `frtb_sbm_fx` (349-393) | sensitivities-based method (MAR21) | partially verified |
| M29 | ORE exposure and XVA adapter | `src/riskdesk/ore.py` `run_ore` (61-82), `prepare_config` (10-58) | adapter to an external risk-neutral engine | not validated |

Independent review evidence is in [research/math-review](../../research/math-review/README.md). Each check id
below names a row of that area's `report.md`.

## Cards

### M01 Historical VaR and ES

- Purpose: loss quantile and tail mean of a supplied P&L sample over its stated horizon.
- Inputs: P&L list, portfolio value, confidence, horizon days, provenance (src/riskdesk/models.py:18-22).
- Outputs: var, expected_shortfall, observations, tail probability mass, backend confidence, skfolio version.
- Key assumptions: ASSUMPTIONS.md rows for M01; I10 (integral boundary adjustment).
- Limitations: no horizon scaling; equal weights; fewer than 20 tail observations is flagged degraded
  (analytics.py:41), not refused.
- Validation evidence: tests/test_risk.py (fractional tail mass by hand, integral boundary, gain-only sample);
  research/math-review/tail hs-var-* and hs-es-* (hand order statistic and fractional tail mass, four (n, q) pairs).
- Sources: skfolio `value_at_risk` and `cvar` (risk-tail/reference.md:13-18).
- Status: verified.

### M02 Linear exposure and concentration

- Purpose: gross and net exposure, leverage and gross shares per asset.
- Inputs: NAV and signed linear positions (models.py:25-40). Outputs: gross, net, leverages, net_by_asset, gross_shares.
- Key assumptions: ASSUMPTIONS.md rows for M02.
- Limitations: linear positions only; no FX translation.
- Validation evidence: tests/test_risk.py test_exposure_sign_scaling_and_concentration (hand values). No
  research/math-review check: the formulas are sums.
- Sources: none needed (definitions in the code, analytics.py:57-75).
- Status: verified.

### M03 Linear stress revaluation

- Purpose: P&L of linear positions under named shock vectors; also the revaluation engine for M14, M16, M18, M19.
- Inputs: NAV, positions, scenarios with a shock for every asset (models.py:43-61). Outputs: pnl, loss,
  stressed NAV and contributions per scenario.
- Key assumptions: ASSUMPTIONS.md rows for M03.
- Limitations: no derivatives, no financing, no probabilities.
- Validation evidence: tests/test_risk.py (shorts revalued, missing shock refused, stressed NAV); indirectly
  research/math-review/scenarios *-revalued-loss and scale-loss.
- Sources: none needed.
- Status: verified.

### M04 Tail model comparison

- Purpose: VaR and ES of one P&L history under historical, normal, Student-t, EVT peaks over threshold,
  filtered historical, GARCH-EVT and GARCH-t Monte Carlo.
- Inputs: as M01; series in time order. Outputs: one row per method, unavailable methods with reasons, GARCH
  diagnostics.
- Key assumptions: ASSUMPTIONS.md rows for M04; I09, I21, I22.
- Limitations: GARCH needs at least 60 observations (risk-tail/reference.md:78) and converges only on some
  samples; EVT needs q beyond the threshold; Student-t and EVT ES are not reported when infinite.
- Validation evidence: tests/test_var_backtest_models.py (16 tests: integrals, EVT inversion, t(4) quantile,
  GARCH filter equality, reproducibility); research/math-review/tail normal-*, student-t-es-integral, evt-*,
  garch-sigma-next, garch-nonconvergence-flagged.
- Sources: McNeil and Frey (2000) eq. (9), (10), (14) (risk-tail/reference.md:44-65); Option Desk
  `fit_garch_t` and `simulate_paths`.
- Status: partially verified. UNPROVEN: the Monte Carlo column has no independent check in research/math-review;
  the maximum likelihood fits are scipy's and are not re-estimated independently; GARCH convergence on general
  data (non-convergence observed on an i.i.d. t(4) sample in this review); forecast accuracy of any column.

### M05 VaR and ES backtests

- Purpose: Kupiec, Christoffersen, Basel traffic light and Acerbi-Szekely Z2 on a forecast series.
- Inputs: P&L, VaR (and optionally ES with a stated null), confidence, horizon, seed (backtest.py:21-44).
- Outputs: exception counts, LR statistics and p-values, Basel zone (99% one-day only), Z2 with simulated p-value.
- Key assumptions: ASSUMPTIONS.md rows for M05; I08, I11, I12, I23.
- Limitations: asymptotic p-values; Z2 p-value conditional on the chosen null family; Basel zone only at 99% one day.
- Validation evidence: tests/test_var_backtest.py (14 tests); research/math-review/backtest basel-* (exact
  binomial sums for T = 250, 500, 1000), kupiec-*, christoffersen-*, z2, z2-p-normal-null.
- Sources: Kupiec (1995), Christoffersen (1998), MAR99.17 Table 2, MathWorks statement of Acerbi and Szekely
  (2014) (risk-backtest/reference.md:14-92).
- Status: partially verified. UNPROVEN: fidelity to the Kupiec, Christoffersen and Acerbi-Szekely papers (not
  read); MAR99 Table 2 transcription (not re-read here); calibration of the Z2 p-value when the true forecast
  distribution is outside the stated family.

### M06 Book Greeks

- Purpose: cash Greeks per underlying for books of linear positions and European options.
- Inputs: underlyings (spot or future price), positions with option terms (derivatives.py:26-80).
- Outputs: option model value, linear notional, cash delta, cash gamma per 1%, vega per point, theta per day,
  rho per point, per underlying and in total.
- Key assumptions: ASSUMPTIONS.md rows for M06; I20.
- Limitations: European exercise, one flat vol per option, no cross-gamma, no FX translation.
- Validation evidence: tests/test_derivatives.py (finite differences of the revalued book, put-call parity);
  research/math-review/derivatives rho-* and value-* (own BSM and Black-76 prices, central differences in r).
- Sources: Black and Scholes (1973), Merton (1973), Black (1976) (risk-derivatives/reference.md:77-83);
  Option Desk pricing functions.
- Status: verified. Black-76 rho comes from the engine since Option Desk 4a282d9 (I20).

### M07 Spot and vol scenario grid

- Purpose: full-revaluation P&L on a spot by vol grid against delta-gamma and delta-gamma-vega approximations.
- Inputs: as M06 plus spot and vol shocks (derivatives.py:83-92). Outputs: cells with full P&L, approximations
  and errors; maximum absolute errors.
- Key assumptions: ASSUMPTIONS.md rows for M07.
- Limitations: one joint shock direction; time fixed; no vanna or vomma terms.
- Validation evidence: tests/test_derivatives.py (parity book exact, linear book exact, third-order error,
  vega absorbs a pure vol shock). No research/math-review check.
- Sources: as M06.
- Status: verified.

### M08 Historical full-revaluation P&L

- Purpose: P&L vector of the option book under historical spot and vol moves, passed to M01 for VaR and ES.
- Inputs: as M06 plus scenarios, horizon, time mode, confidence, portfolio value (derivatives.py:100-116).
- Outputs: P&L vector, settled options, M01 tail result.
- Key assumptions: ASSUMPTIONS.md rows for M08.
- Limitations: payoff of options expiring inside the horizon is undiscounted; vol changes are parallel per underlying.
- Validation evidence: tests/test_derivatives.py (parity book closed form, decay mode charges theta and settles
  expiring options). No research/math-review check.
- Sources: as M06.
- Status: verified.

### M09 Covariance estimation

- Purpose: sample, EWMA or Ledoit-Wolf covariance of asset returns, with a positive definiteness test.
- Inputs: assets, return rows, horizon, method, decay for EWMA (decomposition.py:20-44).
- Outputs: covariance, volatilities, correlation, eigenvalue range, positive_definite, shrinkage.
- Key assumptions: ASSUMPTIONS.md rows for M09.
- Limitations: no repair of a non-positive-definite estimate (flagged degraded).
- Validation evidence: tests/test_decomposition.py (brute-force sample sum, RiskMetrics recursion, Ledoit-Wolf
  lemmas); research/math-review/decomposition cov-sample, cov-ewma-recursion. Ledoit-Wolf has no
  research/math-review check.
- Sources: RiskMetrics Technical Document (1996), Ledoit and Wolf (2004) (risk-attribution/reference.md:34-66).
- Status: verified.

### M10 Parametric VaR and ES with Euler allocation

- Purpose: normal VaR and ES of a linear book with marginal, component, percentage and incremental contributions.
- Inputs: NAV, positions, covariance, confidence above 0.5, horizon (decomposition.py:47-60).
- Outputs: VaR, ES, sigma, z and per-position contributions.
- Key assumptions: ASSUMPTIONS.md rows for M10.
- Limitations: normality and zero mean; zero portfolio variance refused.
- Validation evidence: tests/test_decomposition.py (closed form, quadrature, sums, finite differences,
  incremental by recomputation); research/math-review/decomposition param-* (loops, quadrature, central
  differences, full recomputation).
- Sources: Tasche (2008) eq. (2.6), (2.10), (3.4a), (3.10a) (risk-attribution/reference.md:68-89).
- Status: verified.

### M11 Historical ES with Euler allocation

- Purpose: historical ES of a linear book and each position's tail-weighted contribution.
- Inputs: NAV, positions, return rows, confidence, horizon. Outputs: ES, components, tail scenarios.
- Key assumptions: ASSUMPTIONS.md rows for M11.
- Limitations: contributions depend on input order at tied losses (flagged degraded).
- Validation evidence: tests/test_decomposition.py (equals M01 on the same P&L, hand fractional tail, derivative
  of ES); research/math-review/decomposition hist-* (three confidences, every component).
- Sources: Tasche (2008) eq. (3.11a) and section 3.4 (risk-attribution/reference.md:91-110).
- Status: verified.

### M12 Factor exposure and variance split

- Purpose: OLS betas per asset, portfolio factor exposure, and the systematic and idiosyncratic variance split.
- Inputs: positions, return rows, factor return rows (decomposition.py:67-81).
- Outputs: per-asset alpha, betas and R squared; portfolio exposure and beta; variance parts.
- Key assumptions: ASSUMPTIONS.md rows for M12.
- Limitations: in-sample identity only; collinear factors refused.
- Validation evidence: tests/test_decomposition.py (noiseless recovery, scikit-learn match);
  research/math-review/decomposition factor-betas-normal-equations, factor-split-adds.
- Sources: risk-attribution/reference.md:112-128.
- Status: verified.

### M13 Limit checks

- Purpose: grade supplied Risk Desk results against user limits with warning thresholds.
- Inputs: limits and result payloads (limits.py:24-61). Outputs: per-limit value, utilisation, status, overall status.
- Key assumptions: ASSUMPTIONS.md rows for M13.
- Limitations: values are trusted as supplied; only currency and as-of provenance are compared.
- Validation evidence: tests/test_limits.py (statuses by hand, min mirrors max, missing metrics, tampered
  artifacts). No research/math-review check: comparisons only.
- Sources: none (desk definitions, risk-limits/reference.md:1-5).
- Status: verified.

### M14 Pre-trade what-if

- Purpose: exposure, stress and tail figures before and after proposed trades, optionally graded by M13.
- Inputs: book, trades, scenarios, asset returns, limits (limits.py:141-187). Outputs: before, after, change,
  limits_after.
- Key assumptions: ASSUMPTIONS.md rows for M14.
- Limitations: linear trades at as-of prices; NAV unchanged.
- Validation evidence: tests/test_limits.py test_what_if_matches_hand_revaluation and related tests.
- Sources: none (risk-limits/reference.md:45-65).
- Status: verified.

### M15 Liquidity horizon and L-VaR

- Purpose: days to liquidate, liquidation schedule, exogenous spread cost and liquidity-adjusted VaR.
- Inputs: positions, participation rate, spread multiplier, per-asset liquidity, optional P&L (liquidity.py:15-36).
- Outputs: per-asset days and cost, schedule, total cost, VaR and L-VaR.
- Key assumptions: ASSUMPTIONS.md rows for M15; I04.
- Limitations: no endogenous price impact; no horizon rescaling; additive L-VaR.
- Validation evidence: tests/test_liquidity.py (hand calculation, brute-force schedule); research/math-review/
  liquidity days-*, col-*, schedule, lvar-additive.
- Sources: Bangia, Diebold, Schuermann and Stroughair (1999) eq. (4); Qi and Ng (2009) for the additive form
  (risk-liquidity/reference.md:29-73).
- Status: partially verified. UNPROVEN: that the additive L-VaR is Bangia et al.'s form (I04).

### M16 Historical replay

- Purpose: shocks from the caller's dated price levels over a window, revalued by M03.
- Inputs: book, prices, window, measure, proxies (scenarios.py:36-58). Outputs: shocks, series used, scenario P&L.
- Key assumptions: ASSUMPTIONS.md rows for M16.
- Limitations: exact dates only; per-asset peak-to-trough falls need not coincide.
- Validation evidence: tests/test_stress_scenarios.py (hand arithmetic, exhaustive pairwise search). No
  research/math-review check.
- Sources: risk-stress/reference.md:26-48.
- Status: verified.

### M17 Dated scenario library

- Purpose: three dated crisis windows with quoted sources; no prices.
- Inputs: none. Outputs: windows with start, end, reason and sources (scenarios.py:115-152).
- Key assumptions: I03 (Lehman end date is a convention).
- Limitations: dates only; starts are US and continental European for COVID (risk-stress/reference.md:93-94).
- Validation evidence: tests/test_stress_scenarios.py test_the_library_dates_are_the_ones_cited_in_reference_md
  (guards code against reference.md, not against the sources).
- Sources: BIS 79th Annual Report, FSB holistic review, Bank of England (scenarios.py:116-145).
- Status: partially verified. UNPROVEN by this review: the quoted dates against the sources (not re-read).

### M18 Reverse stress

- Purpose: the smallest-Mahalanobis-distance shock that produces a target loss, with floors.
- Inputs: book, target loss, horizon, covariance, floors (scenarios.py:157-175). Outputs: shocks, distances,
  binding floors, normal exceedance probability, revaluation.
- Key assumptions: ASSUMPTIONS.md rows for M18.
- Limitations: geometric plausibility, not probability; normal probability is a reference figure.
- Validation evidence: tests/test_stress_scenarios.py (one-asset hand case, perturbations, 300,001-point grid,
  optimality conditions, seeded simulation); research/math-review/scenarios unbounded-* and floor-binds-*
  (search along the equal-loss line with an explicit inverse).
- Sources: derivation in risk-stress/reference.md:119-164; no external paper.
- Status: verified.

### M19 Scenario scaling

- Purpose: the multiple of a scenario that reaches a target loss.
- Inputs: book, scenario, target loss. Outputs: multiple, scaled shocks, base and scaled revaluation.
- Key assumptions: ASSUMPTIONS.md rows for M19.
- Limitations: linear books; refused if any scaled shock falls below -100%.
- Validation evidence: tests/test_stress_scenarios.py test_scaling_matches_hand_arithmetic;
  research/math-review/scenarios scale-*.
- Sources: risk-stress/reference.md:166-172.
- Status: verified.

### M20 SA-CCR exposure at default

- Purpose: CRE52 EAD of one bilateral netting set, margined or unmargined, all five asset classes.
- Inputs: trades with class-specific fields, collateral and margin terms (counterparty.py:34-127).
- Outputs: EAD, RC, PFE, multiplier, add-ons by class and hedging set, trade-level figures, cap flag.
- Key assumptions: ASSUMPTIONS.md rows for M20; I05, I06, I07, I13, I14, I15, I24.
- Limitations: no basis or volatility hedging sets, CDO tranches, CCP MPOR floors, 20-day MPOR cases or
  multiple netting sets (counterparty.py:268-270).
- Validation evidence: tests/test_counterparty.py (CRE99 examples 1 to 5 and margin cases, hand FX and equity);
  research/math-review/counterparty example-*-published and example-*-module (independent CRE52
  recomputation), fx-no-published-example, equity-no-published-example, negative-rate-shift, margined-cap-*.
- Sources: CRE52, CRE99, BCBS 279 Annex 4a (risk-counterparty/reference.md:5-16).
- Status: partially verified. UNPROVEN: FX and equity add-ons have no published example (maintainer decision
  2026-11-04: ship as partially verified, I05); the CRE99 EADs and CRE52.72 constants are the engineers'
  transcription of bis.org images, not re-read here (I24); the zero aggregate add-on branch is unguarded (I14).

### M21 Exposure profile summary

- Purpose: peak PFE, EPE and Effective EPE from an ORE netting-set exposure report.
- Inputs: ORE rows with Time, BaselEE and PFE (counterparty.py:288-319). Outputs: peak PFE and date, EPE,
  Effective EPE, Effective EE path.
- Key assumptions: ASSUMPTIONS.md rows for M21; I16.
- Limitations: no EAD; grids without a one-year date are flagged degraded.
- Validation evidence: tests/test_counterparty.py (by hand, convergence to closed-form integrals, short sets).
  No research/math-review check.
- Sources: CRE50.27-31, CRE53.12-13; ORE ReportWriter at the pinned revision (risk-counterparty/reference.md:104-133).
- Status: verified.

### M22 ASRF (Vasicek) credit VaR

- Purpose: loss quantile of an infinitely granular default-mode portfolio.
- Inputs: obligors with exposure, PD, LGD, correlation; confidence; horizon (credit.py:20-48).
- Outputs: credit VaR, expected loss, unexpected loss, contributions.
- Key assumptions: ASSUMPTIONS.md rows for M22; I25.
- Limitations: no name concentration, no migration, deterministic LGD, no IRB maturity adjustment.
- Validation evidence: tests/test_credit.py (CRE99 Table 1 risk weights, brute force over the factor);
  research/math-review/credit rw-* (CRE99 Table 1 read from bis.org in this review, all 18 PDs within 0.005
  percentage points) and ul-* (module against a stdlib CRE31.5 term).
- Sources: CRE31.5, CRE99 Table 1 (risk-credit/reference.md:5-55).
- Status: verified. The column-to-LGD mapping of the bis.org table was not readable in the fetched text; LGD 40%
  is the engineers' reading, consistent with all 18 values reproducing.

### M23 Gaussian copula credit VaR

- Purpose: Monte Carlo default-mode loss distribution of a finite pool, VaR and ES via M01.
- Inputs: obligors with factor loadings, scenarios, seed (credit.py:28-60). Outputs: VaR, ES, expected and
  analytic expected loss, standard deviation.
- Key assumptions: ASSUMPTIONS.md rows for M23.
- Limitations: one factor; Monte Carlo error.
- Validation evidence: tests/test_credit.py (exact finite-pool distribution by quadrature, convergence to
  Vasicek, reproducibility). No research/math-review check.
- Sources: risk-credit/reference.md:57-78.
- Status: verified.

### M24 FRTB IMA liquidity-adjusted ES and IMCC

- Purpose: MAR33.4 liquidity-horizon cascade, MAR33.6 stress calibration and MAR33.15 IMCC.
- Inputs: 10-day ES cascades for portfolio and risk classes (frtb.py:61-75). Outputs: scaled ES per set, IMCC.
- Key assumptions: ASSUMPTIONS.md rows for M24; I01.
- Limitations: ES is supplied, not estimated; stress period consistency not checked.
- Validation evidence: tests/test_frtb.py (hand calculation, sqrt-of-time closed form, overflow); research/
  math-review/frtb cascade-* (sqrt(LH/10) for all five horizons, mixed weights) and imcc.
- Sources: MAR33.4, MAR33.6, MAR33.15 (risk-frtb/reference.md:15-47).
- Status: partially verified. UNPROVEN: the per-class floor reading of MAR33.15 (I01).

### M25 FRTB IMA capital aggregation

- Purpose: C_A, DRC, IMA_G,A, PLA surcharge, aggregate capital and RWA.
- Inputs: IMCC, SES, DRC figures, exception count, desk standardised charges (frtb.py:117-141).
- Outputs: zone, multiplier, C_A, surcharge, aggregate capital, RWA.
- Key assumptions: ASSUMPTIONS.md rows for M25; I17.
- Limitations: averages and charges are inputs; MAR32.2 eligibility not tested.
- Validation evidence: tests/test_frtb.py (hand calculation, cap and excess branches, MAR32 Table 1). No
  research/math-review check.
- Sources: MAR33.41-46, MAR32.9 Table 1 (risk-frtb/reference.md:49-81).
- Status: partially verified. UNPROVEN by this review: the MAR32.9 Table 1 multipliers (frtb.py:28) against
  the source (not re-read).

### M26 FRTB P&L attribution test

- Purpose: Spearman and KS metrics between RTPL and HPL and the MAR32.42 zone.
- Inputs: 250 RTPL and HPL observations (frtb.py:186-189). Outputs: Spearman, KS, KS count, zone.
- Key assumptions: ASSUMPTIONS.md rows for M26; I19.
- Limitations: zone transitions over time not applied.
- Validation evidence: tests/test_frtb.py (independent calculations, exact KS boundaries); research/
  math-review/frtb pla-* (own average ranks and empirical CDFs, one green and one red case).
- Sources: MAR32.34-42 (risk-frtb/reference.md:103-123).
- Status: verified.

### M27 FRTB backtesting exception count

- Purpose: bank-wide zone and multiplier, or desk eligibility under MAR32.19.
- Inputs: APL, HPL, VaR at 99% (and 97.5% for desks), gaps allowed (frtb.py:221-236).
- Outputs: exceptions per series and level; zone and multiplier, or pass.
- Key assumptions: ASSUMPTIONS.md rows for M27; I02.
- Limitations: NMRF-driven exceptions are not disregarded.
- Validation evidence: tests/test_frtb.py (separate counting, ties, gaps, desk limits); research/math-review/
  frtb desk-limit-* (boundary at 12 and 13, 30 and 31).
- Sources: MAR32.3-19 (risk-frtb/reference.md:83-101).
- Status: partially verified. UNPROVEN: the 'more than 30' reading at 97.5% (I02).

### M28 FRTB SA FX delta and vega

- Purpose: FX delta and vega charge under the three correlation scenarios.
- Inputs: net FX delta and vega sensitivities, specified-pair election (frtb.py:271-300).
- Outputs: per-scenario delta and vega charges, binding scenario, capital.
- Key assumptions: ASSUMPTIONS.md rows for M28; I18.
- Limitations: curvature not computed (flagged degraded when vega is present); other risk classes, DRC and
  RRAO absent (risk-frtb/reference.md:170-180).
- Validation evidence: tests/test_frtb.py (one and two buckets, specified pairs, vega correlation, brute-force
  loop, MAR21.4(5)(b) fallback); research/math-review/frtb sbm-fx-capital-* (hand formula, both elections).
- Sources: MAR21.4-7, MAR21.86-95 (risk-frtb/reference.md:125-168).
- Status: partially verified. UNPROVEN by this review: MAR21 constants against the source (not re-read); the
  charge understates any book with optionality because curvature is missing.

### M29 ORE exposure and XVA adapter

- Purpose: run a trusted local ORE project in a worker and accept only error-free XVA output.
- Inputs: ORE project path, config, output path, data mode (ore.py:10-82). Outputs: ORE reports, input hashes,
  artifact path.
- Key assumptions: ASSUMPTIONS.md rows for M29.
- Limitations: risk-neutral valuation; Risk Desk does not check ORE's numbers.
- Validation evidence: tests/test_ore.py (5 tests: fresh cube, inactive simulation refused, path escape
  refused, backend errors rejected, the XVA result checker catches tampering). These test the adapter's
  safety, not ORE's numbers. The pinned ORE
  example (AGENTS.md) was not run in this review.
- Sources: Open Source Risk Engine (THIRD-PARTY.md, docs/ORE.md).
- Status: not validated. Risk Desk validates the adapter contract only; ORE's exposure and XVA figures have no
  independent check here.
