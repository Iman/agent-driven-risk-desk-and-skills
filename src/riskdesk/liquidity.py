"""Days to liquidate, the liquidation schedule, and spread-adjusted VaR (Bangia et al. 1999)."""
from collections import defaultdict
import math

from pydantic import Field, model_validator

from riskdesk.analytics import envelope, fsum, tail_risk
from riskdesk.models import PortfolioRequest, StrictModel

# The same ten-year ceiling TailRequest places on horizon_days; beyond it an input is
# far more likely to be a unit error (daily value given per year, or in thousands).
MAX_SCHEDULE_DAYS = 3650


class AssetLiquidity(StrictModel):
    average_daily_value: float = Field(gt=0)
    mean_relative_spread: float = Field(ge=0)
    spread_volatility: float = Field(ge=0)


class LiquidityRequest(PortfolioRequest):
    participation_rate: float = Field(gt=0, le=1)
    spread_multiplier: float = Field(ge=0)
    liquidity: dict[str, AssetLiquidity]
    pnl: list[float] | None = Field(default=None, min_length=2, max_length=1_000_000)
    confidence: float | None = Field(default=None, gt=0, lt=1)
    horizon_days: int | None = Field(default=None, gt=0, le=3650, strict=True)

    @model_validator(mode="after")
    def coherent(self):
        if set(self.liquidity) != {p.asset for p in self.positions}:
            raise ValueError("liquidity must name exactly the portfolio assets")
        tail = (self.pnl, self.confidence, self.horizon_days)
        if any(v is not None for v in tail) and any(v is None for v in tail):
            raise ValueError("pnl, confidence and horizon_days are given together or not at all")
        return self


def liquidity_risk(payload):
    request = LiquidityRequest.model_validate(payload)
    gross = defaultdict(float)
    for position in request.positions:
        gross[position.asset] += abs(position.market_value)
    by_asset = {}
    for asset, value in gross.items():
        inputs = request.liquidity[asset]
        capacity = request.participation_rate*inputs.average_daily_value
        by_asset[asset] = dict(
            inputs.model_dump(), gross_value=value, daily_capacity=capacity, days_to_liquidate=value/capacity,
            cost_of_liquidity=0.5*value*(inputs.mean_relative_spread
                                         + request.spread_multiplier*inputs.spread_volatility))
    longest = max(row["days_to_liquidate"] for row in by_asset.values())
    cost = fsum(row["cost_of_liquidity"] for row in by_asset.values())
    total = fsum(gross.values())
    if not all(math.isfinite(v) for v in (longest, cost, total)):
        raise ValueError("liquidity calculation exceeded numerical limits")
    if longest > MAX_SCHEDULE_DAYS:
        raise ValueError("liquidation would take {:.0f} days, over {}; check the units of "
                         "average_daily_value".format(longest, MAX_SCHEDULE_DAYS))
    schedule = []
    for day in range(math.ceil(longest) + 1):
        held = fsum(max(0.0, r["gross_value"] - r["daily_capacity"]*day) for r in by_asset.values())
        schedule.append(dict(day=day, held_value=held, held_fraction=held/total if total else 0.0,
                             assets_held=sum(r["gross_value"] > r["daily_capacity"]*day
                                             for r in by_asset.values())))
    warnings, extra = [], dict(var=None, liquidity_adjusted_var=None, confidence=None, horizon_days=None, tail=None)
    if request.pnl is not None:
        tail = tail_risk(dict(request.model_dump(mode="json", include={"as_of", "currency", "source", "data_mode"}),
                              pnl=request.pnl, confidence=request.confidence,
                              horizon_days=request.horizon_days, portfolio_value=request.nav))
        if tail["degraded"]:
            warnings.append("tail: " + tail["degraded_reason"])
        slow = sorted(a for a, r in by_asset.items() if r["days_to_liquidate"] > request.horizon_days)
        if slow:
            warnings.append("{} take longer to liquidate than the {} day VaR horizon; the VaR is not "
                            "rescaled to the liquidation period".format(", ".join(slow), request.horizon_days))
        lvar = tail["var"] + cost
        if not math.isfinite(lvar):
            raise ValueError("liquidity-adjusted VaR exceeded numerical limits")
        extra = dict(var=tail["var"], liquidity_adjusted_var=lvar, confidence=request.confidence,
                     horizon_days=request.horizon_days, tail=tail)
    result = envelope(request, "days to liquidate and exogenous spread cost (Bangia, Diebold, "
                      "Schuermann and Stroughair 1999)", [
        "Days to liquidate = gross asset value / (participation rate x average daily traded value), "
        "at as-of mid values; positions in one asset share its volume and are not crossed internally.",
        "The schedule sells each asset at its daily capacity until done; prices are held at as-of values.",
        "Cost of liquidity = 1/2 x gross value x (mean relative spread + multiplier x spread volatility); "
        "relative spread is (ask - bid) / mid. The multiplier is a user input, not a default.",
        "Liquidity-adjusted VaR = supplied-P&L historical VaR + total cost of liquidity, a plain sum "
        "with no correlation adjustment. No horizon scaling of VaR, spreads or volumes is done.",
        "Loss and cost are positive. Endogenous price impact of large trades is not modelled."], warnings)
    result.update(participation_rate=request.participation_rate, spread_multiplier=request.spread_multiplier,
                  gross_value=total, by_asset=by_asset, max_days_to_liquidate=longest,
                  schedule=schedule, cost_of_liquidity=cost, **extra)
    return result
