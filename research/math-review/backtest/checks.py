"""Independent checks of riskdesk.backtest.var_backtest.

References are computed here with exact binomial sums (fractions), hand-written
likelihood ratios and stdlib chi-square tails; the module is only called.
"""
from fractions import Fraction
import math
from pathlib import Path
import sys

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from _review import Review  # noqa: E402
from riskdesk.backtest import var_backtest  # noqa: E402  (called for comparison only)

META = dict(as_of="2026-11-04", currency="USD", source="independent math review", data_mode="synthetic")
REF = "plugins/risk-desk/skills/risk-backtest/reference.md"


def binom_cdf(x, n, p=Fraction(1, 100)):
    return float(sum(math.comb(n, k) * p**k * (1 - p)**(n - k) for k in range(x + 1)))


def first_at_or_above(n, level):
    return next(x for x in range(n + 1) if binom_cdf(x, n) >= level)


def series(hits):
    """P&L of -2 on an exception day and +1 otherwise, against a VaR of 1."""
    return [-2.0 if h else 1.0 for h in hits], [1.0] * len(hits)


def chi2_sf(lr, dof):
    return math.erfc(math.sqrt(lr / 2)) if dof == 1 else math.exp(-lr / 2)  # chi-square 1 and 2 tails


def xlogy(a, b):
    return 0.0 if a == 0 else a * math.log(b)


def main():
    r = Review("backtest", "VaR and ES backtests: independent numerical review", __file__)
    table2 = {0: 8.11, 1: 28.58, 2: 54.32, 3: 75.81, 4: 89.22, 5: 95.88, 6: 98.63, 7: 99.60,
              8: 99.89, 9: 99.97, 10: 99.99}  # MAR99 Table 2 cumulative %, as transcribed in REF:58-59
    for x in range(11):
        pnl, var = series([True] * x + [False] * (250 - x))
        out = var_backtest(dict(META, pnl=pnl, var=var, confidence=0.99, horizon_days=1))["basel_traffic_light"]
        exact = binom_cdf(x, 250)
        zone = "green" if x <= 4 else "amber" if x <= 9 else "red"  # MAR99.17 Table 2 zones, REF:48-49
        r.close(f"basel-cdf-{x}", f"P(Bin(250,0.01) <= {x})", "exact binomial sum", exact,
                out["cumulative_probability"], rel_tol=1e-12)
        r.close(f"basel-table2-{x}", f"exact CDF vs MAR99 Table 2 at {x}, percent", f"{REF}:58-59 (two decimals)",
                table2[x], round(100 * exact, 2), abs_tol=1e-9, compared="published")
        r.equal(f"basel-zone-{x}", f"zone at {x} exceptions of 250", f"MAR99.17 Table 2 ({REF}:48-49)",
                zone, out["zone"])
    for n in (250, 500, 1000):
        pnl, var = series([False] * n)
        out = var_backtest(dict(META, pnl=pnl, var=var, confidence=0.99, horizon_days=1))["basel_traffic_light"]
        r.equal(f"basel-bounds-{n}", f"amber and red starts for T={n}",
                f"MAR99.17 rule: first count with CDF >= 95% and >= 99.99% ({REF}:49-52)",
                [first_at_or_above(n, Fraction(95, 100)), first_at_or_above(n, Fraction(9999, 10000))],
                [out["amber_from"], out["red_from"]])

    # Kupiec POF and Christoffersen on one hand-built hit sequence: clustered exceptions.
    hits = [False] * 240 + [True, True, True, False, True, True, False, False, True, False]
    n, x, p = len(hits), sum(hits), 0.01
    pnl, var = series(hits)
    out = var_backtest(dict(META, pnl=pnl, var=var, confidence=0.99, horizon_days=1))
    lr_pof = -2 * (xlogy(n - x, 1 - p) + xlogy(x, p) - xlogy(n - x, 1 - x / n) - xlogy(x, x / n))
    r.close("kupiec-lr", f"Kupiec LR, {x} of {n} at p=0.01", "Kupiec (1995) as stated in REF:17", lr_pof,
            out["kupiec_pof"]["lr"], rel_tol=1e-12)
    r.close("kupiec-p", "Kupiec p-value, chi-square(1) tail by erfc", "REF:17", chi2_sf(lr_pof, 1),
            out["kupiec_pof"]["p_value"], rel_tol=1e-9)
    counts = {(a, b): 0 for a in (0, 1) for b in (0, 1)}
    for a, b in zip(hits, hits[1:]):
        counts[(int(a), int(b))] += 1
    n00, n01, n10, n11 = counts[(0, 0)], counts[(0, 1)], counts[(1, 0)], counts[(1, 1)]
    pi0, pi1, pi = n01 / (n00 + n01), n11 / (n10 + n11), (n01 + n11) / (n - 1)
    markov = xlogy(n00, 1 - pi0) + xlogy(n01, pi0) + xlogy(n10, 1 - pi1) + xlogy(n11, pi1)
    lr_ind = -2 * (xlogy(n00 + n10, 1 - pi) + xlogy(n01 + n11, pi) - markov)
    lr_cc = -2 * (xlogy(n00 + n10, 1 - p) + xlogy(n01 + n11, p) - markov)
    src = "Christoffersen (1998) as stated in REF:28-35"
    r.close("christoffersen-ind", "LR_ind by hand transition counts", src, lr_ind,
            out["christoffersen_independence"]["lr"], rel_tol=1e-12)
    r.close("christoffersen-cc", "LR_cc by hand transition counts", src, lr_cc,
            out["christoffersen_conditional_coverage"]["lr"], rel_tol=1e-12)
    r.close("christoffersen-cc-p", "LR_cc p-value, chi-square(2) tail exp(-x/2)", src, chi2_sf(lr_cc, 2),
            out["christoffersen_conditional_coverage"]["p_value"], rel_tol=1e-9)

    # Acerbi-Szekely Z2 by hand, and its p-value under the normal null by a separate simulation.
    rng = np.random.default_rng(20261104)
    c, alpha, t = 0.975, 0.025, 250
    z = 1.959963984540054  # Phi^-1(0.975)
    es_unit = math.exp(-z * z / 2) / math.sqrt(2 * math.pi) / alpha
    pnl = (1.1 * rng.standard_normal(t)).tolist()  # risk understated by 10 percent
    var, es = [z] * t, [es_unit] * t
    out = var_backtest(dict(META, pnl=pnl, var=var, expected_shortfall=es, es_null="normal",
                            confidence=c, horizon_days=1, seed=0))["es_backtest"]
    z2 = sum(x * (x + v < 0) / e for x, v, e in zip(pnl, var, es)) / (t * alpha) + 1
    r.close("z2", "Acerbi-Szekely Z2 by hand loop", "REF:67", z2, out["z2"], rel_tol=1e-12)
    sims = 20_000  # forecasts are N(0,1) quantiles, so the stated normal null is N(0,1) itself
    draws = rng.standard_normal((sims, t))
    sim_z2 = (draws * (draws + z < 0)).sum(axis=1) / (es_unit * t * alpha) + 1
    p_ref = (np.sum(sim_z2 <= z2) + 1) / (sims + 1)
    se = math.sqrt(p_ref * (1 - p_ref) / sims + out["p_value"] * (1 - out["p_value"]) / out["simulations"])
    r.close("z2-p-normal-null", "Z2 p-value, independent 20,000-draw simulation (4 combined SE)",
            "REF:72-82 null construction", p_ref, out["p_value"], abs_tol=4 * se)
    return r.write()


if __name__ == "__main__":
    main()
