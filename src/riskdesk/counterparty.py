"""Counterparty credit exposure: SA-CCR exposure at default (Basel CRE52) and
Basel summaries of a simulated exposure profile (CRE50, CRE53).

Every supervisory constant below is quoted from the Basel Framework text on
bis.org; the paragraph is named beside it. Amounts are in the request
currency, times are in years from the as-of date.
"""
from collections import defaultdict
import math
import re
from typing import Literal

from pydantic import Field, model_validator
from scipy.stats import norm

from riskdesk.analytics import envelope
from riskdesk.models import Provenance, StrictModel

ALPHA = 1.4                  # CRE52.1
MULTIPLIER_FLOOR = 0.05      # CRE52.23
BUSINESS_DAYS_PER_YEAR = 250  # market convention given in CRE52.49 and CRE52.53
TEN_BUSINESS_DAYS = 10 / BUSINESS_DAYS_PER_YEAR  # floor on SD (CRE52.34) and M (CRE52.48)
IR_SF, FX_SF = 0.005, 0.04   # CRE52.72 Table 2 (also CRE52.57 step 6, CRE52.59 step 4)
IR_VOL, FX_VOL = 0.50, 0.15  # CRE52.72 Table 2, supervisory option volatility
# CRE52.72 Table 2: rating -> (supervisory factor, correlation, option volatility)
CREDIT = {"AAA": (0.0038, 0.5, 1.0), "AA": (0.0038, 0.5, 1.0), "A": (0.0042, 0.5, 1.0),
          "BBB": (0.0054, 0.5, 1.0), "BB": (0.0106, 0.5, 1.0), "B": (0.016, 0.5, 1.0),
          "CCC": (0.06, 0.5, 1.0), "IG": (0.0038, 0.8, 0.8), "SG": (0.0106, 0.8, 0.8)}
EQUITY = {False: (0.32, 0.5, 1.2), True: (0.20, 0.8, 0.75)}        # single name, index
COMMODITY = {True: (0.40, 0.4, 1.5), False: (0.18, 0.4, 0.7)}      # electricity, other types
COMMODITY_SETS = ("energy", "metals", "agricultural", "other")    # CRE52.45(5)


class SaccrTrade(StrictModel):
    id: str = Field(min_length=1)
    asset_class: Literal["interest_rate", "fx", "credit", "equity", "commodity"]
    notional: float = Field(gt=0)      # see contract: adjusted notional basis differs by class
    market_value: float                # signed value to the bank, part of V
    maturity: float = Field(gt=0, le=100)  # M_i in years (CRE52.31)
    position: Literal["long", "short"]     # long = bought for an option (CRE52.39, CRE52.40)
    hedging_set: str | None = None     # IR currency, FX currency pair, commodity hedging set
    reference: str | None = None       # credit or equity entity or index, commodity type
    start: float | None = Field(default=None, ge=0, le=100)  # S_i (IR and credit)
    end: float | None = Field(default=None, gt=0, le=100)    # E_i (IR and credit)
    rating: Literal["AAA", "AA", "A", "BBB", "BB", "B", "CCC", "IG", "SG"] | None = None
    index: bool = False                # credit or equity index
    electricity: bool = False          # commodity type is electricity
    option: Literal["call", "put"] | None = None
    underlying_price: float | None = None  # P_i (CRE52.40)
    strike: float | None = None            # K_i
    exercise: float | None = Field(default=None, gt=0, le=100)  # T_i in years
    shift: float = Field(default=0, ge=0)  # lambda for interest rate options (CRE52.40 FAQ2)

    @model_validator(mode="after")
    def class_fields(self):
        cls = self.asset_class
        dated = cls in ("interest_rate", "credit")
        if dated != (self.start is not None and self.end is not None):
            raise ValueError(f"trade {self.id}: start and end are required for interest rate "
                             "and credit trades and not accepted for other classes")
        if dated and self.end <= self.start:
            raise ValueError(f"trade {self.id}: end must be after start")
        patterns = {"interest_rate": r"[A-Z]{3}", "fx": r"[A-Z]{3}/[A-Z]{3}",
                    "commodity": "|".join(COMMODITY_SETS)}
        if (self.hedging_set is not None) != (cls in patterns) or (
                cls in patterns and not re.fullmatch(patterns[cls], self.hedging_set)):
            raise ValueError(f"trade {self.id}: hedging_set must be a currency for interest rate, "
                             "a pair such as EUR/USD for fx, one of energy, metals, agricultural, "
                             "other for commodity, and absent for credit and equity")
        if cls == "fx" and self.hedging_set[:3] == self.hedging_set[4:]:
            raise ValueError(f"trade {self.id}: an fx pair needs two currencies")
        if (self.reference is None) == (cls in ("credit", "equity", "commodity")) or (
                self.reference is not None and not self.reference.strip()):
            raise ValueError(f"trade {self.id}: reference names the credit or equity entity or "
                             "index, or the commodity type, and is not accepted for other classes")
        if cls == "credit":
            allowed = ("IG", "SG") if self.index else ("AAA", "AA", "A", "BBB", "BB", "B", "CCC")
            if self.rating not in allowed:
                raise ValueError(f"trade {self.id}: credit rating must be one of {allowed}")
        elif self.rating is not None:
            raise ValueError(f"trade {self.id}: rating applies to credit trades only")
        if self.index and cls not in ("credit", "equity"):
            raise ValueError(f"trade {self.id}: index applies to credit and equity only")
        if self.electricity and self.hedging_set != "energy":
            raise ValueError(f"trade {self.id}: electricity belongs to the energy hedging set")
        option_fields = (self.underlying_price, self.strike, self.exercise)
        if (self.option is None) != all(v is None for v in option_fields) or (
                self.option is not None and None in option_fields):
            raise ValueError(f"trade {self.id}: an option needs underlying_price, strike and "
                             "exercise; a non-option takes none of them")
        if self.shift and (self.option is None or cls != "interest_rate"):
            raise ValueError(f"trade {self.id}: shift applies to interest rate options only")
        if self.option is not None:
            if self.underlying_price + self.shift <= 0 or self.strike + self.shift <= 0:
                raise ValueError(f"trade {self.id}: price and strike plus shift must be positive")
            if self.exercise > self.maturity:
                raise ValueError(f"trade {self.id}: exercise date cannot be after maturity")
        return self


