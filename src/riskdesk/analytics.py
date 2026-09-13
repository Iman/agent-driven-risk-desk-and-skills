"""Validated adapters to skfolio and position/scenario aggregation."""
from collections import defaultdict
from decimal import Decimal
import hashlib
from importlib.metadata import version
import json
import math

import numpy as np
from skfolio.measures import cvar, value_at_risk

from riskdesk import __version__
from riskdesk.models import TailRequest, PortfolioRequest, StressRequest


def envelope(request, method, assumptions, warnings=()):
    raw = request.model_dump(mode="json")
    return dict(schema_version=1, riskdesk_version=__version__, method=method,
                currency=request.currency, as_of=request.as_of.isoformat(), source=request.source,
                data_mode=request.data_mode, input_sha256=hashlib.sha256(
                    json.dumps(raw, sort_keys=True, allow_nan=False).encode()).hexdigest(),
                degraded=bool(warnings), degraded_reason="; ".join(warnings) if warnings else None,
                assumptions=assumptions, disclaimer="Research software; model results are not guarantees.")


def tail_risk(payload):
    request = TailRequest.model_validate(payload)
    returns = np.asarray(request.pnl) / request.portfolio_value
    if not np.isfinite(returns).all():
        raise ValueError("normalised P&L exceeds numerical limits")
    count = len(returns)
    exact_mass = Decimal(count) * (1 - Decimal(str(request.confidence)))
    tail_mass = float(exact_mass)
    backend_confidence = request.confidence
    # skfolio uses ceil((1-beta)*n). At a mathematically integral boundary,
    # binary rounding can select the next observation (95%, n=20 selected 2).
    # Move only that boundary one float toward 1; skfolio still computes both measures.
    if (exact_mass == exact_mass.to_integral_value()
            and count*(1-request.confidence) > tail_mass):
        backend_confidence = math.nextafter(request.confidence, 1.0)
    warnings = ["Fewer than 20 observations of tail probability mass; this reporting threshold is not a confidence test."] if tail_mass < 20 else []
    result = envelope(request, "historical VaR and Expected Shortfall via skfolio", [
        "Each P&L sample already spans the stated horizon; no square-root-of-time scaling.",
        "Equally weighted empirical distribution; sample dependence and forecast validity are not tested.",
        "Loss is positive; negative VaR or ES denotes a gain. Values are not floored at zero.",
        "VaR uses skfolio's empirical order statistic; ES integrates fractional tail mass."], warnings)
    result.update(var=float(value_at_risk(returns, beta=backend_confidence))*request.portfolio_value,
                  expected_shortfall=float(cvar(returns, beta=backend_confidence))*request.portfolio_value,
                  confidence=request.confidence, horizon_days=request.horizon_days,
                  backend_confidence=backend_confidence, portfolio_value=request.portfolio_value,
                  observations=count, tail_probability_mass=tail_mass, skfolio_version=version("skfolio"))
    if not all(math.isfinite(result[k]) for k in ("var", "expected_shortfall")):
        raise ValueError("tail calculation exceeded numerical limits")
    return result


def portfolio_exposure(payload):
    request = PortfolioRequest.model_validate(payload)
    gross_by_asset = defaultdict(float)
    net_by_asset = defaultdict(float)
    for position in request.positions:
        gross_by_asset[position.asset] += abs(position.market_value)
        net_by_asset[position.asset] += position.market_value
    gross = math.fsum(gross_by_asset.values())
    net = math.fsum(net_by_asset.values())
    if not math.isfinite(gross) or not math.isfinite(net) or not math.isfinite(gross/request.nav):
        raise ValueError("aggregated exposure exceeds numerical limits")
    result = envelope(request, "signed base-currency linear position exposure", [
        "Market values are signed and already translated into the stated currency.",
        "Gross concentration uses absolute position values before offsetting; leverage divides by supplied NAV.",
        "Positions are linear assets; derivative Greeks and counterparty netting are separate calculations."])
    result.update(nav=request.nav, gross_exposure=gross, net_exposure=net, gross_leverage=gross/request.nav,
                  net_leverage=net/request.nav, net_by_asset=dict(net_by_asset),
                  gross_shares={asset: amount/gross if gross else 0.0 for asset, amount in gross_by_asset.items()})
    return result


def stress_test(payload):
    request = StressRequest.model_validate(payload)
    result = envelope(request, "linear full-position scenario revaluation", [
        "Shocks are simple asset returns; all assets must have explicit shocks.",
        "No probability is attached to a scenario. Derivatives and financing costs are outside this model."])
    rows = []
    for scenario in request.scenarios:
        contributions = {p.id: p.market_value*scenario.shocks[p.asset] for p in request.positions}
        pnl = math.fsum(contributions.values())
        if not math.isfinite(pnl) or not math.isfinite(request.nav+pnl):
            raise ValueError("stressed P&L exceeds numerical limits")
        rows.append(dict(name=scenario.name, pnl=pnl, loss=-pnl, stressed_nav=request.nav+pnl,
                         contributions=contributions))
    result["scenarios"] = rows
    return result
