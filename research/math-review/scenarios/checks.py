"""Independent checks of riskdesk.scenarios.reverse_stress and scale_scenario.

For two assets the equal-loss set w's = -L is a line. The most plausible shock is found here
by a dense grid then ternary search of the Mahalanobis distance along that line, using the
explicit 2x2 inverse, with no Lagrangian, no Cholesky factor and no optimiser.
"""
import math
from pathlib import Path
from statistics import NormalDist
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from _review import Review  # noqa: E402
from riskdesk.scenarios import reverse_stress, scale_scenario  # noqa: E402  (called for comparison only)

META = dict(as_of="2026-11-04", currency="USD", source="independent math review", data_mode="synthetic")
REF = "plugins/risk-desk/skills/risk-stress/reference.md"
COV = [[0.04, 0.01], [0.01, 0.09]]


def distance(s):
    (a, b), (_, d) = COV
    det = a * d - b * b
    return math.sqrt((d * s[0] ** 2 - 2 * b * s[0] * s[1] + a * s[1] ** 2) / det)


def brute_force(w, loss, lo, hi):
    """Minimise distance over s0 in [lo, hi] with s1 = (-loss - w0 s0) / w1."""
    shock = lambda t: (t, (-loss - w[0] * t) / w[1])
    grid = [lo + (hi - lo) * k / 100_000 for k in range(100_001)]
    best = min(grid, key=lambda t: distance(shock(t)))
    a, b = max(lo, best - (hi - lo) / 100_000), min(hi, best + (hi - lo) / 100_000)
    for _ in range(200):
        m1, m2 = a + (b - a) / 3, b - (b - a) / 3
        a, b = (m1, b) if distance(shock(m1)) > distance(shock(m2)) else (a, m2)
    return shock((a + b) / 2)


def book(w):
    return [dict(id=f"p{i}", asset=name, market_value=v, instrument_type="linear")
            for i, (name, v) in enumerate(zip("AB", w))]


def main():
    r = Review("scenarios", "Reverse stress and scenario scaling: independent numerical review", __file__)
    cases = [("unbounded", [1000.0, -400.0], 150.0, {}, (-5.0, 5.0)),
             ("floor-binds", [1000.0, 500.0], 600.0, {"A": -0.3}, (-0.3, -0.1))]
    for name, w, loss, floors, (lo, hi) in cases:
        out = reverse_stress(dict(META, nav=2000.0, positions=book(w), target_loss=loss, horizon_days=10,
                                  assets=["A", "B"], covariance=COV, floors=floors))
        s = brute_force(w, loss, lo, hi)
        r.close(f"{name}-distance", "Mahalanobis distance vs search along the equal-loss line",
                f"{REF}:121-156", distance(s), out["mahalanobis_distance"], rel_tol=1e-8)
        for asset, value in zip("AB", s):
            r.close(f"{name}-shock-{asset}", f"most plausible shock to {asset}", f"{REF}:121-156",
                    value, out["shocks"][asset], abs_tol=1e-6)
        r.close(f"{name}-revalued-loss", "the shocks revalue to the target loss", f"{REF}:137-138",
                loss, out["scenarios"][0]["loss"], rel_tol=1e-9)
        if name == "unbounded":
            sd = math.sqrt(sum(w[i] * COV[i][j] * w[j] for i in range(2) for j in range(2)))
            r.close("unbounded-normal-probability", "P(loss >= L) = Phi(-L / sqrt(w' Sigma w))",
                    f"{REF}:158-164", NormalDist().cdf(-loss / sd), out["loss_exceedance_probability_if_normal"],
                    rel_tol=1e-9)

    scenario = dict(name="sell-off", shocks={"A": -0.05, "B": 0.02})
    out = scale_scenario(dict(META, nav=2000.0, positions=book([1000.0, -400.0]), scenario=scenario,
                              target_loss=180.0))
    base = -(1000.0 * -0.05 + -400.0 * 0.02)
    r.close("scale-multiple", "k = target loss / scenario loss", f"{REF}:168-172", 180.0 / base, out["multiple"],
            rel_tol=1e-12)
    r.close("scale-loss", "scaled scenario revalues to the target loss", f"{REF}:168-172", 180.0,
            out["scenarios"][-1]["loss"], rel_tol=1e-12)
    return r.write()


if __name__ == "__main__":
    main()