class SaccrRequest(Provenance):
    netting_set: str = Field(min_length=1)
    trades: list[SaccrTrade] = Field(min_length=1, max_length=100_000)
    collateral: float = 0.0            # C: haircut value of net collateral held (CRE52.10, 52.18)
    margined: bool = False
    threshold: float | None = Field(default=None, ge=0)                # TH (CRE52.18)
    minimum_transfer_amount: float | None = Field(default=None, ge=0)  # MTA (CRE52.18)
    nica: float | None = None                                          # NICA (CRE52.17)
    remargining_period_business_days: int | None = Field(default=None, ge=1, le=250, strict=True)
    mpor_business_days: int | None = Field(default=None, ge=1, le=250, strict=True)

    @model_validator(mode="after")
    def margin_terms(self):
        if len({t.id for t in self.trades}) != len(self.trades):
            raise ValueError("trade ids must be unique")
        terms = (self.threshold, self.minimum_transfer_amount, self.nica,
                 self.remargining_period_business_days, self.mpor_business_days)
        if self.margined and None in terms:
            raise ValueError("a margined netting set needs threshold, minimum_transfer_amount, "
                             "nica, remargining_period_business_days and mpor_business_days")
        if not self.margined and any(v is not None for v in terms):
            raise ValueError("margin terms apply to margined netting sets only")
        # CRE52.50(1)-(2): ten days for daily margining, nine plus the period otherwise.
        if self.margined and self.mpor_business_days < 9 + self.remargining_period_business_days:
            raise ValueError("mpor_business_days is below the CRE52.50 floor of nine business "
                             "days plus the remargining period")
        return self


def _parameters(trade):
    """(supervisory factor, correlation, option volatility) from CRE52.72 Table 2."""
    return {"interest_rate": (IR_SF, None, IR_VOL), "fx": (FX_SF, None, FX_VOL),
            "credit": CREDIT.get(trade.rating), "equity": EQUITY[trade.index],
            "commodity": COMMODITY[trade.electricity]}[trade.asset_class]


def _delta(trade, volatility):
    """CRE52.39 for linear trades, CRE52.40 (with the FAQ2 shift) for options."""
    sign = 1.0 if trade.position == "long" else -1.0
    if trade.option is None:
        return sign
    d1 = ((math.log((trade.underlying_price + trade.shift) / (trade.strike + trade.shift))
           + 0.5 * volatility ** 2 * trade.exercise) / (volatility * math.sqrt(trade.exercise)))
    return sign * float(norm.cdf(d1) if trade.option == "call" else -norm.cdf(-d1))


