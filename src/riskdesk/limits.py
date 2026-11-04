"""Limit checks on Risk Desk result payloads, and pre-trade what-if revaluation."""
from collections import Counter
import json
import math
from typing import Literal

from pydantic import Field, model_validator

from riskdesk.analytics import envelope, portfolio_exposure, stress_test, tail_risk
from riskdesk.models import PortfolioRequest, Provenance, Scenario, StrictModel

# metric -> (result payload it is read from, key in that payload)
METRICS = {"gross_exposure": ("exposure", "gross_exposure"),
           "net_exposure": ("exposure", "net_exposure"),
           "gross_leverage": ("exposure", "gross_leverage"),
           "net_leverage": ("exposure", "net_leverage"),
           "gross_share": ("exposure", "gross_shares"),
           "var": ("tail", "var"),
           "expected_shortfall": ("tail", "expected_shortfall"),
           "stress_loss": ("stress", "scenarios")}
SEVERITY = ("within", "not_evaluated", "warning", "breach")


class Limit(StrictModel):
    name: str = Field(min_length=1)
    metric: Literal["gross_exposure", "net_exposure", "gross_leverage", "net_leverage",
                    "gross_share", "var", "expected_shortfall", "stress_loss"]
    asset: str | None = Field(default=None, min_length=1)
    scenario: str | None = Field(default=None, min_length=1)
    direction: Literal["max", "min"]
    limit: float
    warning: float | None = None

    @model_validator(mode="after")
    def coherent(self):
        if (self.metric == "gross_share") != (self.asset is not None):
            raise ValueError("an asset is required for gross_share and allowed only there")
        if (self.metric == "stress_loss") != (self.scenario is not None):
            raise ValueError("a scenario is required for stress_loss and allowed only there")
        if self.warning is not None and _exceeds(self.direction, self.warning, self.limit):
            raise ValueError("a warning threshold must lie on the safe side of its hard limit")
        return self


def _unique_names(limits):
    if len({limit.name for limit in limits}) != len(limits):
        raise ValueError("limit names must be unique")


class LimitRequest(Provenance):
    limits: list[Limit] = Field(min_length=1, max_length=1000)
    results: dict[Literal["exposure", "tail", "stress"], dict] = Field(min_length=1)

    @model_validator(mode="after")
    def unique_limits(self):
        _unique_names(self.limits)
        try:
            json.dumps(self.results, allow_nan=False)
        except ValueError:
            raise ValueError("supplied results contain a non-finite number") from None
        return self


def _exceeds(direction, value, threshold):
    return value > threshold if direction == "max" else value < threshold


def _read(limit, results, currency):
    """Return (value, basis, reason). Exactly one of value and reason is None."""
    kind, key = METRICS[limit.metric]
    payload = results.get(kind)
    if payload is None:
        return None, None, "no {} result was supplied".format(kind)
    if "error" in payload:
        return None, None, "the {} result is an error: {}".format(kind, payload.get("message"))
    if payload.get("currency") != currency:
        return None, None, "the {} result is in {}, the limits are in {}".format(
            kind, payload.get("currency"), currency)
    value, basis = payload.get(key), {}
    if limit.asset is not None:
        value = value.get(limit.asset) if isinstance(value, dict) else None
        if value is None:
            return None, None, "asset {} is not in the exposure result".format(limit.asset)
    if limit.scenario is not None:
        rows = [row for row in value or [] if isinstance(row, dict) and row.get("name") == limit.scenario]
        if not rows:
            return None, None, "scenario {} is not in the stress result".format(limit.scenario)
        value = rows[0].get("loss")
    if kind == "tail":
        basis = dict(confidence=payload.get("confidence"), horizon_days=payload.get("horizon_days"))
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        return None, None, "{} is missing or not a finite number in the {} result".format(key, kind)
    return float(value), basis, None


def _evaluate(request):
    warnings = []
    for kind, payload in request.results.items():
        if payload.get("currency") != request.currency:
            warnings.append("{} result currency {} differs from {}; its limits are not evaluated".format(
                kind, payload.get("currency"), request.currency))
        if payload.get("as_of") != request.as_of.isoformat():
            warnings.append("{} result as-of {} differs from {}".format(
                kind, payload.get("as_of"), request.as_of.isoformat()))
        if payload.get("degraded"):
            warnings.append("{} result is degraded: {}".format(kind, payload.get("degraded_reason")))
    rows = []
    for limit in request.limits:
        value, basis, reason = _read(limit, request.results, request.currency)
        row = dict(name=limit.name, metric=limit.metric, scope="asset" if limit.asset else "portfolio",
                   asset=limit.asset, scenario=limit.scenario, direction=limit.direction,
                   limit=limit.limit, warning=limit.warning, value=value, utilisation=None, basis=basis)
        if reason is not None:
            row.update(status="not_evaluated", reason=reason)
        else:
            row["utilisation"] = value/limit.limit if limit.limit else None
            row["status"] = ("breach" if _exceeds(limit.direction, value, limit.limit) else
                             "warning" if limit.warning is not None
                             and not _exceeds(limit.direction, limit.warning, value) else "within")
        rows.append(row)
    counts = Counter(row["status"] for row in rows)
    if counts["not_evaluated"]:
        warnings.append("{} of {} limits not evaluated".format(counts["not_evaluated"], len(rows)))
    overall = max((row["status"] for row in rows), key=SEVERITY.index)
    return rows, overall, {status: counts[status] for status in SEVERITY}, warnings


