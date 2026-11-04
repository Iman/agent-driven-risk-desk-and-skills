"""Build docs/models/ASSUMPTIONS.md from the `assumptions` list each model function returns.

    python docs/models/build_assumptions.py

Texts are extracted by calling each function on its shipped example (plus the three variants
that reach the conditional assumptions), and from run_ore's literal list by AST, since running
ORE needs the ORE binary. The register is never retyped. Every extracted text must match exactly
one entry of CLASSIFICATION, and every entry must match a text, so wording drift fails loudly.
"""
import ast
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))  # this worktree's code, not an installed copy
OUT = Path(__file__).resolve().parent / "ASSUMPTIONS.md"

from riskdesk import (analytics, backtest, counterparty, credit, decomposition, derivatives,  # noqa: E402
                      frtb, limits, liquidity, scenarios, tail_models)

MODEL, DATA, REG = "modelling choice", "data assumption", "regulatory interpretation"


def example(name, **change):
    payload = json.loads((ROOT / "examples" / name).read_text(encoding="utf-8"))
    for key, value in change.items():
        if value is None:
            payload.pop(key, None)
        else:
            payload[key] = value
    return payload


UNMARGINED = dict(margined=False, threshold=None, minimum_transfer_amount=None, nica=None,
                  remargining_period_business_days=None, mpor_business_days=None)
CALLS = [  # (model id, function, payload, how it was reached)
    ("M01", analytics.tail_risk, example("tail.json"), "examples/tail.json"),
    ("M02", analytics.portfolio_exposure, example("portfolio.json"), "examples/portfolio.json"),
    ("M03", analytics.stress_test, example("stress.json"), "examples/stress.json"),
    ("M04", tail_models.tail_models, example("energy_tail.json"), "examples/energy_tail.json"),
    ("M05", backtest.var_backtest, example("var_backtest_energy.json"), "examples/var_backtest_energy.json"),
    ("M06", derivatives.book_greeks, example("derivatives_book.json"), "examples/derivatives_book.json"),
    ("M07", derivatives.scenario_grid, example("derivatives_grid.json"), "examples/derivatives_grid.json"),
    ("M08", derivatives.historical_pnl, example("derivatives_historical.json"), "examples/derivatives_historical.json"),
    ("M08", derivatives.historical_pnl, example("derivatives_historical.json", time_mode="fixed"),
     "examples/derivatives_historical.json with time_mode fixed"),
    ("M09", decomposition.covariance_estimate, example("decomposition_covariance.json"),
     "examples/decomposition_covariance.json"),
    ("M10", decomposition.parametric_var, example("decomposition_parametric.json"), "examples/decomposition_parametric.json"),
    ("M11", decomposition.historical_es, example("decomposition_historical.json"), "examples/decomposition_historical.json"),
    ("M12", decomposition.factor_exposure, example("decomposition_factor.json"), "examples/decomposition_factor.json"),
    ("M13", limits.check_limits, example("limits_check.json"), "examples/limits_check.json"),
    ("M14", limits.what_if, example("limits_what_if.json"), "examples/limits_what_if.json"),
    ("M15", liquidity.liquidity_risk, example("liquidity_book.json"), "examples/liquidity_book.json"),
    ("M16", scenarios.historical_replay, example("stress_replay.json"), "examples/stress_replay.json"),
    ("M16", scenarios.historical_replay, example("stress_replay.json", measure="worst_peak_to_trough"),
     "examples/stress_replay.json with measure worst_peak_to_trough"),
    ("M18", scenarios.reverse_stress, example("stress_reverse.json"), "examples/stress_reverse.json"),
    ("M19", scenarios.scale_scenario, example("stress_scale.json"), "examples/stress_scale.json"),
    ("M20", counterparty.saccr_ead, example("counterparty_saccr.json"), "examples/counterparty_saccr.json"),
    ("M20", counterparty.saccr_ead, example("counterparty_saccr.json", **UNMARGINED),
     "examples/counterparty_saccr.json unmargined"),
    ("M21", counterparty.exposure_profile_summary, example("counterparty_profile.json"), "examples/counterparty_profile.json"),
    ("M22", credit.asrf_credit_var, example("credit_asrf.json"), "examples/credit_asrf.json"),
    ("M23", credit.copula_credit_var, example("credit_copula.json"), "examples/credit_copula.json"),
    ("M24", frtb.frtb_imcc, example("frtb_imcc.json"), "examples/frtb_imcc.json"),
    ("M25", frtb.frtb_ima_capital, example("frtb_ima_capital.json"), "examples/frtb_ima_capital.json"),
    ("M26", frtb.frtb_pla, example("frtb_pla.json"), "examples/frtb_pla.json"),
    ("M27", frtb.frtb_backtest, example("frtb_backtest.json"), "examples/frtb_backtest.json"),
    ("M28", frtb.frtb_sbm_fx, example("frtb_sbm_fx.json"), "examples/frtb_sbm_fx.json"),
]