def _single_factor(addons):
    """CRE52.61 step 4, CRE52.66 step 4, CRE52.70 step 5: [(sum rho*A)^2 + sum (1-rho^2)*A^2]^0.5."""
    systematic = math.fsum(rho * a for a, rho in addons) ** 2
    return math.sqrt(systematic + math.fsum((1 - rho ** 2) * a * a for a, rho in addons))


def _consistent(groups, what):
    for key, params in groups.items():
        if len(set(params)) > 1:
            raise ValueError(f"{what} {key} has trades with different supervisory parameters")


def _netting_set(request, margined):
    trades, effective = [], {}
    if margined:  # CRE52.52 and CRE52.53
        mf_margined = 1.5 * math.sqrt(request.mpor_business_days / BUSINESS_DAYS_PER_YEAR)
    for t in request.trades:
        sf, rho, vol = _parameters(t)
        sd = None
        if t.asset_class in ("interest_rate", "credit"):  # CRE52.34
            sd = max((math.exp(-0.05 * t.start) - math.exp(-0.05 * t.end)) / 0.05, TEN_BUSINESS_DAYS)
        adjusted = t.notional * (sd if sd is not None else 1.0)  # CRE52.34 to CRE52.36
        mf = mf_margined if margined else math.sqrt(min(max(t.maturity, TEN_BUSINESS_DAYS), 1.0))
        delta = _delta(t, vol)
        effective[t.id] = adjusted * mf * delta  # CRE52.30, D = d * MF * delta
        trades.append(dict(id=t.id, asset_class=t.asset_class, adjusted_notional=adjusted,
                           supervisory_duration=sd, maturity_factor=mf, supervisory_delta=delta,
                           effective_notional=effective[t.id], supervisory_factor=sf,
                           correlation=rho, supervisory_option_volatility=vol if t.option else None))
    by_class = defaultdict(list)
    for t in request.trades:
        by_class[t.asset_class].append(t)
    hedging_sets, addon_by_class = [], {}
    if "interest_rate" in by_class:  # CRE52.57
        buckets = defaultdict(lambda: [0.0, 0.0, 0.0])
        for t in by_class["interest_rate"]:
            buckets[t.hedging_set][0 if t.end < 1 else 1 if t.end <= 5 else 2] += effective[t.id]
        rows = []
        for ccy, (d1, d2, d3) in sorted(buckets.items()):
            en = math.sqrt(max(d1 * d1 + d2 * d2 + d3 * d3 + 1.4 * d1 * d2 + 1.4 * d2 * d3
                               + 0.6 * d1 * d3, 0.0))
            rows.append(dict(asset_class="interest_rate", hedging_set=ccy,
                             bucket_effective_notionals=[d1, d2, d3],
                             effective_notional=en, addon=IR_SF * en))
        hedging_sets += rows
        addon_by_class["interest_rate"] = math.fsum(r["addon"] for r in rows)
    if "fx" in by_class:  # CRE52.59
        pairs = defaultdict(list)
        for t in by_class["fx"]:
            pairs[t.hedging_set].append(effective[t.id])
        rows = [dict(asset_class="fx", hedging_set=pair, effective_notional=math.fsum(values),
                     addon=FX_SF * abs(math.fsum(values))) for pair, values in sorted(pairs.items())]
        hedging_sets += rows
        addon_by_class["fx"] = math.fsum(r["addon"] for r in rows)
    for cls in ("credit", "equity"):  # CRE52.61, CRE52.66: one hedging set, entity level offset
        if cls not in by_class:
            continue
        entities, params = defaultdict(list), defaultdict(set)
        for t in by_class[cls]:
            entities[t.reference].append(effective[t.id])
            params[t.reference].add(_parameters(t))
        _consistent(params, cls + " entity")
        addons = []
        rows = []
        for name, values in sorted(entities.items()):
            sf, rho, _ = next(iter(params[name]))
            addons.append((sf * math.fsum(values), rho))
            rows.append(dict(reference=name, effective_notional=math.fsum(values),
                             addon=addons[-1][0], correlation=rho))
        addon_by_class[cls] = _single_factor(addons)
        hedging_sets.append(dict(asset_class=cls, hedging_set=cls, entities=rows,
                                 addon=addon_by_class[cls]))
    if "commodity" in by_class:  # CRE52.70
        types, params = defaultdict(list), defaultdict(set)
        for t in by_class["commodity"]:
            types[(t.hedging_set, t.reference)].append(effective[t.id])
            params[(t.hedging_set, t.reference)].add(_parameters(t))
        _consistent(params, "commodity type")
        total = []
        for hs in COMMODITY_SETS:
            keys = sorted(k for k in types if k[0] == hs)
            if not keys:
                continue
            rows = [dict(reference=k[1], effective_notional=math.fsum(types[k]),
                         addon=next(iter(params[k]))[0] * math.fsum(types[k]),
                         correlation=next(iter(params[k]))[1]) for k in keys]
            addon = _single_factor([(r["addon"], r["correlation"]) for r in rows])
            hedging_sets.append(dict(asset_class="commodity", hedging_set=hs, entities=rows,
                                     addon=addon))
            total.append(addon)
        addon_by_class["commodity"] = math.fsum(total)
    addon = math.fsum(addon_by_class.values())  # CRE52.25
    v = math.fsum(t.market_value for t in request.trades)
    c = request.collateral
    rc = max(v - c, 0.0)  # CRE52.10
    if margined:  # CRE52.18
        rc = max(v - c, request.threshold + request.minimum_transfer_amount - request.nica, 0.0)
    if v - c >= 0:  # CRE52.23: the exponential is at least 1, so the minimum is 1
        multiplier = 1.0
    elif addon > 0:  # CRE52.23
        multiplier = MULTIPLIER_FLOOR + (1 - MULTIPLIER_FLOOR) * math.exp(
            (v - c) / (2 * (1 - MULTIPLIER_FLOOR) * addon))
    else:  # no add-on, so PFE is zero whatever the multiplier; report the limit value
        multiplier = MULTIPLIER_FLOOR
    pfe = multiplier * addon  # CRE52.20
    return dict(ead=ALPHA * (rc + pfe), replacement_cost=rc, pfe=pfe, multiplier=multiplier,
                addon_aggregate=addon, addon_by_asset_class=addon_by_class,
                netting_set_value=v, hedging_sets=hedging_sets, trades=trades)


