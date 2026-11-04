"""Covariance estimation, Euler risk allocation and factor exposure for linear positions.

Formulas and sources are in plugins/risk-desk/skills/risk-attribution/reference.md.
"""
from decimal import Decimal
import math
from typing import Literal

import numpy as np
from pydantic import Field, model_validator
from scipy.stats import norm
from sklearn.covariance import LedoitWolf

from riskdesk.analytics import envelope
from riskdesk.models import PortfolioRequest, Provenance

HORIZON = "Each return row spans horizon_days; no square-root-of-time scaling is applied."


class ReturnHistory(Provenance):
    assets: list[str] = Field(min_length=1, max_length=1000)
    returns: list[list[float]] = Field(min_length=2, max_length=100_000)
    horizon_days: int = Field(gt=0, le=3650, strict=True)

    @model_validator(mode="after")
    def rectangular_history(self):
        if len(set(self.assets)) != len(self.assets):
            raise ValueError("asset names must be unique")
        if any(len(row) != len(self.assets) for row in self.returns):
            raise ValueError("every return row must have one value per asset")
        if any(value < -1 for row in self.returns for value in row):
            raise ValueError("linear asset returns cannot be less than -100%")
        return self


class CovarianceRequest(ReturnHistory):
    method: Literal["sample", "ewma", "ledoit_wolf"]
    decay: float | None = Field(default=None, gt=0, lt=1)

    @model_validator(mode="after")
    def decay_only_for_ewma(self):
        if (self.method == "ewma") != (self.decay is not None):
            raise ValueError("decay is required for ewma and is not accepted for other methods")
        return self


class ParametricRequest(PortfolioRequest):
    assets: list[str] = Field(min_length=1, max_length=1000)
    covariance: list[list[float]] = Field(min_length=1, max_length=1000)
    confidence: float = Field(gt=0.5, lt=1)  # z > 0, so VaR is a loss and percentages are defined
    horizon_days: int = Field(gt=0, le=3650, strict=True)

    @model_validator(mode="after")
    def square_covariance(self):
        if len(set(self.assets)) != len(self.assets):
            raise ValueError("asset names must be unique")
        if len(self.covariance) != len(self.assets) or any(
                len(row) != len(self.assets) for row in self.covariance):
            raise ValueError("covariance must be a square matrix with one row per asset")
        return self


class HistoricalRequest(PortfolioRequest, ReturnHistory):
    confidence: float = Field(gt=0, lt=1)


class FactorRequest(PortfolioRequest, ReturnHistory):
    factors: list[str] = Field(min_length=1, max_length=100)
    factor_returns: list[list[float]] = Field(min_length=2, max_length=100_000)

    @model_validator(mode="after")
    def aligned_factors(self):
        if len(set(self.factors)) != len(self.factors):
            raise ValueError("factor names must be unique")
        if len(self.factor_returns) != len(self.returns):
            raise ValueError("factor_returns must have one row per asset return row")
        if any(len(row) != len(self.factors) for row in self.factor_returns):
            raise ValueError("every factor return row must have one value per factor")
        if len(self.returns) <= len(self.factors) + 1:
            raise ValueError("regression needs more observations than factors plus intercept")
        return self


def _positions(request):
    """Position values, each position's asset index, and net exposure per asset."""
    index = {asset: i for i, asset in enumerate(request.assets)}
    missing = sorted({p.asset for p in request.positions} - set(index))
    if missing:
        raise ValueError("positions name assets with no data: " + ", ".join(missing))
    values = np.array([p.market_value for p in request.positions])
    where = np.array([index[p.asset] for p in request.positions])
    return values, where, np.bincount(where, weights=values, minlength=len(index))


def _eigen(matrix):
    """Eigenvalues and the numpy matrix_rank default tolerance, max|eig| * n * eps."""
    eig = np.linalg.eigvalsh(matrix)
    return eig, float(np.abs(eig).max()) * len(eig) * np.finfo(float).eps


def _finite(*values):
    if not all(np.isfinite(v).all() for v in values):
        raise ValueError("calculation exceeded numerical limits")