def ore_assumptions():
    """run_ore's assumptions are one literal list (ore.py); read it without running ORE."""
    tree = ast.parse((ROOT / "src" / "riskdesk" / "ore.py").read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if isinstance(node, ast.keyword) and node.arg == "assumptions":
            return ast.literal_eval(node.value)
    raise ValueError("run_ore assumptions list not found in ore.py")


def extract():
    """{assumption text: {model id: [how reached]}} in first-seen order."""
    found = {}
    for model, fn, payload, how in CALLS:
        for text in fn(payload)["assumptions"]:
            found.setdefault(text, {}).setdefault(model, []).append(how)
    for text in ore_assumptions():
        found.setdefault(text, {}).setdefault("M29", []).append("src/riskdesk/ore.py run_ore literal, by AST")
    return found


# (fragment unique to one returned text, class, consequence if the assumption is wrong)
CLASSIFICATION = [
    ("Each P&L sample already spans", DATA, "If the P&L is daily but the stated horizon is longer, VaR and ES are understated by the missing horizon scaling."),
    ("Equally weighted empirical", MODEL, "Regime change or serial dependence in the sample is not reflected; the measure describes the past window only."),
    ("Loss is positive; negative VaR or ES denotes a gain", DATA, "A caller who passes losses as positive P&L inverts every sign and reads gains as risk."),
    ("VaR uses skfolio's empirical order statistic", MODEL, "Another quantile rule (interpolated, or floor index) gives a different VaR on small samples; ES is less sensitive."),
    ("Market values are signed and already translated", DATA, "Untranslated foreign amounts or unsigned shorts give wrong gross, net and leverage."),
    ("Gross concentration uses absolute position values", MODEL, "None if the definition is accepted; a netted concentration measure would differ for books with offsetting positions."),
    ("Positions are linear assets", DATA, "Options passed as linear holdings are revalued linearly and their convexity is lost."),
    ("Shocks are simple asset returns; all assets", DATA, "Log returns passed as simple returns misstate large shocks; a missing shock is refused, not zeroed."),
    ("No probability is attached to a scenario", MODEL, "None for the arithmetic; a reader who treats a stress loss as a likely loss misreads it."),
    ("Each P&L sample spans the stated horizon and the series is in time order", DATA, "Out-of-order rows break the GARCH filter and the one-step forecast; horizon mismatch as for M01."),
    ("Normal and Student-t parameters are maximum likelihood", MODEL, "A poor fit (for example a skewed sample) gives parametric VaR and ES that differ from the empirical tail."),
    ("EVT fits a generalised Pareto", MODEL, "The 10% threshold fraction is a choice; a different k changes xi, beta and the EVT quantile."),
    ("GARCH(1,1)-t is Option Desk's Bayesian fit", MODEL, "The posterior mean ignores parameter uncertainty in two columns; non-convergence makes all three unreliable (flagged degraded)."),
    ("The forecast is one sample period ahead", MODEL, "Reading these figures as tested or calibrated forecasts would be unsupported; use M05 to backtest."),
    ("An exception is a realised loss strictly greater", REG, "Counting a loss equal to VaR as an exception would raise counts at ties; MAR99 wording is the cited basis."),
    ("Each VaR was forecast before its P&L was realised", DATA, "Look-ahead VaR series pass backtests they should fail."),
    ("Kupiec and Christoffersen p-values use their asymptotic", MODEL, "In small samples or with few exceptions the chi-square approximation can be poor; exact tests would differ."),
    ("The ES p-value is simulated under a stated location-scale null", MODEL, "If the bank's forecast distribution is not normal or Student-t, the Z2 p-value is miscalibrated (see I08)."),
    ("Prices and Greeks from optiondesk_engine", MODEL, "An engine defect propagates; the Black-76 rho defect did, until Option Desk 4a282d9 (see I20)."),
    ("Time is ACT/365 years", DATA, "Inputs built on another day count shift time to expiry and every Greek slightly."),
    ("Black-76 rho is -t x V with the future fixed", MODEL, "STALE TEXT since Option Desk 4a282d9: the engine now returns -tV itself (see I20). The value is unchanged; the second clause is false."),
    ("European exercise, one flat implied volatility", MODEL, "American options and smile or skew effects are not captured; full revaluation under shocks keeps one vol per option."),
    ("All prices and amounts are in the stated currency", DATA, "Mixed-currency books give wrong totals; no FX translation is attempted."),
    ("Totals add per-underlying figures", MODEL, "Cross-gamma and non-parallel vol moves are missing from the totals."),
    ("Each cell applies the same relative spot shock", MODEL, "The grid shows one joint direction only; dispersion between underlyings is not explored."),
    ("Instantaneous shocks: time to expiry is held fixed", MODEL, "Theta over any horizon is excluded from the grid P&L."),
    ("Approximation error is approximation P&L minus", MODEL, "None for the arithmetic; it is a sign convention a reader must apply."),
    ("Delta-gamma-vega adds first-order vega only", MODEL, "Vanna and vomma effects appear as approximation error, not as terms."),
    ("Time decays by horizon_days / 365 years", MODEL, "Decay mode charges calendar time; a trading-day horizon gives a different theta charge."),
    ("Spot returns are simple returns applied", DATA, "Log returns passed as simple returns misstate large moves."),
    ("A scenario without vol_changes holds", MODEL, "Historical P&L omits vol moves for those scenarios, typically understating option risk in stress."),
    ("An option whose life ends inside the horizon", MODEL, "Payoff is undiscounted over the remaining horizon; immaterial for short horizons, not modelled otherwise."),
    ("Time to expiry is held fixed: the P&L excludes theta", MODEL, "Fixed mode excludes theta over the horizon, which matters for short-dated books."),
    ("Each return row spans horizon_days", DATA, "Daily rows labelled with a longer horizon understate the risk by the missing scaling."),
    ("Rows are ordered oldest first; EWMA", DATA, "Reversed rows give the oldest observation the largest EWMA weight."),
    ("Sample is unbiased (T-1)", MODEL, "Estimator choice changes the estimate by up to a factor T/(T-1) and by the shrinkage amount."),
    ("Positive definiteness is tested against", MODEL, "A matrix just inside the tolerance is reported positive definite; no repair is applied either way."),
    ("Portfolio P&L is normal with zero mean", MODEL, "Fat tails and non-zero drift are ignored; parametric VaR understates tail risk for heavy-tailed books."),
    ("Loss is positive. Marginal values are per unit", MODEL, "None for the arithmetic (components summing to the total is checked in research/math-review/decomposition)."),
    ("Incremental VaR is total VaR minus", MODEL, "Incremental VaR does not sum to VaR; a reader adding it up overstates or understates the total."),
    ("Percentage contributions can be negative", MODEL, "None; a reading aid for hedges and concentrations."),
    ("Each scenario row is equally likely", MODEL, "Weighted or regime-filtered histories are not supported; recent stress gets no extra weight."),
    ("A position's ES contribution is its tail-weighted", MODEL, "Contributions are noisy with few tail scenarios and depend on input order at ties (flagged)."),
    ("Loss is positive; contributions sum to the historical ES", MODEL, "None for the arithmetic (checked in research/math-review/decomposition)."),
    ("Each asset is regressed on all factors", MODEL, "Omitted or collinear factors bias betas; collinear designs are refused."),
    ("Variances use T-1. In sample", MODEL, "Out of sample the split need not add up; the identity is an in-sample property."),
    ("Idiosyncratic includes residual cross-covariance", MODEL, "None; a diagonal factor model would report only the specific part."),
    ("Factor exposure is currency P&L per 1.00", DATA, "Factor returns supplied in percent rather than per 1.00 scale exposures by 100."),
    ("Values are read from the supplied result payloads", DATA, "A tampered or stale payload is graded as supplied; provenance checks flag currency and as-of only."),
    ("max limits breach when value > limit", MODEL, "A value exactly at the hard limit is within; a desk whose policy is breach-at-limit would differ."),
    ("Utilisation is value divided by limit", MODEL, "None; status, not utilisation, is the authority."),
    ("A limit whose metric, asset or scenario is absent", MODEL, "None; missing data is reported, never passed as within."),
    ("Overall status is the most severe", MODEL, "None; ordering is the desk's definition."),
    ("Each trade is a signed change in linear market value", DATA, "Trades priced away from as-of prices or non-linear trades are not represented."),
    ("NAV is unchanged: trades are assumed cash-financed", MODEL, "Financing costs, fees and NAV effects of the trade are ignored in leverage after."),
    ("Tail P&L is net market value per asset times", MODEL, "Assets whose P&L does not scale with value (options, leveraged products) are misrepresented."),
    ("Stress shocks to assets not yet held are dropped", MODEL, "None; there is no position for the shock to act on."),
    ("Days to liquidate = gross asset value", MODEL, "Participation-rate liquidation is the desk's definition; real liquidation speed depends on market depth and impact."),
    ("The schedule sells each asset at its daily capacity", MODEL, "Price moves during liquidation are ignored."),
    ("Cost of liquidity = 1/2 x gross value", MODEL, "The spread multiplier is a user input; Bangia et al. report 2.0 to 4.5 for their instruments only."),
    ("Liquidity-adjusted VaR = supplied-P&L historical VaR", MODEL, "The additive form rests on a secondary source (see I04); a correlation correction would change L-VaR."),
    ("Loss and cost are positive. Endogenous price impact", MODEL, "Large positions are under-costed when their own trades move the price."),
    ("Shocks are simple price returns of the caller's series", DATA, "Total-return and price-return series give different shocks; the caller's series defines the result."),
    ("Each asset's worst peak-to-trough fall", MODEL, "The combined shock is not the book's worst loss in the window; it can overstate or understate it."),
    ("w is the net market value per asset", DATA, "A covariance over a different horizon than the shocks mis-scales every distance."),
    ("Most plausible means the smallest Mahalanobis", MODEL, "Plausibility is geometric under the covariance; it is not a probability."),
    ("Every shock is floored at -100%", MODEL, "None for linear assets; floors make the problem non-closed-form and are solved numerically."),
    ("ASSUMPTION: loss_exceedance_probability_if_normal", MODEL, "Under fat tails the true exceedance probability is larger than the normal reference figure."),
    ("Loss is linear in the shocks, so the multiple", MODEL, "Exact for linear books only."),
    ("The multiple measures distance along one scenario", MODEL, "None; it is not a probability."),
    ("Basel Framework CRE52 (effective 1 January 2023)", REG, "Multi-netting-set and CCP cases are out of scope; applying the tool to them misstates EAD."),
    ("All amounts are in the request currency. notional is", DATA, "A notional on the wrong basis (for example units instead of value) scales the add-on directly."),
    ("collateral is the haircut value of net collateral", DATA, "Unhaircut collateral overstates C and understates RC and EAD."),
    ("Times are in years; ten business days are 10/250", REG, "None if CRE52.49 is accepted; another business-day convention moves the floors slightly."),
    ("The interest rate hedging sets use the offset formula", REG, "The no-offset alternative of CRE52.57 step 5 gives a different, larger add-on (see I13)."),
    ("Not modelled: basis and volatility hedging sets", REG, "Books with basis or volatility trades, CDO tranches or CCP clearing get a wrong EAD."),
    ("The CRE52.2 cap recomputes the netting set", REG, "Another reading of the cap changes EAD where the cap binds (see I07)."),
    ("BaselEE is ORE's undiscounted expected exposure", DATA, "If the ORE column meaning changes upstream, EPE and Effective EPE change silently."),
    ("PFE is ORE's quantile at the confidence level", DATA, "The PFE level is whatever ORE was configured with; it is not checked here."),
    ("EPE and Effective EPE weight each date", REG, "Coarse grids or a grid without a one-year date change the averages (degraded when the grid passes one year)."),
    ("No EAD is reported: alpha times Effective EPE", REG, "None; IMM EAD needs supervisory approval and is deliberately not produced."),
    ("Infinitely granular portfolio driven by one", MODEL, "Concentrated portfolios have more tail risk than ASRF shows; the copula (M23) captures finite-pool effects."),
    ("Default rate quantile is the CRE31.5 term", MODEL, "None for the arithmetic (CRE99 Table 1 is reproduced in research/math-review/credit)."),
    ("PD, LGD and correlation are caller inputs", DATA, "PD and correlation on a different horizon than stated misstate credit VaR."),
    ("Unexpected loss is credit VaR minus expected loss", REG, "Reading unexpected loss as IRB capital omits the maturity adjustment and the CRE31.7 multiplier."),
    ("Rating migration is not modelled", MODEL, "Mark-to-market credit losses from downgrades are excluded; default-mode VaR understates them."),
    ("Obligor i defaults when a_i Z + sqrt(1-a_i^2)", MODEL, "One factor only; sector or regional correlation structure is not represented."),
    ("Loss is the sum of exposure times LGD over defaulted", MODEL, "Deterministic LGD ignores recovery risk and its correlation with defaults."),
    ("PD, LGD and loadings are caller inputs", DATA, "As for the ASRF inputs."),
    ("VaR and ES come from the desk's historical tail", MODEL, "None for the arithmetic; Monte Carlo error remains (see next row)."),
    ("Results are reproducible for the same seed", MODEL, "With too few scenarios the tail estimates carry visible Monte Carlo error."),
    ("Inputs are 10-day ES values per liquidity-horizon", DATA, "ES not at 97.5% or not per MAR33.12 horizon subsets makes the cascade meaningless."),
    ("MAR33.6 floors ES_F,C / ES_R,C at 1. The same floor", REG, "If MAR33.15 intends no per-class floor, IMCC is overstated where a class ratio is below 1 (see I01)."),
    ("Risk classes not supplied contribute nothing", DATA, "Omitting a class with exposure understates the constrained IMCC."),
    ("The stress period for each class must be", DATA, "A class calibrated on its own stress period overstates or understates its IMCC(C_i)."),
    ("Amounts are positive losses in the stated currency; no non-modellable", MODEL, "None; SES and DRC are separate inputs to M25."),
    ("IMCC, SES, DRC and every standardised charge", DATA, "Errors in the supplied averages pass straight into capital."),
    ("m_c is the MAR32.9 table value", REG, "None if the MAR32.9 Table 1 transcription is correct (frtb.py:28)."),
    ("The multiplier applies to the 60-day IMCC average only", REG, "If SES were also scaled, C_A would be higher."),
    ("k uses the sum of desk-level standardised charges", REG, "A different denominator for k changes the surcharge."),
    ("The 10% eligibility criterion of MAR32.2", REG, "A bank failing MAR32.2 is not detected."),
    ("RTPL and HPL are the desk's most recent 250", DATA, "A window that is not the latest 250 days gives a PLA zone for the wrong period."),
    ("Spearman uses scipy average ranks for ties", REG, "Another tie rule changes Spearman when P&L values repeat (see I19)."),
    ("KS is the largest gap between the two empirical", REG, "None at exactly 250 observations (checked in research/math-review/frtb)."),
    ("Zone exit rules of MAR32.43-44", REG, "The reported zone is the test result for this window only, not the desk's regulatory status."),
    ("P&L is signed profit; VaR is a positive one-day loss", REG, "As for M05; a tie at VaR is not an exception."),
    ("Actual and hypothetical exceptions are counted separately", REG, "None if MAR32.5 is read as cited."),
    ("A missing P&L or VaR on a day counts as an exception", REG, "None if MAR32.5 and MAR32.18 are read as cited; gaps raise the count."),
    ("The 250 observations are the most recent 12 months", REG, "NMRF-driven exceptions the supervisor would disregard are still counted, so counts can be higher than regulatory ones."),
    ("Sensitivities are supplied in the reporting currency", DATA, "Sensitivities defined differently from MAR21.24 and MAR21.25 give a wrong charge."),
    ("One bucket per currency against the reporting currency", REG, "The specified-pair reading (see I18) changes the delta risk weight by sqrt(2)."),
    ("Vega risk weight 100% (MAR21.92 Table 13, FX)", REG, "None if the Table 13 transcription is correct."),
    ("The capital requirement is the largest of the low", REG, "Curvature is omitted, so an options book is understated (flagged degraded when vega is present)."),
    ("Risk-neutral ORE valuation/exposure", MODEL, "Using ORE exposure as a real-world loss forecast mixes measures."),
    ("Preserve ORE column names and sign conventions", DATA, "Adding netting-set and trade rows double counts exposure."),
    ("No-error execution does not establish calibration", MODEL, "None; a successful ORE run is not model validation."),
]

# Interpretations and choices stated in the code and the skill references, beyond the returned lists.
# (id, models, class, statement, code, reference, evidence and status, consequence if wrong)
INTERPRETATIONS = [
    ("I01", "M24", REG, "MAR33.6 floor of ES_F,C / ES_R,C at 1 applied to every risk-class ratio in MAR33.15, not only the portfolio ratio.",
     "src/riskdesk/frtb.py:86-95, 101", "risk-frtb/reference.md:43-47",
     "Arithmetic agrees with the reading: research/math-review/frtb check imcc, where the interest-rate class floor binds. Whether MAR33.15 intends it is UNPROVEN: the MAR33.15 FAQ formulas could not be read (reference.md:45-47).",
     "If no class floor is intended, IMCC is overstated (conservative) where a class ratio is below 1."),
    ("I02", "M27", REG, "MAR32.19 desk limits read as 'more than 12' at 99% and 'more than 30' at 97.5%: a desk passes at 12 and 30.",
     "src/riskdesk/frtb.py:32, 263-265", "risk-frtb/reference.md:91-99",
     "Boundary behaviour checked: research/math-review/frtb desk-limit-99-12/13 and desk-limit-975-30/31. The reading is supported by EU CRR Art 325bf(3) as read by the engineers (reference.md:95-99); the engineers note the BIS sentence can be read either way.",
     "If '30 exceptions' means 30 or more, a desk with exactly 30 at 97.5% passes here and should not."),
    ("I03", "M17, M16", MODEL, "Lehman window ends 2008-10-31 by library convention; the BIS source says only 'late October'.",
     "src/riskdesk/scenarios.py:116-123", "risk-stress/reference.md:62-76",
     "Stated as a convention in the code reason text and in reference.md; tests/test_stress_scenarios.py test_the_library_dates_are_the_ones_cited_in_reference_md guards the dates against reference.md, not against the source.",
     "A different end date gives a different replayed shock; the caller can replay any window."),
    ("I04", "M15", MODEL, "L-VaR = historical VaR + total cost of liquidity, a plain sum. The form is confirmed only from a secondary source (Qi and Ng 2009); the copy of Bangia et al. read ends before its L-VaR equation.",
     "src/riskdesk/liquidity.py:77", "risk-liquidity/reference.md:57-73",
     "The module computes the additive form: research/math-review/liquidity lvar-additive. That the form is Bangia et al.'s is UNPROVEN.",
     "If the paper applies a correlation correction, L-VaR here differs from the paper's figure."),
    ("I05", "M20", REG, "SA-CCR FX (CRE52.59) and equity (CRE52.66) add-ons have no published worked example. Maintainer decision relayed on 2026-11-04: ship in v0.2 as partially verified, constants checked against CRE52.72.",
     "src/riskdesk/counterparty.py:23-24, 29, 193-218", "risk-counterparty/reference.md:50-51, 59-75, 80-88",
     "Hand checks only: tests/test_counterparty.py test_fx_hedging_sets_offset_within_a_pair_only and test_equity_single_factor_aggregation_by_hand; research/math-review/counterparty fx-no-published-example and equity-no-published-example (first principles, same reading of the text). PARTIALLY VERIFIED.",
     "A misreading of CRE52.59 or CRE52.66 shared by the code and the hand checks would go undetected."),
    ("I06", "M20", REG, "Negative-rate options: P and K are both shifted by a caller-supplied lambda (CRE52.40 FAQ2); the shift is accepted for interest rate options only.",
     "src/riskdesk/counterparty.py:52, 91-95, 142", "risk-counterparty/reference.md:43",
     "Arithmetic agrees with the reading: tests/test_counterparty.py test_negative_rate_option_uses_the_faq2_shift; research/math-review/counterparty negative-rate-shift. The FAQ text was read from bis.org images by the engineers, not in this review: UNPROVEN beyond that reading.",
     "If FAQ2 prescribes lambda or applies to other classes, the supervisory delta differs."),
    ("I07", "M20", REG, "CRE52.2 cap: the margined EAD is capped at the same netting set recomputed with unmargined maturity factors and unmargined replacement cost, keeping V and C.",
     "src/riskdesk/counterparty.py:272-278", "risk-counterparty/reference.md:97-98",
     "Arithmetic agrees with the reading where the cap binds: research/math-review/counterparty margined-cap-binding; tests/test_counterparty.py test_margined_ead_is_capped_at_the_unmargined_ead. The reading itself is an implementer's choice (reference.md:95).",
     "Another reading of 'calculated on an unmargined basis' changes EAD only where the cap binds."),
    ("I08", "M05", MODEL, "The Z2 p-value is simulated under a location-scale normal or Student-t null that reproduces each day's VaR and ES forecast; the bank's own forecast distribution is not used.",
     "src/riskdesk/backtest.py:85-108", "risk-backtest/reference.md:72-89",
     "The simulation is reproduced by an independent 20,000-draw simulation within four standard errors: research/math-review/backtest z2-p-normal-null. Calibration against other forecast distributions is UNPROVEN (reference.md:87-89 records one measured run, not a test).",
     "If the true forecast distribution is not in the stated family, the p-value is miscalibrated."),
    ("I09", "M04", MODEL, "The three GARCH columns depend on Option Desk's Bayesian GARCH(1,1)-t converging; non-convergence marks the result degraded but still returns the columns.",
     "src/riskdesk/tail_models.py:96-127", "risk-tail/reference.md:70-96",
     "Observed in this review: on a seeded i.i.d. t(4) sample of 1,000 the posterior did not converge, and the result was flagged degraded as designed (research/math-review/tail garch-nonconvergence-flagged). The filter arithmetic matches a hand recursion (garch-sigma-next).",
     "A reader who ignores the degraded flag uses GARCH columns from an unconverged posterior."),
    ("I10", "M01", MODEL, "At an exactly integral tail mass, the confidence passed to skfolio is moved one float towards 1 so binary rounding cannot select the next order statistic.",
     "src/riskdesk/analytics.py:32-40", "risk-tail/reference.md:15-18",
     "tests/test_risk.py test_exact_integer_tail_boundary_is_not_shifted_by_float_rounding; research/math-review/tail hs-var-n20-q0.95 (exact boundary) agrees with a hand order statistic.",
     "Without the adjustment, VaR at boundaries such as n=20, q=0.95 selects the wrong observation."),
    ("I11", "M05", REG, "The Basel traffic light is reported only for 99% one-day VaR, over all rows supplied, with zone starts computed for that row count (MAR99.17).",
     "src/riskdesk/backtest.py:73-77, 119-122", "risk-backtest/reference.md:44-59",
     "Zones and boundaries for T = 250, 500, 1000 agree with exact binomial sums: research/math-review/backtest basel-*. The MAR99 Table 2 figures are as transcribed in reference.md; not re-read in this review.",
     "Applying Basel zones to other confidences or horizons would be unsupported; the module withholds the zone and says why."),
    ("I12", "M05", MODEL, "Z2 is taken from MathWorks documentation citing Acerbi and Szekely (2014); the paper text was not read and its zone cut-offs are not used.",
     "src/riskdesk/backtest.py:80-82", "risk-backtest/reference.md:61-70, 91-92",
     "Z2 arithmetic matches a hand loop: research/math-review/backtest z2. Fidelity to the paper is UNPROVEN.",
     "If the paper's statistic differs from the MathWorks statement, Z2 differs."),
    ("I13", "M20", REG, "Interest rate hedging sets use the CRE52.57 step 5 offset formula only; the no-offset alternative is not offered.",
     "src/riskdesk/counterparty.py:180-192", "risk-counterparty/reference.md:101-102",
     "CRE99 examples 1, 4 and 5 reproduce with it (research/math-review/counterparty example-*-published).",
     "A bank that elects no offset gets a lower add-on here than its own."),
    ("I14", "M20", MODEL, "With an aggregate add-on of zero, PFE is zero and the multiplier is reported as its limit (1, or 5% when V - C is negative).",
     "src/riskdesk/counterparty.py:244-250", "risk-counterparty/reference.md:99-100",
     "UNGUARDED: no test in tests/test_counterparty.py exercises a zero aggregate add-on (searched 2026-11-04), and research/math-review does not either. UNPROVEN.",
     "None for EAD; only the reported multiplier is a convention."),
    ("I15", "M20", REG, "CRE52.57 step 3 buckets: an end date of exactly 1 or exactly 5 years falls in the middle bucket.",
     "src/riskdesk/counterparty.py:183", "risk-counterparty/reference.md:54-55",
     "tests/test_counterparty.py test_floors_and_maturity_buckets.",
     "Trades ending exactly on a boundary would move bucket under another reading."),
    ("I16", "M21", REG, "EPE and Effective EPE average over exactly one year (CRE50.30); ORE's own cut-off is one year plus four days.",
     "src/riskdesk/counterparty.py:328-334", "risk-counterparty/reference.md:111-118, 132-133",
     "tests/test_counterparty.py test_profile_summary_by_hand and test_grid_without_a_one_year_date_is_degraded. No independent check in research/math-review: UNPROVEN beyond the tests.",
     "Figures differ from ORE's own Basel EPE where a grid date falls inside those four days."),
    ("I17", "M25", REG, "MAR33.41 prose says 'weighted average' while its formula shows an average; the 60-day averages are inputs and the module takes no position.",
     "src/riskdesk/frtb.py:157", "risk-frtb/reference.md:51-55",
     "Not testable here: the averages are supplied.",
     "A caller who supplies the wrong kind of average gets a wrong C_A."),
    ("I18", "M28", REG, "MAR21.88 specified pairs and first-order crosses: the reduction applies when both currencies are in the footnote 22 list or are USD.",
     "src/riskdesk/frtb.py:43, 356-358", "risk-frtb/reference.md:147-153",
     "tests/test_frtb.py test_specified_pair_reduction_follows_mar21_88; research/math-review/frtb sbm-fx-capital-reduce-True.",
     "A narrower reading of 'first-order cross' would remove the sqrt(2) reduction for some pairs."),
    ("I19", "M26", REG, "PLA Spearman tie handling: average ranks (scipy); MAR32.36-38 do not specify ties.",
     "src/riskdesk/frtb.py:203", "risk-frtb/reference.md:106-108",
     "research/math-review/frtb pla-spearman-* with own average-rank implementation on rounded (tied) P&L.",
     "Another tie rule moves Spearman when P&L values repeat, possibly across a zone threshold."),
    ("I20", "M06, M07, M08", MODEL, "Black-76 rho is reported as -t x V with the future held fixed. The text says the engine's black76_greeks rho is wrong and is not used.",
     "src/riskdesk/derivatives.py:6-8, 155, 186", "risk-derivatives/reference.md:31-37",
     "STALE TEXT. Option Desk commit 4a282d9 (git show --stat: engine/src/optiondesk_engine/pricing/forwards.py and engine/tests/test_forwards.py) sets the engine's rho to -t x price; the installed engine returned -9.226412244425209 = -tV at F=100, K=95, t=0.75, vol 0.3, r=0.05 on 2026-11-04. The values are unchanged and agree with a finite difference (research/math-review/derivatives rho-future-*). The integrator is removing the Risk Desk workaround.",
     "None for the numbers; the docstring, CONVENTIONS and reference.md now state an engine defect that no longer exists."),
    ("I21", "M04", MODEL, "EVT threshold fraction fixed at k = floor(0.10 n), from McNeil and Frey's k = 100 for n = 1000; k below 50 is flagged.",
     "src/riskdesk/tail_models.py:16-19, 38-53, 128-131", "risk-tail/reference.md:42-68",
     "EVT quantile inverts eq. (9) and ES matches integration of the GPD survival: research/math-review/tail evt-*.",
     "Another threshold choice changes the EVT columns materially on small samples."),
    ("I22", "M04", MODEL, "No published source is cited for filtered historical simulation or for the Student-t ES formula.",
     "src/riskdesk/tail_models.py:30-35, 108", "risk-tail/reference.md:98-101",
     "Student-t ES agrees with numerical integration of the fitted density: research/math-review/tail student-t-es-integral.",
     "None for the arithmetic; the method has no cited authority."),
    ("I23", "M05", MODEL, "Kupiec (1995) and Christoffersen (1998) are cited bibliographically; the paper texts were not read.",
     "src/riskdesk/backtest.py:52-70", "risk-backtest/reference.md:14-15, 25-26",
     "Statistics agree with hand likelihood ratios: research/math-review/backtest kupiec-*, christoffersen-*.",
     "If the papers' statistics differ from the textbook form used, the tests differ."),
    ("I24", "M20", DATA, "The CRE99 SA-CCR example EADs are images on bis.org; the published figures used are the engineers' transcription in reference.md.",
     "tests/test_counterparty.py:31-52", "risk-counterparty/reference.md:80-93",
     "An independent CRE52 recomputation reproduces all five transcribed EADs to whole thousands (research/math-review/counterparty example-*-published). A web fetch on 2026-11-04 confirmed the EAD values are images and could not read them: the transcription is UNPROVEN by this review.",
     "A transcription error shared by tests and review would go undetected."),
    ("I25", "M22", MODEL, "The ASRF correlation R is a caller input; the CRE31.5 supervisory corporate correlation appears only in the tests and the review as a reference.",
     "src/riskdesk/credit.py:63-73", "risk-credit/reference.md:48-53",
     "CRE99 Table 1 (read from bis.org on 2026-11-04) reproduced for all 18 PDs: research/math-review/credit rw-*.",
     "A caller who supplies a non-supervisory R gets an economic, not a regulatory, figure."),
]


def cell(text):
    return text.replace("|", "\\|")


def render():
    found = extract()
    rows, used = [], set()
    for text, models in found.items():
        matches = [entry for entry in CLASSIFICATION if entry[0] in text]
        if len(matches) != 1:
            raise SystemExit(f"{len(matches)} classification entries match: {text}")
        used.add(matches[0][0])
        rows.append((", ".join(sorted(models)), matches[0][1], text, matches[0][2]))
    unused = [entry[0] for entry in CLASSIFICATION if entry[0] not in used]
    if unused:
        raise SystemExit(f"classification entries match no returned assumption: {unused}")
    lines = ["# Assumptions register", "",
             "Generated by `python docs/models/build_assumptions.py`; do not edit by hand. Model ids are those of "
             "[INVENTORY.md](INVENTORY.md).", "",
             "Part A is extracted programmatically: every text below is returned verbatim in the `assumptions` list "
             "of the named functions, collected by calling them on the inputs listed under Extraction. The class and "
             "the consequence are this register's reading. Part B records interpretations and choices stated in the "
             "code and the skill references that the returned lists do not carry, each with its evidence.", "",
             f"Part A: {len(rows)} distinct returned assumptions. Part B: {len(INTERPRETATIONS)} interpretations.", "",
             "## Part A: returned assumptions", "",
             "| # | Models | Class | Assumption (verbatim) | Consequence if wrong |", "|---|---|---|---|---|"]
    lines += [f"| A{i:03d} | {m} | {c} | {cell(t)} | {cell(q)} |" for i, (m, c, t, q) in enumerate(rows, 1)]
    lines += ["", "## Part B: interpretations and choices", "",
              "| Id | Models | Class | Interpretation | Code | Reference | Evidence and status | Consequence if wrong |",
              "|---|---|---|---|---|---|---|---|"]
    lines += ["| " + " | ".join(cell(x) for x in row) + " |" for row in INTERPRETATIONS]
    lines += ["", "## Extraction", "",
              "| Model | Function | Input |", "|---|---|---|"]
    lines += [f"| {m} | `{fn.__module__}.{fn.__name__}` | {how} |" for m, fn, _, how in CALLS]
    lines += ["| M29 | `riskdesk.ore.run_ore` | literal `assumptions` list in src/riskdesk/ore.py, read by AST "
              "(running ORE needs the ORE binary) |",
              "| M17 | `riskdesk.scenarios.scenario_library` | returns no envelope and no assumptions list "
              "(src/riskdesk/scenarios.py:148-152); its date conventions are I03 |", "",
              "Conditional assumptions were reached by the variant inputs above: the decay and fixed time modes "
              "(src/riskdesk/derivatives.py:262-263), the worst peak-to-trough measure (src/riskdesk/scenarios.py:95-99) "
              "and the margined cap note (src/riskdesk/counterparty.py:272-278). Every other function returns a fixed "
              "list."]
    OUT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return len(rows)


if __name__ == "__main__":
    print(f"wrote {OUT.relative_to(ROOT)}: {render()} returned assumptions, {len(INTERPRETATIONS)} interpretations")