def saccr_ead(payload):
    request = SaccrRequest.model_validate(payload)
    result = envelope(request, "SA-CCR exposure at default, Basel Framework CRE52", [
        "Basel Framework CRE52 (effective 1 January 2023) for a single bilateral netting set; "
        "constants cite their paragraph in reference.md.",
        "All amounts are in the request currency. notional is the trade notional for interest "
        "rate and credit, the foreign leg in the request currency for fx (CRE52.35), and "
        "price times units for equity and commodity (CRE52.36).",
        "collateral is the haircut value of net collateral held; haircuts are applied by the caller.",
        "Times are in years; ten business days are 10/250 years (CRE52.49).",
        "The interest rate hedging sets use the offset formula of CRE52.57 step 5.",
        "Not modelled: basis and volatility hedging sets (CRE52.46, 52.47), CDO tranches "
        "(CRE52.41), central counterparty MPOR floors (CRE54), the 20 day MPOR cases of CRE52.51, "
        "and multiple margin agreements or netting sets (CRE52.74 to 52.77)."])
    if {t.asset_class for t in request.trades} & {"fx", "equity"}:
        result["assumptions"].append("FX and equity add-ons are partially verified: constants checked "
                                     "against CRE52.72, but the Basel Framework publishes no worked "
                                     "FX or equity example to reproduce.")
    figures = _netting_set(request, request.margined)
    if request.margined:  # CRE52.2: capped at the same netting set calculated unmargined
        unmargined = _netting_set(request, False)
        figures.update(unmargined_ead=unmargined["ead"],
                       cap_applied=unmargined["ead"] < figures["ead"])
        figures["ead"] = min(figures["ead"], unmargined["ead"])
        result["assumptions"].append("The CRE52.2 cap recomputes the netting set with unmargined "
                                     "maturity factors and replacement cost, keeping V and C.")
    numbers = [figures[k] for k in ("ead", "replacement_cost", "pfe", "multiplier", "addon_aggregate")]
    numbers += [t[k] for t in figures["trades"] for k in ("adjusted_notional", "effective_notional")]
    if not all(math.isfinite(x) for x in numbers):
        raise ValueError("SA-CCR calculation exceeded numerical limits")
    result.update(netting_set=request.netting_set, alpha=ALPHA, margined=request.margined,
                  mpor_business_days=request.mpor_business_days, **figures)
    return result