def check_limits(payload):
    request = LimitRequest.model_validate(payload)
    rows, overall, counts, warnings = _evaluate(request)
    result = envelope(request, "limit utilisation against supplied Risk Desk results", [
        "Values are read from the supplied result payloads; nothing is recomputed here.",
        "max limits breach when value > limit and warn when value >= warning; min limits mirror this.",
        "Utilisation is value divided by limit (null when the limit is zero); status is the authority.",
        "A limit whose metric, asset or scenario is absent is reported not_evaluated, never skipped.",
        "Overall status is the most severe of breach, warning, not_evaluated, within."], warnings)
    result.update(overall_status=overall, status_counts=counts, limits=rows)
    return result


class Trade(StrictModel):
    asset: str = Field(min_length=1)
    market_value_change: float
    position_id: str | None = Field(default=None, min_length=1)


def _apply(positions, trades):
    """Add each trade to the position it changes, so a sale reduces gross rather than offsetting it."""
    book = {p.id: p.model_dump() for p in positions}
    for i, trade in enumerate(trades, 1):
        target = trade.position_id
        if target is None:
            held = [pid for pid, p in book.items() if p["asset"] == trade.asset]
            if len(held) > 1:
                raise ValueError("asset {} is held in several positions; name the position_id the trade "
                                 "changes".format(trade.asset))
            target = held[0] if held else "what-if-{}".format(i)
        position = book.setdefault(target, dict(id=target, asset=trade.asset, market_value=0.0,
                                                instrument_type="linear"))
        if position["asset"] != trade.asset:
            raise ValueError("position {} holds {}, not {}".format(target, position["asset"], trade.asset))
        position["market_value"] += trade.market_value_change
    return list(book.values())


class WhatIfRequest(PortfolioRequest):
    trades: list[Trade] = Field(min_length=1, max_length=10_000)
    scenarios: list[Scenario] | None = Field(default=None, min_length=1, max_length=1000)
    asset_returns: dict[str, list[float]] | None = None
    confidence: float | None = Field(default=None, gt=0, lt=1)
    horizon_days: int | None = Field(default=None, gt=0, le=3650, strict=True)
    limits: list[Limit] | None = Field(default=None, min_length=1, max_length=1000)

    @model_validator(mode="after")
    def coherent(self):
        tail = (self.asset_returns, self.confidence, self.horizon_days)
        if any(v is not None for v in tail) and any(v is None for v in tail):
            raise ValueError("asset_returns, confidence and horizon_days are given together or not at all")
        if self.asset_returns is not None:
            assets = {p.asset for p in self.positions} | {t.asset for t in self.trades}
            if set(self.asset_returns) != assets:
                raise ValueError("asset_returns must name exactly the assets held before or after the trades")
            if len({len(r) for r in self.asset_returns.values()}) != 1 or len(next(iter(self.asset_returns.values()))) < 2:
                raise ValueError("every asset needs the same number of return observations, at least two")
        if self.limits is not None:
            _unique_names(self.limits)
        return self


def what_if(payload):
    request = WhatIfRequest.model_validate(payload)
    meta = request.model_dump(mode="json", include={"as_of", "currency", "source", "data_mode"})
    before = [p.model_dump() for p in request.positions]
    after = _apply(request.positions, request.trades)
    sides = {}
    for side, positions in (("before", before), ("after", after)):
        book = dict(meta, nav=request.nav, positions=positions)
        held = {p["asset"] for p in positions}
        results = {"exposure": portfolio_exposure(book)}
        if request.scenarios:
            # A shock to an asset the book does not hold yet has no position to act on.
            results["stress"] = stress_test(dict(book, scenarios=[
                dict(name=s.name, shocks={a: r for a, r in s.shocks.items() if a in held})
                for s in request.scenarios]))
        if request.asset_returns:
            net = results["exposure"]["net_by_asset"]
            count = len(next(iter(request.asset_returns.values())))
            pnl = [math.fsum(value*request.asset_returns[asset][t] for asset, value in net.items())
                   for t in range(count)]
            results["tail"] = tail_risk(dict(meta, pnl=pnl, confidence=request.confidence,
                                             horizon_days=request.horizon_days, portfolio_value=request.nav))
        sides[side] = results
    keys = {"exposure": ("gross_exposure", "net_exposure", "gross_leverage", "net_leverage"),
            "tail": ("var", "expected_shortfall")}
    change = {key: sides["after"][kind][key] - sides["before"][kind][key]
              for kind, names in keys.items() if kind in sides["after"] for key in names}
    if "stress" in sides["after"]:
        change["stress_loss"] = {b["name"]: a["loss"] - b["loss"] for b, a in zip(
            sides["before"]["stress"]["scenarios"], sides["after"]["stress"]["scenarios"])}
    warnings = ["{} {}: {}".format(side, kind, r["degraded_reason"])
                for side, results in sides.items() for kind, r in results.items() if r["degraded"]]
    result = envelope(request, "pre-trade what-if by revaluing the book with the trades added", [
        "Each trade is a signed change in linear market value at as-of prices, applied to the position "
        "holding its asset (or the named position_id); an asset not yet held opens a what-if-N position.",
        "NAV is unchanged: trades are assumed cash-financed with no costs, so leverage uses the same NAV.",
        "Tail P&L is net market value per asset times its supplied horizon return: a linear position's "
        "historical P&L is assumed to scale with its value. No square-root-of-time scaling.",
        "Stress shocks to assets not yet held are dropped for the before book; they act on no position."],
        warnings)
    result.update(before=sides["before"], after=sides["after"], change=change, limits_after=None)
    if request.limits:
        result["limits_after"] = check_limits(dict(meta, limits=[l.model_dump() for l in request.limits],
                                                   results=sides["after"]))
        if result["limits_after"]["degraded"]:
            warnings.append("limit check: " + result["limits_after"]["degraded_reason"])
            result.update(degraded=True, degraded_reason="; ".join(warnings))
    return result
