"""FRTB market risk capital (Basel Framework MAR21, MAR32, MAR33).

Constants are quoted from the BIS consolidated Basel Framework, read on
2026-11-04: MAR21 in force 2023-01-01, published 2026-03-23; MAR32 in force
2023-01-01, published 2020-03-27; MAR33 in force 2023-01-01, published
2020-06-05. Every constant names its paragraph. Inputs are figures the caller
computed (ES, P&L, VaR, sensitivities, standardised charges); nothing here
estimates a risk measure from market data.
"""
import math
from typing import Annotated, Literal

import numpy as np
from pydantic import Field, model_validator
from scipy.stats import ks_2samp, spearmanr

from riskdesk.analytics import envelope
from riskdesk.models import Provenance, StrictModel

NonNegative = Annotated[float, Field(ge=0)]

# MAR33.4 Table 1: liquidity horizons LH_j, j = 1..5, and base horizon T = 10 days.
LIQUIDITY_HORIZONS = (10, 20, 40, 60, 120)
BASE_HORIZON = 10
RHO_IMCC = 0.5           # MAR33.15: relative weight of the unconstrained ES.
MULTIPLIER_FLOOR = 1.5   # MAR33.42: m_c fixed at 1.5 before add-ons.
# MAR32.9 Table 1: backtesting dependent multiplier by bank-wide 99% exceptions over 250 observations.
BACKTEST_MULTIPLIER = {5: 1.70, 6: 1.76, 7: 1.83, 8: 1.88, 9: 1.92}
SURCHARGE_K = 0.5        # MAR33.45: k = 0.5 x amber SA share.
RWA_FACTOR = 12.5        # MAR33.46.
OBSERVATIONS = 250       # MAR32.3 (12 months, ie 250 trading days) and MAR32.35.
DESK_LIMIT_99, DESK_LIMIT_975 = 12, 30  # MAR32.19.
# MAR32.42 Table 2. KS thresholds are held as counts of 0.004 (MAR32.39-41) so boundaries are exact.
PLA_GREEN_RHO, PLA_RED_RHO = 0.80, 0.70
PLA_GREEN_KS_COUNT, PLA_RED_KS_COUNT = 22.5, 30   # 0.09 and 0.12 divided by 0.004.

FX_DELTA_RW = 0.15       # MAR21.87.
FX_GAMMA = 0.60          # MAR21.89; MAR21.95 applies it to vega too.
FX_VEGA_RW = 1.0         # MAR21.92 Table 13, FX: liquidity horizon 40, risk weight 100%.
VEGA_ALPHA = 0.01        # MAR21.93: alpha set at 1%.
VEGA_TENORS = (0.5, 1.0, 3.0, 5.0, 10.0)  # MAR21.14(2).
# MAR21.88 footnote 22: pairs against USD; any two of these form a first-order cross (footnote 23).
SPECIFIED_FX = frozenset("USD EUR JPY GBP AUD CAD CHF MXN CNY NZD RUB HKD SGD TRY KRW SEK ZAR INR NOK BRL".split())


def _refuse_non_finite(values, what):
    if not all(math.isfinite(v) for v in values):
        raise ValueError(what + " exceeded numerical limits")


def _fsum(values):
    """math.fsum raises OverflowError on an infinite sum; the contract is ValueError."""
    try:
        return math.fsum(values)
    except OverflowError:
        raise ValueError("a sum exceeded numerical limits") from None


# ---------------------------------------------------------------- MAR33 IMA

Cascade = Annotated[list[NonNegative], Field(min_length=5, max_length=5)]


class EsSet(StrictModel):
    """Each cascade is ES_T(P, j) for j = 1..5 at the 10-day base horizon;
    element 0 is ES_T(P) over all risk factors (MAR33.4)."""
    reduced_stressed: Cascade
    full_current: Cascade
    reduced_current: Cascade


class ImccRequest(Provenance):
    base_horizon_days: Literal[10]
    portfolio: EsSet
    risk_classes: dict[Literal["interest_rate", "equity", "fx", "commodity", "credit_spread"], EsSet] = Field(min_length=1)


def liquidity_adjusted_es(cascade):
    """MAR33.4: ES = sqrt(ES_T(P)^2 + sum_{j>=2} (ES_T(P,j) sqrt((LH_j - LH_{j-1})/T))^2)."""
    # hypot is sqrt of the sum of squares without overflowing on the intermediate squares.
    return math.hypot(cascade[0], *(
        cascade[j] * math.sqrt((LIQUIDITY_HORIZONS[j] - LIQUIDITY_HORIZONS[j - 1]) / BASE_HORIZON)
        for j in range(1, 5)))


