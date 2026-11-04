"""Independent checks of riskdesk.derivatives.book_greeks: Black-Scholes-Merton and Black-76
prices written here with the stdlib NormalDist, and every rho as a central finite difference
of those prices in the rate. The Option Desk engine is not used for the references.
"""
import math
from pathlib import Path
from statistics import NormalDist
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from _review import Review  # noqa: E402
from riskdesk.derivatives import book_greeks  # noqa: E402  (called for comparison only)

META = dict(as_of="2026-11-04", currency="USD", source="independent math review", data_mode="synthetic")
REF = "plugins/risk-desk/skills/risk-derivatives/reference.md"
N = NormalDist().cdf


def bsm(s, k, t, vol, kind, r, q):
    d1 = (math.log(s / k) + (r - q + vol * vol / 2) * t) / (vol * math.sqrt(t))
    d2 = d1 - vol * math.sqrt(t)
    if kind == "call":
        return s * math.exp(-q * t) * N(d1) - k * math.exp(-r * t) * N(d2)
    return k * math.exp(-r * t) * N(-d2) - s * math.exp(-q * t) * N(-d1)


def black76(f, k, t, vol, kind, r):
    return bsm(f, k, t, vol, kind, r, r)  # F e^{-rt} N(d1) - K e^{-rt} N(d2): carry equals the rate


def main():
    r = Review("derivatives", "Option book Greeks: independent numerical review", __file__)
    h = 1e-6
    for kind in ("call", "put"):
        for label, price_type, fn, extra in (("future", "future", black76, {}),
                                             ("spot", "spot", bsm, {"carry_yield": 0.02})):
            pos = dict(id="o", underlying="U", instrument_type="option", quantity=3.0, multiplier=10.0, kind=kind,
                       strike=95.0, year_fraction=0.75, implied_vol=0.3, rate=0.05, **extra)
            out = book_greeks(dict(META, underlyings={"U": dict(price=100.0, price_type=price_type)},
                                   positions=[pos]))["by_underlying"]["U"]
            args = (100.0, 95.0, 0.75, 0.3, kind)
            price = lambda rate: fn(*args, rate) if label == "future" else fn(*args, rate, 0.02)
            rho = (price(0.05 + h) - price(0.05 - h)) / (2 * h) * 30 / 100
            src = f"{REF}:31-37 (Black-76, future held fixed)" if label == "future" else f"{REF}:9-13"
            r.close(f"rho-{label}-{kind}", f"{label} {kind} rho per rate point, central difference", src,
                    rho, out["rho_per_rate_point"], rel_tol=1e-7)
            r.close(f"value-{label}-{kind}", f"{label} {kind} model value, own closed form", src,
                    price(0.05) * 30, out["option_model_value"], rel_tol=1e-12)
    return r.write()


if __name__ == "__main__":
    main()
