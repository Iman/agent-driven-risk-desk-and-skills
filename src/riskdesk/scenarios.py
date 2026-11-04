"""Historical replay, a dated scenario library, reverse stress and scenario scaling for linear books.

Every revaluation goes through analytics.stress_test; this module only builds the shocks.
"""
from datetime import date
import math
from typing import Literal

import numpy as np
from pydantic import Field, PositiveFloat, model_validator
from scipy.linalg import cho_solve, solve_triangular
from scipy.optimize import minimize
from scipy.stats import norm

from riskdesk import __version__
from riskdesk.analytics import envelope, stress_test
from riskdesk.models import PortfolioRequest, Scenario

BOOK = {"as_of", "currency", "source", "data_mode", "nav", "positions"}


def _revalue(request, name, shocks):
    """Revalue the request's book under one scenario by calling stress_test."""
    payload = request.model_dump(mode="json", include=BOOK)
    return stress_test(dict(payload, scenarios=[dict(name=name, shocks=shocks)]))


def _with_stress(request, method, assumptions, warnings, stress):
    if stress["degraded"]:
        warnings = [*warnings, stress["degraded_reason"]]
    return envelope(request, method, assumptions + stress["assumptions"], warnings)


# ---------------------------------------------------------------- replay

class ReplayRequest(PortfolioRequest):
    scenario_name: str = Field(min_length=1)
    prices: dict[str, dict[date, PositiveFloat]] = Field(min_length=1)
    start: date
    end: date
    measure: Literal["end_over_start", "worst_peak_to_trough"] = "end_over_start"
    proxies: dict[str, str] = {}

    @model_validator(mode="after")
    def complete_window(self):
        if self.start >= self.end:
            raise ValueError("window start must be before window end")
        assets = {p.asset for p in self.positions}
        if set(self.proxies) - assets:
            raise ValueError("proxies may only map portfolio assets")
        for asset in sorted(assets):
            series = self.proxies.get(asset, asset)
            if series not in self.prices:
                raise ValueError(f"no price series for {series} (needed for asset {asset})")
            for day in (self.start, self.end):
                if day not in self.prices[series]:
                    raise ValueError(f"price series {series} has no level on {day.isoformat()}")
        return self


def _worst_peak_to_trough(window):
    """Largest fall from a running peak to a later level, as (return, peak index, trough index)."""
    peak = worst_peak = worst_trough = 0
    worst = 0.0
    for i, (_, level) in enumerate(window):
        if level > window[peak][1]:
            peak = i
        fall = level / window[peak][1] - 1
        if fall < worst:
            worst, worst_peak, worst_trough = fall, peak, i
    return worst, worst_peak, worst_trough


def historical_replay(payload):
    request = ReplayRequest.model_validate(payload)
    shocks, series = {}, {}
    for asset in sorted({p.asset for p in request.positions}):
        name = request.proxies.get(asset, asset)
        window = sorted((d, v) for d, v in request.prices[name].items() if request.start <= d <= request.end)
        if request.measure == "end_over_start":
            first, last = 0, len(window) - 1
            shock = window[last][1] / window[first][1] - 1
        else:
            shock, first, last = _worst_peak_to_trough(window)
        if not math.isfinite(shock):
            raise ValueError(f"window return for {asset} exceeds numerical limits")
        shocks[asset] = shock
        series[asset] = dict(series=name, from_date=window[first][0].isoformat(), from_level=window[first][1],
                             to_date=window[last][0].isoformat(), to_level=window[last][1], shock=shock)
    stress = _revalue(request, request.scenario_name, shocks)
    assumptions = [
        "Shocks are simple price returns of the caller's series on the exact window dates; "
        "no interpolation, nearest-date matching or filling. Income, carry and currency translation "
        "are excluded unless the series already contains them."]
    if request.measure == "worst_peak_to_trough":
        assumptions.append(
            "Each asset's worst peak-to-trough fall is found separately inside the window. The falls need "
            "not coincide in time, and a fall is a gain for a short position, so this is not the book's "
            "worst loss inside the window.")
    warnings = [f"{asset} replayed with proxy series {name}" for asset, name in sorted(request.proxies.items())]
    result = _with_stress(request, f"historical replay ({request.measure}) through linear scenario revaluation",
                          assumptions, warnings, stress)
    result.update(window=dict(start=request.start.isoformat(), end=request.end.isoformat(), measure=request.measure),
                  proxies=dict(request.proxies), series=series, shocks=shocks, scenarios=stress["scenarios"])
    return result


# ---------------------------------------------------------------- library