def _scaled_es(es_set, label):
    """MAR33.6: ES_R,S x ES_F,C / ES_R,C with the ratio floored at 1."""
    rs, fc, rc = (liquidity_adjusted_es(c) for c in (es_set.reduced_stressed, es_set.full_current, es_set.reduced_current))
    _refuse_non_finite([rs, fc, rc], label + " liquidity-adjusted ES")  # inf / inf is NaN, and max(1.0, NaN) is 1.0
    if rc == 0:
        raise ValueError(label + ": reduced-set current ES is zero, so the MAR33.6 ratio is undefined")
    ratio = fc / rc
    floored = max(1.0, ratio)
    return dict(es_reduced_stressed=rs, es_full_current=fc, es_reduced_current=rc,
                ratio=ratio, ratio_floored=floored, imcc=rs * floored)


def frtb_imcc(payload):
    request = ImccRequest.model_validate(payload)
    portfolio = _scaled_es(request.portfolio, "portfolio")
    classes = {name: _scaled_es(es_set, name) for name, es_set in request.risk_classes.items()}
    constrained = _fsum(c["imcc"] for c in classes.values())
    imcc = RHO_IMCC * portfolio["imcc"] + (1 - RHO_IMCC) * constrained
    _refuse_non_finite([imcc, constrained, portfolio["imcc"]], "IMCC")
    result = envelope(request, "FRTB IMA liquidity-adjusted, stress-calibrated ES and IMCC (MAR33.4, MAR33.6, MAR33.15)", [
        "Inputs are 10-day ES values per liquidity-horizon subset Q(p,j), computed by the caller at 97.5% (MAR33.3); no ES is estimated here.",
        "MAR33.6 floors ES_F,C / ES_R,C at 1. The same floor is applied to each risk-class ratio in MAR33.15; the text states the floor once, for the ES used for capital.",
        "Risk classes not supplied contribute nothing to the constrained sum; supply every broad class with exposure (MAR33.14).",
        "The stress period for each class must be the portfolio-wide one (MAR33.15); this is the caller's responsibility and is not checked.",
        "Amounts are positive losses in the stated currency; no non-modellable (SES) or default (DRC) capital is included here."])
    result.update(base_horizon_days=BASE_HORIZON, liquidity_horizons=list(LIQUIDITY_HORIZONS), rho=RHO_IMCC,
                  portfolio=portfolio, risk_classes=classes, imcc_unconstrained=portfolio["imcc"],
                  imcc_constrained_sum=constrained, imcc=imcc)
    return result


class DeskStandardised(StrictModel):
    desk: str = Field(min_length=1)
    pla_zone: Literal["green", "amber"]
    sa: NonNegative


class ImaCapitalRequest(Provenance):
    imcc_latest: NonNegative
    ses_latest: NonNegative
    imcc_average_60d: NonNegative
    ses_average_60d: NonNegative
    bankwide_backtesting_exceptions: int = Field(ge=0, le=OBSERVATIONS, strict=True)
    qualitative_addon: NonNegative
    drc_latest: NonNegative
    drc_average_12w: NonNegative
    desks: list[DeskStandardised] = Field(min_length=1, max_length=10_000)
    sa_green_amber: NonNegative
    sa_out_of_scope: NonNegative
    sa_all_desks: NonNegative

    @model_validator(mode="after")
    def unique_desks(self):
        if len({d.desk for d in self.desks}) != len(self.desks):
            raise ValueError("desk names must be unique")
        return self


def backtesting_multiplier(exceptions):
    """MAR32.9 Table 1: green 0-4 -> 1.50, amber 5-9 -> 1.70..1.92, red 10 or more -> 2.00."""
    if exceptions <= 4:
        return "green", MULTIPLIER_FLOOR
    if exceptions <= 9:
        return "amber", BACKTEST_MULTIPLIER[exceptions]
    return "red", 2.00


