"""Books that mix linear positions and European options.

Every price and every Greek comes from optiondesk_engine: Black-Scholes-Merton
(bs_price, all_greeks) for a spot underlying, Black-76 (black76_price,
black76_greeks) for a futures underlying, and net_greeks for aggregation.
One correction is made here and stated: black76_greeks returns all_greeks'
partial in r with the carry rate held fixed, which is not Black-76 rho. With
the future held fixed, dV/dr = -t * V, so that is reported instead.
"""
import math
from datetime import date
from typing import Literal

from pydantic import Field, model_validator

from optiondesk_engine.pricing.black_scholes import DAYS_PER_YEAR, bs_price, intrinsic
from optiondesk_engine.pricing.forwards import black76_greeks, black76_price
from optiondesk_engine.pricing.greeks_full import all_greeks, net_greeks

from riskdesk.analytics import envelope, tail_risk
from riskdesk.models import Provenance, StrictModel

MAX_REVALUATIONS = 2_000_000  # about one second of pure Python engine pricing


class Underlying(StrictModel):
    price: float = Field(gt=0)
    price_type: Literal["spot", "future"]


class BookPosition(StrictModel):
    id: str = Field(min_length=1)
    underlying: str = Field(min_length=1)
    instrument_type: Literal["linear", "option"]
    quantity: float
    multiplier: float = Field(gt=0)
    kind: Literal["call", "put"] | None = None
    strike: float | None = Field(default=None, gt=0)
    expiry: date | None = None
    year_fraction: float | None = Field(default=None, gt=0)
    implied_vol: float | None = Field(default=None, gt=0)
    rate: float | None = None
    carry_yield: float | None = None

    @model_validator(mode="after")
    def option_fields(self):
        terms = (self.kind, self.strike, self.implied_vol, self.rate, self.carry_yield,
                 self.expiry, self.year_fraction)
        if self.instrument_type == "linear":
            if any(v is not None for v in terms):
                raise ValueError(f"linear position {self.id} must not carry option terms")
            return self
        if None in (self.kind, self.strike, self.implied_vol, self.rate):
            raise ValueError(f"option {self.id} needs kind, strike, implied_vol and rate")
        if (self.expiry is None) == (self.year_fraction is None):
            raise ValueError(f"option {self.id} needs exactly one of expiry or year_fraction")
        return self


class DerivativesBookRequest(Provenance):
    underlyings: dict[str, Underlying] = Field(min_length=1)
    positions: list[BookPosition] = Field(min_length=1, max_length=10_000)

    @model_validator(mode="after")
    def consistent_book(self):
        if len({p.id for p in self.positions}) != len(self.positions):
            raise ValueError("position ids must be unique")
        for p in self.positions:
            if p.underlying not in self.underlyings:
                raise ValueError(f"position {p.id} names unknown underlying {p.underlying}")
            if p.instrument_type != "option":
                continue
            future = self.underlyings[p.underlying].price_type == "future"
            if future and p.carry_yield is not None:
                raise ValueError(f"option {p.id} is on a future; Black-76 takes no carry_yield")
            if not future and p.carry_yield is None:
                raise ValueError(f"option {p.id} is on a spot underlying and needs carry_yield (0 if none)")
            if p.expiry is not None and p.expiry <= self.as_of:
                raise ValueError(f"option {p.id} expires on or before as_of")
        return self


class ScenarioGridRequest(DerivativesBookRequest):
    spot_shocks: list[float] = Field(min_length=1, max_length=101)
    vol_shocks: list[float] = Field(min_length=1, max_length=101)

    @model_validator(mode="after")
    def valid_shocks(self):
        if any(s <= -1 for s in self.spot_shocks):
            raise ValueError("spot shocks are simple returns and must be above -100%")
        _check_size(self, len(self.spot_shocks) * len(self.vol_shocks))
        return self


class HistoricalScenario(StrictModel):
    spot_returns: dict[str, float] = Field(min_length=1)
    vol_changes: dict[str, float] | None = None


class HistoricalPnlRequest(DerivativesBookRequest):
    scenarios: list[HistoricalScenario] = Field(min_length=2, max_length=100_000)
    horizon_days: int = Field(gt=0, le=3650, strict=True)
    time_mode: Literal["fixed", "decay"]
    confidence: float = Field(gt=0, lt=1)
    portfolio_value: float = Field(gt=0)

    @model_validator(mode="after")
    def complete_scenarios(self):
        names = set(self.underlyings)
        for i, s in enumerate(self.scenarios):
            if set(s.spot_returns) != names or (s.vol_changes is not None and set(s.vol_changes) != names):
                raise ValueError(f"scenario {i} must name exactly the book underlyings")
            if any(r <= -1 for r in s.spot_returns.values()):
                raise ValueError(f"scenario {i} has a spot return at or below -100%")
        _check_size(self, len(self.scenarios))
        return self