def covariance_estimate(payload):
    request = CovarianceRequest.model_validate(payload)
    returns = np.asarray(request.returns)
    shrinkage = None
    if request.method == "sample":
        covariance = np.atleast_2d(np.cov(returns, rowvar=False, ddof=1))
        method = "sample covariance, demeaned, divided by T-1"
    elif request.method == "ewma":
        # RiskMetrics 1996 Eq. [5.2] weights, latest row weight 1; zero mean per Section 5.3.
        weights = request.decay ** np.arange(len(returns))[::-1]
        weights /= weights.sum()
        covariance = (returns * weights[:, None]).T @ returns
        method = "EWMA covariance, zero mean, finite-sample normalised weights"
    else:
        fit = LedoitWolf().fit(returns)
        covariance, shrinkage = fit.covariance_, float(fit.shrinkage_)
        method = "Ledoit-Wolf shrinkage towards a scaled identity via scikit-learn"
    _finite(covariance)
    eig, tol = _eigen(covariance)
    positive_definite = bool(eig.min() > tol)
    warnings = [] if positive_definite else [
        "Covariance is not positive definite (smallest eigenvalue {:.6g}, tolerance {:.6g}); "
        "no repair was applied. ledoit_wolf gives a positive definite estimate.".format(eig.min(), tol)]
    vol = np.sqrt(np.clip(np.diag(covariance), 0, None))
    with np.errstate(divide="ignore", invalid="ignore"):
        corr = covariance / np.outer(vol, vol)
    result = envelope(request, method, [
        HORIZON,
        "Rows are ordered oldest first; EWMA gives the last row the largest weight.",
        "Sample is unbiased (T-1); Ledoit-Wolf shrinks the maximum-likelihood (1/T) estimate; EWMA uses no mean.",
        "Positive definiteness is tested against max|eigenvalue| * n * machine epsilon. No matrix is altered."],
        warnings)
    result.update(
        estimator=request.method, decay=request.decay, shrinkage=shrinkage, assets=request.assets,
        observations=len(returns), horizon_days=request.horizon_days,
        covariance=covariance.tolist(), volatilities=vol.tolist(),
        correlation=[[float(c) if vol[i] > 0 and vol[j] > 0 else None for j, c in enumerate(row)]
                     for i, row in enumerate(corr)],
        min_eigenvalue=float(eig.min()), max_eigenvalue=float(eig.max()),
        positive_definite=positive_definite, repair=None)
    return result


def parametric_var(payload):
    request = ParametricRequest.model_validate(payload)
    values, where, exposure = _positions(request)
    covariance = np.asarray(request.covariance)
    if not np.allclose(covariance, covariance.T, rtol=1e-12, atol=0):
        raise ValueError("covariance must be symmetric")
    eig, tol = _eigen(covariance)
    if eig.min() < -tol:
        raise ValueError("covariance is not positive semidefinite")
    variance = float(exposure @ covariance @ exposure)
    if not math.isfinite(variance):
        raise ValueError("portfolio variance exceeds numerical limits")
    if variance <= 0:
        raise ValueError("portfolio variance is zero; Euler contributions are undefined")
    sigma = math.sqrt(variance)
    z = float(norm.ppf(request.confidence))
    es_multiplier = float(norm.pdf(z)) / (1 - request.confidence)
    gradient = covariance @ exposure / sigma  # d sigma / d exposure per asset, Tasche 2008 Eq. (3.4a)
    # Incremental VaR: the portfolio without each position, variance recomputed in full.
    # shortcut: memory and time grow as positions x assets^2; batch this when books exceed ~10^4 x 10^3.
    without = np.tile(exposure, (len(values), 1))
    without[np.arange(len(values)), where] -= values
    var_without = z * np.sqrt(np.clip(np.einsum("pi,ij,pj->p", without, covariance, without), 0, None))
    var, es = z * sigma, es_multiplier * sigma
    marginal = gradient[where]
    _finite(var_without, marginal * values)
    rows = [dict(id=p.id, asset=p.asset, market_value=p.market_value,
                 marginal_var=z*m, component_var=z*m*p.market_value, percentage_var=z*m*p.market_value/var,
                 marginal_es=es_multiplier*m, component_es=es_multiplier*m*p.market_value,
                 percentage_es=es_multiplier*m*p.market_value/es, incremental_var=var-float(w))
            for p, m, w in zip(request.positions, marginal.tolist(), var_without)]
    result = envelope(request, "parametric normal VaR and ES with Euler allocation", [
        HORIZON,
        "Portfolio P&L is normal with zero mean and the supplied covariance of simple returns.",
        "Loss is positive. Marginal values are per unit of market value; components sum to the total.",
        "Incremental VaR is total VaR minus the VaR of the portfolio without that position.",
        "Percentage contributions can be negative for hedges and above one for concentrations."])
    result.update(confidence=request.confidence, horizon_days=request.horizon_days, nav=request.nav,
                  portfolio_std=sigma, var=var, expected_shortfall=es, z=z, positions=rows)
    return result