def _source(publisher, title, published, section, url):
    return dict(publisher=publisher, title=title, published=published, section=section, url=url)


# Dates only. Each date and reason is quoted from the cited source in skills/risk-stress/reference.md.
SCENARIO_LIBRARY = (
    dict(id="lehman-2008", name="Lehman Brothers failure and global loss of confidence",
         start="2008-09-12", end="2008-10-31",
         reason="Starts on the last business day before the failure of Lehman Brothers on 15 September 2008. "
                "The BIS dates the following stage 'from mid-September to late October'; the source gives no "
                "day for its end, so the window closes at the end of October 2008 by this library's convention.",
         sources=[_source("Bank for International Settlements", "79th Annual Report, 2008/09", "2009-06-29",
                          "Chapter II, opening list of the five stages of the crisis",
                          "https://www.bis.org/publ/arpdf/ar2009e2.htm")]),
    dict(id="covid-2020", name="COVID-19 market turmoil and dash for cash",
         start="2020-02-19", end="2020-03-23",
         reason="US and continental European stock markets reached record highs on 19 February 2020. The dash "
                "for cash ran to about 23 March, when the Federal Reserve announced extensive additional "
                "measures and US stock markets bottomed out.",
         sources=[_source("Financial Stability Board", "Holistic review of the March market turmoil", "2020-11-17",
                          "Sections 2.1 and 2.4; Annex 1", "https://www.fsb.org/uploads/P171120-2.pdf")]),
    dict(id="uk-gilt-ldi-2022", name="UK gilt market and LDI episode",
         start="2022-09-22", end="2022-10-14",
         reason="Starts on the last business day before the UK Government's fiscal statement of 23 September "
                "2022. Ends on 14 October 2022, the last day of the Bank of England's temporary purchases of "
                "long-dated gilts, which began on 28 September.",
         sources=[_source("Bank of England", "Bank of England announces gilt market operation", "2022-09-28",
                          "Press release",
                          "https://www.bankofengland.co.uk/news/2022/september/"
                          "bank-of-england-announces-gilt-market-operation"),
                  _source("Bank of England", "Financial stability buy/sell tools: a gilt market case study",
                          "2023", "Quarterly Bulletin 2023; sections 'Context for the Bank's intervention' and "
                          "'Outline of the Bank's intervention'",
                          "https://www.bankofengland.co.uk/quarterly-bulletin/2023/2023/"
                          "financial-stability-buy-sell-tools-a-gilt-market-case-study")]),
)


def scenario_library():
    return dict(schema_version=1, riskdesk_version=__version__, method="dated historical windows",
                windows=[dict(w, sources=[dict(s) for s in w["sources"]]) for w in SCENARIO_LIBRARY],
                note="Dates only. Risk Desk ships no prices or returns. Replay a window with your own "
                     "licensed price levels through the historical replay; your series must contain both dates.")


# ---------------------------------------------------------------- reverse stress

class ReverseStressRequest(PortfolioRequest):
    target_loss: float = Field(gt=0)
    horizon_days: int = Field(gt=0, le=3650, strict=True)
    assets: list[str] = Field(min_length=1)
    covariance: list[list[float]]
    floors: dict[str, float] = {}

    @model_validator(mode="after")
    def matching_covariance(self):
        if len(set(self.assets)) != len(self.assets) or set(self.assets) != {p.asset for p in self.positions}:
            raise ValueError("covariance assets must name each portfolio asset exactly once")
        n = len(self.assets)
        if len(self.covariance) != n or any(len(row) != n for row in self.covariance):
            raise ValueError("covariance must be a square matrix ordered like assets")
        if set(self.floors) - set(self.assets):
            raise ValueError("floors may only name portfolio assets")
        if any(value < -1 for value in self.floors.values()):
            raise ValueError("a floor cannot be below -100%")
        return self