def _check_size(request, cells):
    options = sum(p.instrument_type == "option" for p in request.positions)
    if options * cells > MAX_REVALUATIONS:
        raise ValueError(f"{options} options x {cells} scenarios exceeds {MAX_REVALUATIONS} revaluations")


def _years(p, as_of):
    return p.year_fraction if p.expiry is None else (p.expiry - as_of).days / DAYS_PER_YEAR


def _future(request, p):
    return request.underlyings[p.underlying].price_type == "future"


def _value(request, p, price, vol_change=0.0, elapsed_years=0.0):
    """Per-unit model value of one position at a shocked price and vol."""
    if p.instrument_type == "linear":
        return price
    t = _years(p, request.as_of) - elapsed_years
    if t <= 0:  # life ends inside the horizon: settle at payoff on the shocked price
        return intrinsic(price, p.strike, p.kind)
    sigma = p.implied_vol + vol_change
    if sigma <= 0:
        raise ValueError(f"vol change takes option {p.id} to a non-positive volatility")
    if _future(request, p):
        return black76_price(price, p.strike, t, sigma, p.kind, p.rate)
    return bs_price(price, p.strike, t, sigma, p.kind, p.rate, p.carry_yield)


def _greeks(request, p):
    if p.instrument_type == "linear":
        return dict(price=request.underlyings[p.underlying].price, delta=1.0, gamma=0.0,
                    vega=0.0, theta=0.0, rho=0.0, vanna=0.0, vomma=0.0, charm=0.0, veta=0.0)
    t, S = _years(p, request.as_of), request.underlyings[p.underlying].price
    if _future(request, p):
        g = black76_greeks(S, p.strike, t, p.implied_vol, p.kind, p.rate)
        g["rho"] = -t * g["price"]  # Black-76 rho with the future held fixed; see module docstring
        return g
    return all_greeks(S, p.strike, t, p.implied_vol, p.kind, p.rate, p.carry_yield)


def _per_underlying(request):
    """Engine net Greeks per underlying, in units of underlying (quantity x multiplier)."""
    out = {}
    for name in request.underlyings:
        legs = [(_greeks(request, p), p.quantity * p.multiplier)
                for p in request.positions if p.underlying == name]
        if legs:
            out[name] = net_greeks(legs)
    return out


def _finite(*values):
    if not all(math.isfinite(v) for v in values):
        raise ValueError("derivatives calculation exceeded numerical limits")


GREEK_UNITS = {
    "cash_delta": "currency change per 1.00 relative move in the underlying, delta x quantity x multiplier x price",
    "cash_gamma_1pct": "change in cash_delta for a 1% rise in the underlying, gamma x quantity x multiplier x price^2 / 100",
    "vega_per_vol_point": "currency change for +0.01 (one point) of implied volatility; engine vega is per 1.00",
    "theta_per_day": "currency change as one calendar day passes (engine convention, ACT/365); negative is decay",
    "rho_per_rate_point": "currency change for +0.01 of the continuously compounded rate; engine rho is per 1.00",
}
CONVENTIONS = [
    "Prices and Greeks from optiondesk_engine: Black-Scholes-Merton for spot underlyings, Black-76 for futures.",
    "Time is ACT/365 years; an expiry date is converted as (expiry - as_of) days / 365.",
    "Black-76 rho is -t x V with the future fixed; the engine's black76_greeks rho holds the carry rate fixed and is not used.",
    "European exercise, one flat implied volatility per option, rates and carry continuously compounded.",
    "All prices and amounts are in the stated currency; no FX translation is performed.",
]


def book_greeks(payload):
    request = DerivativesBookRequest.model_validate(payload)
    rows, keys = {}, ("option_model_value", "linear_notional") + tuple(GREEK_UNITS)
    for name, net in _per_underlying(request).items():
        S = request.underlyings[name].price
        opts = [p for p in request.positions if p.underlying == name and p.instrument_type == "option"]
        row = dict(price=S, price_type=request.underlyings[name].price_type,
                   option_model_value=math.fsum(_value(request, p, S) * p.quantity * p.multiplier for p in opts),
                   linear_notional=math.fsum(p.quantity * p.multiplier * S for p in request.positions
                                             if p.underlying == name and p.instrument_type == "linear"),
                   cash_delta=net["delta"] * S, cash_gamma_1pct=net["gamma"] * S * S / 100,
                   vega_per_vol_point=net["vega"] / 100, theta_per_day=net["theta"],
                   rho_per_rate_point=net["rho"] / 100, positions=net["legs"])
        _finite(*(row[k] for k in keys))
        rows[name] = row
    total = {k: math.fsum(r[k] for r in rows.values()) for k in keys}
    _finite(*total.values())
    result = envelope(request, "book Greeks via optiondesk_engine", CONVENTIONS + [
        "Totals add per-underlying figures: total gamma ignores cross-gamma, total vega is a parallel shift of every vol."])
    result.update(units=GREEK_UNITS, by_underlying=rows, total=total)
    return result