def historical_es(payload):
    request = HistoricalRequest.model_validate(payload)
    values, where, _ = _positions(request)
    losses = -np.asarray(request.returns)[:, where] * values  # scenarios x positions, loss positive
    total = losses.sum(axis=1)
    _finite(losses, total)
    count = len(total)
    mass = Decimal(count) * (1 - Decimal(str(request.confidence)))
    whole = int(mass)
    weights = np.zeros(count)
    weights[:whole] = 1.0
    if whole < count:
        weights[whole] = float(mass - whole)
    order = np.argsort(-total, kind="stable")
    ranked = total[order]
    components = weights @ losses[order] / float(mass)
    es = float(weights @ ranked / float(mass))
    warnings = []
    if mass < 20:
        warnings.append("Fewer than 20 observations of tail probability mass; this reporting threshold is not a confidence test.")
    if np.any((ranked[1:] == ranked[:-1]) & (weights[1:] != weights[:-1])):
        warnings.append("Scenarios with equal portfolio loss straddle the tail boundary; "
                        "the total is unaffected but the split between positions depends on input order.")
    result = envelope(request, "historical-simulation Expected Shortfall with Euler allocation", [
        HORIZON,
        "Each scenario row is equally likely; ES integrates fractional tail mass as in risk_tail.",
        "A position's ES contribution is its tail-weighted average loss over the same scenarios.",
        "Loss is positive; contributions sum to the historical ES."], warnings)
    result.update(confidence=request.confidence, horizon_days=request.horizon_days, nav=request.nav,
                  observations=count, tail_probability_mass=float(mass), expected_shortfall=es,
                  positions=[dict(id=p.id, asset=p.asset, market_value=p.market_value,
                                  component_es=float(c), percentage_es=float(c)/es if es else None)
                             for p, c in zip(request.positions, components)],
                  tail_scenarios=[dict(index=int(i), weight=float(w), loss=float(total[i]))
                                  for i, w in zip(order, weights) if w > 0])
    return result


def factor_exposure(payload):
    request = FactorRequest.model_validate(payload)
    _, _, exposure = _positions(request)
    returns, factors = np.asarray(request.returns), np.asarray(request.factor_returns)
    design = np.column_stack([np.ones(len(factors)), factors])
    if np.linalg.matrix_rank(design) < design.shape[1]:
        raise ValueError("factor returns are collinear or constant; betas are not identified")
    coef, *_ = np.linalg.lstsq(design, returns, rcond=None)
    residuals = returns - design @ coef
    betas = coef[1:].T  # assets x factors
    loading = betas.T @ exposure  # currency P&L per unit factor return
    factor_cov = np.atleast_2d(np.cov(factors, rowvar=False, ddof=1))
    residual_cov = np.atleast_2d(np.cov(residuals, rowvar=False, ddof=1))
    asset_var = np.var(returns, axis=0, ddof=1)
    systematic = float(loading @ factor_cov @ loading)
    idiosyncratic = float(exposure @ residual_cov @ exposure)
    specific = float(exposure**2 @ np.diag(residual_cov))
    total = float(np.var(returns @ exposure, ddof=1))
    _finite(coef, loading, systematic, idiosyncratic, total)
    result = envelope(request, "OLS factor regression with portfolio variance split", [
        HORIZON,
        "Each asset is regressed on all factors with an intercept by ordinary least squares.",
        "Variances use T-1. In sample, total = systematic + idiosyncratic exactly, because OLS "
        "residuals are uncorrelated with the factors.",
        "Idiosyncratic includes residual cross-covariance between assets; specific is its diagonal part.",
        "Factor exposure is currency P&L per 1.00 factor return; factor beta divides it by NAV."])
    result.update(
        horizon_days=request.horizon_days, nav=request.nav, observations=len(returns),
        factors=request.factors,
        assets={a: dict(alpha=float(coef[0, i]), betas=dict(zip(request.factors, betas[i].tolist())),
                        r_squared=1 - float(residual_cov[i, i] / asset_var[i]) if asset_var[i] > 0 else None)
                for i, a in enumerate(request.assets)},
        portfolio_factor_exposure=dict(zip(request.factors, loading.tolist())),
        portfolio_factor_beta=dict(zip(request.factors, (loading / request.nav).tolist())),
        variance=dict(total=total, systematic=systematic, idiosyncratic=idiosyncratic,
                      specific=specific, residual_cross=idiosyncratic - specific),
        systematic_share=systematic / total if total > 0 else None)
    return result
