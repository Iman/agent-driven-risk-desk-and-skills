"""Backtest a VaR (and optionally ES) forecast series against realised P&L.

Formulas and sources are in plugins/risk-desk/skills/risk-backtest/reference.md.
"""
from typing import Literal

import numpy as np
from pydantic import Field, model_validator
from scipy import stats
from scipy.special import xlogy

from riskdesk.analytics import envelope
from riskdesk.models import Provenance

# Basel Framework MAR99.17 and Table 2: amber from a cumulative binomial probability of 95%,
# red from 99.99%, at 99% coverage. MAR99.4: one-day risk measures against one-day outcomes.
BASEL_AMBER, BASEL_RED = 0.95, 0.9999
ES_SIMULATIONS = 10_000


class BacktestRequest(Provenance):
    pnl: list[float] = Field(min_length=2, max_length=10_000)
    var: list[float] = Field(min_length=2, max_length=10_000)
    expected_shortfall: list[float] | None = Field(default=None, min_length=2, max_length=10_000)
    confidence: float = Field(gt=0, lt=1)
    horizon_days: int = Field(gt=0, le=3650, strict=True)
    es_null: Literal["normal", "student-t"] | None = None
    es_null_dof: float | None = Field(default=None, gt=1, le=1000)
    seed: int = Field(default=0, ge=0, strict=True)

    @model_validator(mode="after")
    def consistent(self):
        if len(self.var) != len(self.pnl):
            raise ValueError("var and pnl must have the same length")
        if (self.expected_shortfall is None) != (self.es_null is None):
            raise ValueError("expected_shortfall and es_null must be given together")
        if (self.es_null == "student-t") != (self.es_null_dof is not None):
            raise ValueError("es_null_dof is required for, and only for, es_null student-t")
        if self.expected_shortfall is not None:
            if len(self.expected_shortfall) != len(self.pnl):
                raise ValueError("expected_shortfall and pnl must have the same length")
            if any(es <= max(var, 0) for es, var in zip(self.expected_shortfall, self.var)):
                raise ValueError("each expected_shortfall must be positive and greater than its VaR")
        return self


def _lr(statistic, dof):
    statistic = max(float(statistic), 0.0)  # rounding can leave -1e-13 at a perfect fit
    return dict(lr=statistic, p_value=float(stats.chi2.sf(statistic, dof)))


def _kupiec(x, n, p):
    """Kupiec (1995) proportion of failures."""
    phat = x/n
    return _lr(-2*(xlogy(n - x, 1 - p) + xlogy(x, p) - xlogy(n - x, 1 - phat) - xlogy(x, phat)), 1)


def _christoffersen(hits, p):
    """Christoffersen (1998) first-order Markov independence and conditional coverage."""
    prev, nxt = hits[:-1], hits[1:]
    n00, n01 = int(np.sum(~prev & ~nxt)), int(np.sum(~prev & nxt))
    n10, n11 = int(np.sum(prev & ~nxt)), int(np.sum(prev & nxt))
    pi0 = n01/(n00 + n01) if n00 + n01 else 0.0
    pi1 = n11/(n10 + n11) if n10 + n11 else 0.0
    pi = (n01 + n11)/len(nxt)
    markov = xlogy(n00, 1 - pi0) + xlogy(n01, pi0) + xlogy(n10, 1 - pi1) + xlogy(n11, pi1)
    iid = xlogy(n00 + n10, 1 - pi) + xlogy(n01 + n11, pi)
    null = xlogy(n00 + n10, 1 - p) + xlogy(n01 + n11, p)
    return (dict(_lr(-2*(iid - markov), 1), n00=n00, n01=n01, n10=n10, n11=n11, pi0=pi0, pi1=pi1),
            _lr(-2*(null - markov), 2))


def _basel_zone(x, n):
    cumulative = float(stats.binom.cdf(x, n, 0.01))
    zone = "red" if cumulative >= BASEL_RED else "amber" if cumulative >= BASEL_AMBER else "green"
    return dict(zone=zone, cumulative_probability=cumulative,
                amber_from=int(stats.binom.ppf(BASEL_AMBER, n, 0.01)), red_from=int(stats.binom.ppf(BASEL_RED, n, 0.01)))