class ExposureRow(StrictModel):
    """One row of ORE's netting-set exposure report; field names are ORE's column names."""
    NettingSet: str | None = None
    Date: str | None = None
    Time: float = Field(ge=0, le=200)
    EPE: float | None = None
    ENE: float | None = None
    PFE: float | None = None
    ExpectedCollateral: float | None = None
    BaselEE: float | None = None
    BaselEEE: float | None = None
    TimeWeightedBaselEPE: float | None = None
    TimeWeightedBaselEEPE: float | None = None


class ExposureProfileRequest(Provenance):
    rows: list[ExposureRow] = Field(min_length=2, max_length=100_000)

    @model_validator(mode="after")
    def usable_profile(self):
        for i, row in enumerate(self.rows):
            if row.BaselEE is None or row.PFE is None:
                raise ValueError(f"row {i} has no BaselEE or PFE; ORE reported it unavailable")
            if row.BaselEE < 0 or row.PFE < 0:
                raise ValueError(f"row {i} has a negative BaselEE or PFE; exposure is not signed")
        if self.rows[0].Time != 0:
            raise ValueError("the first row must be the as-of date, Time 0")
        if any(b.Time <= a.Time for a, b in zip(self.rows, self.rows[1:])):
            raise ValueError("Time must increase strictly from row to row")
        if len({r.NettingSet for r in self.rows}) != 1:
            raise ValueError("rows must come from one netting set")
        return self


def exposure_profile_summary(payload):
    request = ExposureProfileRequest.model_validate(payload)
    rows = request.rows
    effective = [rows[0].BaselEE]  # CRE53.12: Effective EE at t0 is the current exposure
    for row in rows[1:]:
        effective.append(max(effective[-1], row.BaselEE))  # CRE53.12 equation 2, CRE50.29
    window = [k for k in range(1, len(rows)) if rows[k].Time <= 1.0]
    if not window:
        raise ValueError("no exposure date falls within the first year")
    horizon = rows[window[-1]].Time
    weights = [rows[k].Time - rows[k - 1].Time for k in window]  # CRE53.13, dt_k = t_k - t_(k-1)
    epe = math.fsum(rows[k].BaselEE * w for k, w in zip(window, weights)) / horizon  # CRE50.30
    eepe = math.fsum(effective[k] * w for k, w in zip(window, weights)) / horizon    # CRE50.31
    warnings = []
    if horizon < 1.0 and window[-1] < len(rows) - 1:
        warnings.append(f"the grid has no date at one year; EPE and Effective EPE average the "
                        f"first {horizon:.6g} years")
    peak = max(range(len(rows)), key=lambda k: rows[k].PFE)
    result = envelope(request, "Basel exposure profile summary, CRE50.27 to 50.31 and CRE53.12 to 53.13", [
        "BaselEE is ORE's undiscounted expected exposure (ORE divides its discounted EPE by the "
        "base currency discount factor); ORE column names and signs are kept.",
        "PFE is ORE's quantile at the confidence level set in the ORE configuration; it is not re-estimated.",
        "EPE and Effective EPE weight each date by dt_k = t_k - t_(k-1) over dates up to one year, "
        "divided by the covered horizon; if the grid ends before one year it is taken as the "
        "netting set maturity.",
        "No EAD is reported: alpha times Effective EPE (CRE53.11) requires internal model approval."],
        warnings)
    if not all(math.isfinite(x) for x in (epe, eepe)):
        raise ValueError("exposure summary exceeded numerical limits")
    result.update(netting_set=rows[0].NettingSet, peak_pfe=rows[peak].PFE,
                  peak_pfe_time=rows[peak].Time, peak_pfe_date=rows[peak].Date,
                  epe=epe, effective_epe=eepe, averaging_horizon_years=horizon,
                  dates_in_first_year=len(window),
                  effective_ee=[dict(Time=r.Time, Date=r.Date, BaselEE=r.BaselEE, effective_ee=e)
                                for r, e in zip(rows, effective)])
    return result