def frtb_ima_capital(payload):
    request = ImaCapitalRequest.model_validate(payload)
    zone, table_multiplier = backtesting_multiplier(request.bankwide_backtesting_exceptions)
    m_c = table_multiplier + request.qualitative_addon
    c_a = max(request.imcc_latest + request.ses_latest, m_c * request.imcc_average_60d + request.ses_average_60d)  # MAR33.41
    drc = max(request.drc_average_12w, request.drc_latest)  # MAR33.22
    ima_ga = c_a + drc  # MAR33.43
    amber = _fsum(d.sa for d in request.desks if d.pla_zone == "amber")
    total_sa = _fsum(d.sa for d in request.desks)
    if amber > 0 and total_sa == 0:
        raise ValueError("desk standardised charges sum to zero, so k in MAR33.45 is undefined")
    k = SURCHARGE_K * amber / total_sa if amber > 0 else 0.0
    surcharge = k * max(0.0, request.sa_green_amber - ima_ga)  # MAR33.45
    acr = min(ima_ga + surcharge + request.sa_out_of_scope, request.sa_all_desks) + max(0.0, ima_ga - request.sa_green_amber)  # MAR33.43
    _refuse_non_finite([c_a, ima_ga, surcharge, acr, acr * RWA_FACTOR], "aggregate capital")
    result = envelope(request, "FRTB IMA capital aggregation (MAR33.41 to MAR33.46, MAR32.9)", [
        "IMCC, SES, DRC and every standardised charge are supplied by the caller; the 60-day and 12-week averages are taken as given.",
        "m_c is the MAR32.9 table value for the bank-wide 99% exception count over 250 days plus the supervisor's qualitative add-on (MAR33.42).",
        "The multiplier applies to the 60-day IMCC average only, as written in MAR33.41; SES enters unscaled.",
        "k uses the sum of desk-level standardised charges; SA_G,A is the standardised charge on the combined green and amber positions (MAR33.45).",
        "The 10% eligibility criterion of MAR32.2 is not tested."])
    result.update(backtesting_zone=zone, backtesting_multiplier=table_multiplier, multiplier=m_c, c_a=c_a, drc=drc,
                  ima_green_amber=ima_ga, k=k, capital_surcharge=surcharge, aggregate_capital=acr,
                  rwa=acr * RWA_FACTOR, amber_desks=sorted(d.desk for d in request.desks if d.pla_zone == "amber"))
    return result


# ---------------------------------------------------------------- MAR32 tests

Series = Annotated[list[float], Field(min_length=OBSERVATIONS, max_length=OBSERVATIONS)]
GappySeries = Annotated[list[float | None], Field(min_length=OBSERVATIONS, max_length=OBSERVATIONS)]


class PlaRequest(Provenance):
    desk: str = Field(min_length=1)
    rtpl: Series
    hpl: Series


def pla_zone(spearman, ks_count):
    """MAR32.42: green needs both metrics inside; red if either is outside the red threshold."""
    if spearman > PLA_GREEN_RHO and ks_count < PLA_GREEN_KS_COUNT:
        return "green"
    if spearman < PLA_RED_RHO or ks_count > PLA_RED_KS_COUNT:
        return "red"
    return "amber"


def frtb_pla(payload):
    request = PlaRequest.model_validate(payload)
    rho = float(spearmanr(request.rtpl, request.hpl).statistic)
    if not math.isfinite(rho):
        raise ValueError("Spearman correlation is undefined, for example for a constant P&L series")
    # MAR32.39-41 use 0.004 per observation; with exactly 250 that is scipy's 1/n, so the count is an integer.
    ks_count = round(float(ks_2samp(request.rtpl, request.hpl).statistic) * OBSERVATIONS)
    zone = pla_zone(rho, ks_count)
    result = envelope(request, "FRTB P&L attribution test (MAR32.34 to MAR32.42)", [
        "RTPL and HPL are the desk's most recent 250 daily observations, oldest first, in the stated currency (MAR32.35).",
        "Spearman uses scipy average ranks for ties; MAR32.36-38 do not specify tie handling.",
        "KS is the largest gap between the two empirical distributions with 0.004 per observation (MAR32.39-41).",
        "Zone exit rules of MAR32.43-44 depend on history and backtesting and are not applied here."])
    result.update(desk=request.desk, horizon_days=1, observations=OBSERVATIONS, spearman=rho,
                  ks=ks_count / OBSERVATIONS, ks_count=ks_count, zone=zone,
                  thresholds=dict(green_spearman_above=PLA_GREEN_RHO, red_spearman_below=PLA_RED_RHO,
                                  green_ks_below=0.09, red_ks_above=0.12))
    return result


class BacktestRequest(Provenance):
    level: Literal["desk", "bank"]
    apl: GappySeries
    hpl: GappySeries
    var_99: GappySeries
    var_975: GappySeries | None = None

    @model_validator(mode="after")
    def var_levels(self):
        if self.level == "desk" and self.var_975 is None:
            raise ValueError("desk-level backtesting needs var_975 as well as var_99 (MAR32.18)")
        if self.level == "bank" and self.var_975 is not None:
            raise ValueError("bank-wide backtesting is at 99% only (MAR32.5); omit var_975")
        if any(v is not None and v < 0 for v in self.var_99 + (self.var_975 or [])):
            raise ValueError("VaR is a positive loss amount; negative VaR values are refused")
        return self