def _z2(pnl, var, es, alpha):
    """Acerbi and Szekely (2014) Z2; rows of pnl are independent samples."""
    return np.sum(pnl*(pnl + var < 0)/es, axis=-1)/(pnl.shape[-1]*alpha) + 1


def _es_test(pnl, var, es, request):
    """Z2 with a p-value simulated under the null that each day's loss is the location-scale
    member of the stated family whose VaR and ES equal the forecasts."""
    c, alpha = request.confidence, 1 - request.confidence
    rng = np.random.default_rng(request.seed)
    if request.es_null == "normal":
        q = stats.norm.ppf(c)
        e = stats.norm.pdf(q)/alpha
        draw = rng.standard_normal
    else:
        dof = request.es_null_dof
        q = stats.t.ppf(c, dof)
        e = stats.t.pdf(q, dof)/alpha*(dof + q*q)/(dof - 1)
        draw = lambda size: rng.standard_t(dof, size)
    scale = (es - var)/(e - q)
    loc = var - scale*q
    if not (np.isfinite(scale).all() and np.isfinite(loc).all()):
        raise ValueError("ES null calibration exceeded numerical limits")
    observed = float(_z2(pnl, var, es, alpha))
    if not np.isfinite(observed):
        raise ValueError("ES backtest statistic exceeded numerical limits")
    batch = max(1, 2_000_000//len(pnl))  # bounds memory at about 16 MB per batch
    simulated = np.concatenate([_z2(-(loc + scale*draw((min(batch, ES_SIMULATIONS - s), len(pnl)))), var, es, alpha)
                                for s in range(0, ES_SIMULATIONS, batch)])
    if not np.isfinite(simulated).all():
        raise ValueError("ES null simulation exceeded numerical limits")
    # add-one estimator: a finite simulation cannot show a p-value of exactly zero
    p_value = float((np.sum(simulated <= observed) + 1)/(ES_SIMULATIONS + 1))
    return dict(z2=observed, p_value=p_value, mc_standard_error=float(np.sqrt(p_value*(1 - p_value)/ES_SIMULATIONS)),
                simulations=ES_SIMULATIONS, seed=request.seed, null=request.es_null, null_dof=request.es_null_dof)


def var_backtest(payload):
    request = BacktestRequest.model_validate(payload)
    pnl, var = np.asarray(request.pnl), np.asarray(request.var)
    p, n = 1 - request.confidence, len(pnl)
    hits = -pnl > var
    x = int(hits.sum())
    independence, conditional = _christoffersen(hits, p)
    basel = basel_reason = None
    if request.confidence == 0.99 and request.horizon_days == 1:
        basel = _basel_zone(x, n)
    else:
        basel_reason = "MAR99 zones apply to one-day VaR at 99% coverage only"
    es_test = None
    if request.expected_shortfall is not None:
        try:
            with np.errstate(over="raise", invalid="raise", divide="raise"):
                es_test = _es_test(pnl, var, np.asarray(request.expected_shortfall), request)
        except FloatingPointError:
            raise ValueError("ES backtest exceeded numerical limits") from None
    result = envelope(request, "VaR exception backtests and Acerbi-Szekely ES backtest", [
        "An exception is a realised loss strictly greater than that day's VaR; loss is minus P&L.",
        "Each VaR was forecast before its P&L was realised and covers the stated horizon; rows are in time order.",
        "Kupiec and Christoffersen p-values use their asymptotic chi-square distributions.",
        "The ES p-value is simulated under a stated location-scale null, not the bank's own model distribution."])
    result.update(confidence=request.confidence, horizon_days=request.horizon_days, observations=n,
                  exceptions=x, expected_exceptions=n*p, exception_rate=x/n,
                  kupiec_pof=_kupiec(x, n, p), christoffersen_independence=independence,
                  christoffersen_conditional_coverage=conditional,
                  basel_traffic_light=basel, basel_traffic_light_unavailable=basel_reason, es_backtest=es_test)
    return result
