"""Portfolio credit VaR: the asymptotic single risk factor (Vasicek) loss
quantile and a seeded default-mode one-factor Gaussian copula simulation.

Loss is positive. PD, LGD and correlation are caller inputs over the stated
horizon; nothing here estimates them.
"""
import math

import numpy as np
from pydantic import Field, model_validator
from scipy.stats import norm

from riskdesk.analytics import envelope, fsum, tail_risk
from riskdesk.models import Provenance, StrictModel

MAX_DRAWS = 200_000_000  # scenarios x obligors; bounds run time and memory per call
CHUNK_DRAWS = 2_000_000  # normal draws held in memory at once


class AsrfObligor(StrictModel):
    id: str = Field(min_length=1)
    exposure: float = Field(gt=0)
    pd: float = Field(gt=0, lt=1)
    lgd: float = Field(ge=0, le=1)
    correlation: float = Field(gt=0, lt=1)


class CopulaObligor(StrictModel):
    id: str = Field(min_length=1)
    exposure: float = Field(gt=0)
    pd: float = Field(gt=0, lt=1)
    lgd: float = Field(ge=0, le=1)
    factor_loading: float = Field(gt=-1, lt=1)


class _CreditRequest(Provenance):
    confidence: float = Field(gt=0, lt=1)
    horizon_days: int = Field(gt=0, le=3650, strict=True)

    @model_validator(mode="after")
    def unique_obligors(self):
        if len({o.id for o in self.obligors}) != len(self.obligors):
            raise ValueError("obligor ids must be unique")
        return self


class AsrfRequest(_CreditRequest):
    obligors: list[AsrfObligor] = Field(min_length=1, max_length=1_000_000)


class CopulaRequest(_CreditRequest):
    obligors: list[CopulaObligor] = Field(min_length=1, max_length=100_000)
    scenarios: int = Field(ge=1000, le=1_000_000, strict=True)  # TailRequest's sample limit
    seed: int = Field(ge=0, strict=True)

    @model_validator(mode="after")
    def bounded_work(self):
        if self.scenarios * len(self.obligors) > MAX_DRAWS:
            raise ValueError(f"scenarios times obligors exceeds {MAX_DRAWS}")
        return self


def asrf_credit_var(payload):
    request = AsrfRequest.model_validate(payload)
    # CRE31.5: N[G(PD)/sqrt(1-R) + sqrt(R/(1-R)) G(q)], the default rate at the q quantile of the factor
    pd = np.array([o.pd for o in request.obligors])
    rho = np.array([o.correlation for o in request.obligors])
    weight = np.array([o.exposure * o.lgd for o in request.obligors])
    conditional = norm.cdf((norm.ppf(pd) + np.sqrt(rho) * norm.ppf(request.confidence))
                           / np.sqrt(1 - rho))
    contributions = weight * conditional
    var = fsum(contributions)
    expected = fsum(weight * pd)
    if not all(math.isfinite(x) for x in (var, expected)):
        raise ValueError("credit VaR exceeded numerical limits")
    result = envelope(request, "asymptotic single risk factor (Vasicek) credit VaR", [
        "Infinitely granular portfolio driven by one standard normal factor; no name concentration.",
        "Default rate quantile is the CRE31.5 term N[G(PD)/sqrt(1-R) + sqrt(R/(1-R)) G(q)] at the "
        "requested confidence q; obligor quantiles add because every conditional default rate "
        "falls as the one factor rises.",
        "PD, LGD and correlation are caller inputs over the stated horizon; LGD is deterministic.",
        "Unexpected loss is credit VaR minus expected loss, the quantity CRE31.5 capitalises "
        "before its maturity adjustment. No IRB capital, maturity adjustment or 1.25 multiplier "
        "(CRE31.7) is applied.",
        "Rating migration is not modelled: default mode only."])
    result.update(confidence=request.confidence, horizon_days=request.horizon_days,
                  total_exposure=fsum(o.exposure for o in request.obligors),
                  expected_loss=expected, credit_var=var, unexpected_loss=var - expected,
                  contributions={o.id: float(c) for o, c in zip(request.obligors, contributions)})
    return result


def copula_credit_var(payload):
    request = CopulaRequest.model_validate(payload)
    n = len(request.obligors)
    threshold = norm.ppf([o.pd for o in request.obligors])
    loading = np.array([o.factor_loading for o in request.obligors])
    idiosyncratic = np.sqrt(1 - loading ** 2)
    weight = np.array([o.exposure * o.lgd for o in request.obligors])
    rng = np.random.default_rng(request.seed)
    losses = np.empty(request.scenarios)
    chunk = max(1, CHUNK_DRAWS // n)
    for start in range(0, request.scenarios, chunk):
        size = min(chunk, request.scenarios - start)
        factor = rng.standard_normal(size)
        assets = loading * factor[:, None] + idiosyncratic * rng.standard_normal((size, n))
        losses[start:start + size] = (assets < threshold) @ weight
    total = fsum(o.exposure for o in request.obligors)
    # One VaR and ES mechanism for the desk: the historical tail on simulated P&L.
    tail = tail_risk(dict(as_of=request.as_of.isoformat(), currency=request.currency,
                          source=request.source, data_mode=request.data_mode,
                          pnl=(-losses).tolist(), confidence=request.confidence,
                          horizon_days=request.horizon_days, portfolio_value=total))
    expected = float(losses.mean())
    warnings = [tail["degraded_reason"]] if tail["degraded"] else []
    result = envelope(request, "default-mode one-factor Gaussian copula Monte Carlo credit VaR", [
        "Obligor i defaults when a_i Z + sqrt(1-a_i^2) e_i < G(PD_i), Z and e_i independent "
        "standard normal; a_i is the factor loading, so pairwise asset correlation is a_i a_j.",
        "Loss is the sum of exposure times LGD over defaulted obligors; LGD is deterministic.",
        "PD, LGD and loadings are caller inputs over the stated horizon.",
        "VaR and ES come from the desk's historical tail calculation applied to the simulated "
        "losses; unexpected loss is credit VaR minus the simulated expected loss.",
        "Results are reproducible for the same seed, scenarios and obligor list; they carry "
        "Monte Carlo error.",
        "Rating migration is not modelled: default mode only."], warnings)
    result.update(confidence=request.confidence, horizon_days=request.horizon_days,
                  scenarios=request.scenarios, seed=request.seed, total_exposure=total,
                  expected_loss=expected,
                  analytic_expected_loss=fsum(o.exposure * o.lgd * o.pd for o in request.obligors),
                  loss_standard_deviation=float(losses.std(ddof=1)),
                  credit_var=tail["var"], expected_shortfall=tail["expected_shortfall"],
                  unexpected_loss=tail["var"] - expected,
                  tail_probability_mass=tail["tail_probability_mass"])
    return result