def reverse_stress(payload):
    request = ReverseStressRequest.model_validate(payload)
    assets, loss = request.assets, request.target_loss
    w = np.array([math.fsum(p.market_value for p in request.positions if p.asset == a) for a in assets])
    sigma = np.array(request.covariance)
    if not np.allclose(sigma, sigma.T, rtol=1e-10, atol=0):
        raise ValueError("covariance must be symmetric")
    try:
        chol = np.linalg.cholesky(sigma)
    except np.linalg.LinAlgError:
        raise ValueError("covariance must be positive definite") from None
    sigma_w = sigma @ w
    variance = float(w @ sigma_w)
    if not (math.isfinite(variance) and variance > 0):
        raise ValueError("the book has no P&L variance under this covariance, so no shock is most plausible")
    pnl_std = math.sqrt(variance)
    # A simple return cannot fall below -100%, so every asset carries at least that floor.
    floors = np.array([request.floors.get(a, -1.0) for a in assets])
    shocks = -loss * sigma_w / variance
    method = "closed form"
    if (shocks < floors).any():
        reachable = math.inf if (w < 0).any() else -math.fsum(w * floors)
        if loss > reachable:
            raise ValueError(f"target loss exceeds the largest loss reachable within the floors ({reachable:g})")
        solved = minimize(lambda s: float(s @ cho_solve((chol, True), s)), np.maximum(shocks, floors),
                          jac=lambda s: 2 * cho_solve((chol, True), s), method="SLSQP",
                          bounds=[(f, None) for f in floors],
                          constraints=[dict(type="eq", fun=lambda s: w @ s / loss + 1, jac=lambda s: w / loss)],
                          options=dict(ftol=1e-14, maxiter=1000))
        shocks = np.maximum(solved.x, floors)
        if not solved.success or abs(w @ shocks + loss) > 1e-7 * loss:
            raise ValueError(f"bounded reverse stress did not converge: {solved.message}")
        method = "bounded minimisation (scipy SLSQP)"
    distance = float(np.linalg.norm(solve_triangular(chol, shocks, lower=True)))
    if not (math.isfinite(distance) and np.isfinite(shocks).all()):
        raise ValueError("reverse stress exceeds numerical limits")
    named = dict(zip(assets, shocks.tolist()))
    stress = _revalue(request, f"reverse stress to loss {loss:g}", named)
    result = _with_stress(request, f"reverse stress, minimum Mahalanobis distance ({method})", [
        "w is the net market value per asset; shocks are simple returns over horizon_days and the covariance "
        "is the caller's covariance of those returns over the same horizon.",
        "Most plausible means the smallest Mahalanobis distance under the supplied covariance. Unbounded, "
        "s* = -L Sigma w / (w' Sigma w) with distance L / sqrt(w' Sigma w). This is a geometric ranking, "
        "not a probability.",
        "Every shock is floored at -100% and at any supplied floor; when the closed form breaches a floor "
        "the floored problem is solved numerically and its distance is at least the unbounded one.",
        "ASSUMPTION: loss_exceedance_probability_if_normal holds only if shocks were jointly normal with "
        "mean zero and this covariance. Simple returns are bounded below and fat-tailed, so it is a "
        "reference figure, not an estimate."], [], stress)
    result.update(target_loss=loss, horizon_days=request.horizon_days, assets=list(assets), shocks=named,
                  mahalanobis_distance=distance, unbounded_mahalanobis_distance=loss / pnl_std,
                  pnl_standard_deviation=pnl_std, solution=method,
                  binding_floors=[a for a, s, f in zip(assets, shocks, floors) if s <= f + 1e-12],
                  loss_exceedance_probability_if_normal=float(norm.sf(loss / pnl_std)),
                  scenarios=stress["scenarios"])
    return result


# ---------------------------------------------------------------- scaling

class ScaleRequest(PortfolioRequest):
    scenario: Scenario
    target_loss: float = Field(gt=0)


def scale_scenario(payload):
    request = ScaleRequest.model_validate(payload)
    base = _revalue(request, request.scenario.name, request.scenario.shocks)["scenarios"][0]
    if not base["loss"] > 0:
        raise ValueError("the scenario does not lose money on this book, so no positive multiple reaches the loss")
    multiple = request.target_loss / base["loss"]
    shocks = {a: multiple * s for a, s in request.scenario.shocks.items()}
    if not (math.isfinite(multiple) and all(math.isfinite(s) for s in shocks.values())):
        raise ValueError("scaled scenario exceeds numerical limits")
    below = sorted(a for a, s in shocks.items() if s < -1)
    if below:
        raise ValueError(f"multiple {multiple:g} takes {', '.join(below)} below -100%; "
                         "scaling this scenario cannot reach the target loss")
    stress = _revalue(request, f"{request.scenario.name} x {multiple:g}", shocks)
    result = _with_stress(request, "linear scenario scaling to a target loss", [
        "Loss is linear in the shocks, so the multiple k = target loss / scenario loss is exact; every shock "
        "is scaled by the same k and the scenario's shape is kept.",
        "The multiple measures distance along one scenario's direction, not probability."], [], stress)
    result.update(target_loss=request.target_loss, multiple=multiple, base_loss=base["loss"],
                  base_shocks=dict(request.scenario.shocks), shocks=shocks,
                  scenarios=[base, *stress["scenarios"]])
    return result