def count_exceptions(pnl, var):
    """MAR32.5 and MAR32.18: an exception is a loss above VaR; a missing P&L or VaR counts as one."""
    return sum(1 for p, v in zip(pnl, var) if p is None or v is None or -p > v)


def _exceptions(request, var):
    apl, hpl = count_exceptions(request.apl, var), count_exceptions(request.hpl, var)
    return dict(apl=apl, hpl=hpl, overall=max(apl, hpl))


def frtb_backtest(payload):
    request = BacktestRequest.model_validate(payload)
    result = envelope(request, "FRTB VaR backtesting exception count (MAR32.5, MAR32.9, MAR32.18, MAR32.19)", [
        "P&L is signed profit; VaR is a positive one-day loss; an exception is a loss strictly greater than VaR.",
        "Actual and hypothetical exceptions are counted separately and the greater is used.",
        "A missing P&L or VaR on a day counts as an exception.",
        "The 250 observations are the most recent 12 months (MAR32.3); NMRF-driven exceptions are not disregarded here (MAR32.6)."])
    result.update(level=request.level, horizon_days=1, observations=OBSERVATIONS,
                  exceptions_99=_exceptions(request, request.var_99))
    if request.level == "bank":
        zone, multiplier = backtesting_multiplier(result["exceptions_99"]["overall"])
        result.update(zone=zone, backtesting_multiplier=multiplier)
    else:
        result["exceptions_975"] = _exceptions(request, request.var_975)
        # MAR32.19 reads "more than 12 ... or 30"; EU CRR Art 325bf(3) states "no more than" both limits.
        result["passes"] = (result["exceptions_99"]["overall"] <= DESK_LIMIT_99
                            and result["exceptions_975"]["overall"] <= DESK_LIMIT_975)
    return result


# ---------------------------------------------------------------- MAR21 SBM, FX

class FxDelta(StrictModel):
    currency: str = Field(pattern=r"^[A-Z]{3}$")
    sensitivity: float


class FxVega(StrictModel):
    currency: str = Field(pattern=r"^[A-Z]{3}$")
    option_maturity_years: float
    sensitivity: float

    @model_validator(mode="after")
    def tenor(self):
        if self.option_maturity_years not in VEGA_TENORS:
            raise ValueError("option maturity must be mapped to 0.5, 1, 3, 5 or 10 years (MAR21.14(2))")
        return self


class FxSbmRequest(Provenance):
    """`currency` is the reporting currency; each bucket is one currency against it (MAR21.86)."""
    apply_specified_pair_reduction: bool
    delta: list[FxDelta] = Field(max_length=100_000)
    vega: list[FxVega] = Field(max_length=100_000)

    @model_validator(mode="after")
    def non_empty_and_foreign(self):
        if not self.delta and not self.vega:
            raise ValueError("supply at least one delta or vega sensitivity")
        if any(s.currency == self.currency for s in self.delta + self.vega):
            raise ValueError("a sensitivity cannot be to the reporting currency itself")
        return self


def scenario_correlation(rho, scenario):
    """MAR21.6: high multiplies by 1.25 capped at 100%; low is max(2 rho - 100%, 75% rho)."""
    if scenario == "high":
        return np.minimum(1.25 * rho, 1.0)
    if scenario == "low":
        return np.maximum(2 * rho - 1, 0.75 * rho)
    return rho


def bucket_position(ws, rho):
    """MAR21.4(4): K_b = sqrt(max(0, sum WS_k^2 + sum_{k != l} rho_kl WS_k WS_l)); rho has a unit diagonal."""
    return math.sqrt(max(0.0, float(ws @ rho @ ws)))


def across_buckets(k, s, gamma):
    """MAR21.4(5): sqrt(sum K_b^2 + sum_{b != c} gamma_bc S_b S_c), with the (5)(b) fallback
    S_b = max(min(S_b, K_b), -K_b) when the sum is negative. gamma has a zero diagonal."""
    total = float(k @ k + s @ gamma @ s)
    alternative = total < 0
    if alternative:
        s = np.clip(s, -k, k)
        total = float(k @ k + s @ gamma @ s)
    _refuse_non_finite([total], "across-bucket aggregation")
    if total < 0:
        raise ValueError("across-bucket aggregation is negative even under MAR21.4(5)(b)")
    return math.sqrt(total), alternative