def _revalue(request, returns, vol_changes, elapsed_years=0.0):
    """Full-revaluation P&L of the book for per-underlying returns and vol changes."""
    pnl = []
    for p in request.positions:
        S = request.underlyings[p.underlying].price
        new = _value(request, p, S * (1 + returns[p.underlying]), vol_changes.get(p.underlying, 0.0), elapsed_years)
        old = _value(request, p, S)
        pnl.append((new - old) * p.quantity * p.multiplier)
    return math.fsum(pnl)


def scenario_grid(payload):
    request = ScenarioGridRequest.model_validate(payload)
    nets = _per_underlying(request)
    cells = []
    for ds in request.spot_shocks:
        for dv in request.vol_shocks:
            full = _revalue(request, dict.fromkeys(request.underlyings, ds), dict.fromkeys(request.underlyings, dv))
            moves = {u: request.underlyings[u].price * ds for u in nets}
            dg = math.fsum(n["delta"] * moves[u] + 0.5 * n["gamma"] * moves[u] ** 2 for u, n in nets.items())
            dgv = dg + math.fsum(n["vega"] * dv for n in nets.values())
            _finite(full, dg, dgv)
            cells.append(dict(spot_shock=ds, vol_shock=dv, full_pnl=full, full_loss=-full,
                              delta_gamma_pnl=dg, delta_gamma_vega_pnl=dgv,
                              delta_gamma_error=dg - full, delta_gamma_vega_error=dgv - full))
    result = envelope(request, "joint spot and vol scenario grid: full revaluation versus Taylor approximations", CONVENTIONS + [
        "Each cell applies the same relative spot shock to every underlying and adds the same absolute vol shock to every option.",
        "Instantaneous shocks: time to expiry is held fixed, so theta does not enter.",
        "Approximation error is approximation P&L minus full-revaluation P&L. Positive P&L is profit.",
        "Delta-gamma-vega adds first-order vega only; vanna and vomma are not in either approximation."])
    result.update(spot_shocks=request.spot_shocks, vol_shocks=request.vol_shocks, cells=cells,
                  max_abs_delta_gamma_error=max(abs(c["delta_gamma_error"]) for c in cells),
                  max_abs_delta_gamma_vega_error=max(abs(c["delta_gamma_vega_error"]) for c in cells))
    return result


def historical_pnl(payload):
    request = HistoricalPnlRequest.model_validate(payload)
    elapsed = request.horizon_days / DAYS_PER_YEAR if request.time_mode == "decay" else 0.0
    pnl = [_revalue(request, s.spot_returns, s.vol_changes or {}, elapsed) for s in request.scenarios]
    _finite(*pnl)
    settled = sorted(p.id for p in request.positions
                     if p.instrument_type == "option" and _years(p, request.as_of) <= elapsed)
    tail = tail_risk(dict(as_of=request.as_of.isoformat(), currency=request.currency, source=request.source,
                          data_mode=request.data_mode, pnl=pnl, confidence=request.confidence,
                          horizon_days=request.horizon_days, portfolio_value=request.portfolio_value))
    warnings = [tail["degraded_reason"]] if tail["degraded"] else []
    time_note = ("Time decays by horizon_days / 365 years in every scenario." if elapsed else
                 "Time to expiry is held fixed: the P&L excludes theta over the horizon.")
    result = envelope(request, "historical full-revaluation P&L of a derivatives book, tail via tail_risk", CONVENTIONS + [
        time_note,
        "Spot returns are simple returns applied to each underlying price; vol changes are absolute and parallel per underlying.",
        "A scenario without vol_changes holds every implied volatility at its supplied level.",
        "An option whose life ends inside the horizon is valued at its undiscounted payoff on the shocked price."], warnings)
    result.update(time_mode=request.time_mode, horizon_days=request.horizon_days, pnl=pnl,
                  scenarios_without_vol_changes=sum(s.vol_changes is None for s in request.scenarios),
                  options_settled_within_horizon=settled, tail=tail)
    return result