def _aggregate(buckets, scenario):
    """buckets: list of (weighted sensitivities, within-bucket correlation with unit diagonal); FX gamma is uniform.
    Both MAR21.6 transforms map a unit diagonal to itself, so the diagonal needs no reset."""
    k = np.array([bucket_position(ws, scenario_correlation(rho, scenario)) for ws, rho in buckets])
    s = np.array([float(ws.sum()) for ws, _ in buckets])
    gamma = np.full((len(buckets), len(buckets)), float(scenario_correlation(FX_GAMMA, scenario)))
    np.fill_diagonal(gamma, 0.0)
    charge, alternative = across_buckets(k, s, gamma)
    return charge, alternative, k, s


def _net(entries, key):
    netted = {}
    for entry in entries:
        netted.setdefault(key(entry), []).append(entry.sensitivity)
    return {k: _fsum(v) for k, v in sorted(netted.items())}


def frtb_sbm_fx(payload):
    request = FxSbmRequest.model_validate(payload)
    reporting = request.currency
    delta = _net(request.delta, lambda e: e.currency)  # MAR21.4(2): net per risk factor.
    vega = _net(request.vega, lambda e: (e.currency, e.option_maturity_years))
    _refuse_non_finite(list(delta.values()) + list(vega.values()), "net sensitivity")

    def delta_rw(ccy):
        reduced = request.apply_specified_pair_reduction and {ccy, reporting} <= SPECIFIED_FX  # MAR21.88
        return FX_DELTA_RW / math.sqrt(2) if reduced else FX_DELTA_RW

    delta_buckets = [(np.array([s * delta_rw(c)]), np.ones((1, 1))) for c, s in delta.items()]
    vega_ccys = sorted({c for c, _ in vega})
    vega_buckets = []
    for ccy in vega_ccys:
        tenors = [t for c, t in vega if c == ccy]
        ws = np.array([vega[(ccy, t)] * FX_VEGA_RW for t in tenors])
        # MAR21.94: rho = min(rho_delta x exp(-alpha |Tk-Tl| / min(Tk,Tl)), 1); one FX delta factor per bucket, so rho_delta = 1.
        rho = np.array([[min(math.exp(-VEGA_ALPHA * abs(a - b) / min(a, b)), 1.0) for b in tenors] for a in tenors])
        vega_buckets.append((ws, rho))

    scenarios = {}
    for name in ("low", "medium", "high"):
        row = dict(delta=0.0, vega=0.0, delta_alternative=False, vega_alternative=False)
        if delta_buckets:
            row["delta"], row["delta_alternative"], _, _ = _aggregate(delta_buckets, name)
        if vega_buckets:
            row["vega"], row["vega_alternative"], vk, vs = _aggregate(vega_buckets, name)
            row["vega_buckets"] = {c: dict(k=float(a), s=float(b)) for c, a, b in zip(vega_ccys, vk, vs)}
        row["total"] = row["delta"] + row["vega"]
        scenarios[name] = row
    binding = max(scenarios, key=lambda n: scenarios[n]["total"])  # MAR21.7: largest of the three scenario totals.
    _refuse_non_finite([r["total"] for r in scenarios.values()], "SBM capital")
    warnings = (["Vega sensitivities imply optionality, which MAR21.2 also subjects to curvature risk; curvature is not computed, so this understates the SBM charge."]
                if vega else [])
    result = envelope(request, "FRTB SA sensitivities-based method, FX delta and vega (MAR21.4, MAR21.6, MAR21.7, MAR21.86 to MAR21.95)", [
        "Sensitivities are supplied in the reporting currency as defined in MAR21.24 and MAR21.25; delta per 1% relative move, vega as vega times implied volatility.",
        "One bucket per currency against the reporting currency; delta risk weight 15%, divided by sqrt(2) for specified pairs and first-order crosses when the bank elects it.",
        "Vega risk weight 100% (MAR21.92 Table 13, FX); within-bucket vega correlation from option maturities (MAR21.93, MAR21.94).",
        "The capital requirement is the largest of the low, medium and high correlation totals; curvature, other risk classes, DRC and RRAO are not included."],
        warnings)
    result.update(reporting_currency=reporting, risk_class="fx",
                  delta_weighted_sensitivities={c: float(ws[0]) for c, (ws, _) in zip(delta, delta_buckets)},
                  scenarios=scenarios, binding_scenario=binding, capital=scenarios[binding]["total"])
    return result
