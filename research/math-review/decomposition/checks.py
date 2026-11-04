"""Independent checks of riskdesk.decomposition: parametric and historical Euler allocation,
covariance estimators and the factor variance split. References use plain loops and numpy
linear algebra written here; the module is only called.
"""
from fractions import Fraction
import math
from pathlib import Path
from statistics import NormalDist
import sys

import numpy as np
from scipy import integrate

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from _review import Review  # noqa: E402
from riskdesk.decomposition import (covariance_estimate, factor_exposure, historical_es,  # noqa: E402
                                    parametric_var)  # called for comparison only

META = dict(as_of="2026-11-04", currency="USD", source="independent math review", data_mode="synthetic")
REF = "plugins/risk-desk/skills/risk-attribution/reference.md"
ASSETS = ["A", "B", "C"]
POSITIONS = [dict(id="p1", asset="A", market_value=600.0, instrument_type="linear"),
             dict(id="p2", asset="A", market_value=-150.0, instrument_type="linear"),
             dict(id="p3", asset="B", market_value=400.0, instrument_type="linear"),
             dict(id="p4", asset="C", market_value=-250.0, instrument_type="linear")]
COV = [[0.0004, 0.00012, -0.00005], [0.00012, 0.0009, 0.0002], [-0.00005, 0.0002, 0.0016]]
N = NormalDist()


def exposure():
    return [sum(p["market_value"] for p in POSITIONS if p["asset"] == a) for a in ASSETS]


def sigma_of(e):
    return math.sqrt(sum(e[i] * COV[i][j] * e[j] for i in range(3) for j in range(3)))


def main():
    r = Review("decomposition", "Euler allocation, covariance and factor split: independent numerical review", __file__)
    c = 0.99
    z = N.inv_cdf(c)
    e = exposure()
    sigma = sigma_of(e)
    out = parametric_var(dict(META, nav=1000.0, positions=POSITIONS, assets=ASSETS, covariance=COV,
                              confidence=c, horizon_days=1))
    r.close("param-var", "VaR = z sqrt(e' Sigma e) by loops", f"{REF}:70-72", z * sigma, out["var"], rel_tol=1e-12)
    es_quad = integrate.quad(lambda u: sigma * N.inv_cdf(u), c, 1, limit=200)[0] / (1 - c)
    r.close("param-es-quadrature", "normal ES = integral of the quantile over (c,1) / (1-c)", f"{REF}:72-74",
            es_quad, out["expected_shortfall"], rel_tol=1e-7)
    rows = {row["id"]: row for row in out["positions"]}
    r.close("param-euler-sum-var", "component VaRs sum to VaR", f"{REF}:79-81, Tasche (2008) Eq. (2.6)",
            out["var"], math.fsum(row["component_var"] for row in rows.values()), rel_tol=1e-12)
    r.close("param-euler-sum-es", "component ESs sum to ES", f"{REF}:79-81", out["expected_shortfall"],
            math.fsum(row["component_es"] for row in rows.values()), rel_tol=1e-12)
    h = 1e-3
    for p in POSITIONS:  # Euler component = x_j dVaR/dx_j, slope by central difference of the loop VaR
        i = ASSETS.index(p["asset"])
        up, down = list(e), list(e)
        up[i] += h
        down[i] -= h
        slope = z * (sigma_of(up) - sigma_of(down)) / (2 * h)
        r.close(f"param-component-{p['id']}", f"component VaR of {p['id']} = x dVaR/dx (central difference)",
                f"{REF}:75-80", p["market_value"] * slope, rows[p["id"]]["component_var"], rel_tol=1e-7)
        without = list(e)
        without[i] -= p["market_value"]
        r.close(f"param-incremental-{p['id']}", f"incremental VaR of {p['id']} by full recomputation",
                f"{REF}:83-87", z * sigma - z * sigma_of(without), rows[p["id"]]["incremental_var"], rel_tol=1e-10)

    rng = np.random.default_rng(42)
    returns = (rng.standard_normal((203, 3)) @ np.linalg.cholesky(np.array(COV)).T).tolist()
    for conf in (0.95, 0.99, 0.975):
        out = historical_es(dict(META, nav=1000.0, positions=POSITIONS, assets=ASSETS, returns=returns,
                                 confidence=conf, horizon_days=1))
        per = [[-row[ASSETS.index(p["asset"])] * p["market_value"] for p in POSITIONS] for row in returns]
        total = [math.fsum(x) for x in per]
        order = sorted(range(len(total)), key=lambda t: -total[t])
        m = len(total) * (1 - Fraction(str(conf)))
        weights = [1.0] * math.floor(m) + [float(m - math.floor(m))]
        es = math.fsum(w * total[t] for w, t in zip(weights, order)) / float(m)
        r.close(f"hist-es-c{conf}", f"historical ES by sorted losses, T=203, c={conf}", f"{REF}:93-100",
                es, out["expected_shortfall"], rel_tol=1e-12)
        comps = {p["id"]: math.fsum(w * per[t][j] for w, t in zip(weights, order)) / float(m)
                 for j, p in enumerate(POSITIONS)}
        for row in out["positions"]:
            r.close(f"hist-component-{row['id']}-c{conf}", f"tail-weighted loss of {row['id']}, c={conf}",
                    f"{REF}:101-106, Tasche (2008) Eq. (3.11a)", comps[row["id"]], row["component_es"],
                    rel_tol=1e-10, abs_tol=1e-12)

    x = np.array(returns)
    out = covariance_estimate(dict(META, assets=ASSETS, returns=returns, horizon_days=1, method="sample"))
    mean = x.mean(axis=0)
    sample = [[sum((row[i] - mean[i]) * (row[j] - mean[j]) for row in x) / (len(x) - 1) for j in range(3)]
              for i in range(3)]
    r.close("cov-sample", "sample covariance, worst element, divisor T-1", f"{REF}:36", 0.0,
            float(np.max(np.abs(np.array(out["covariance"]) - sample))), abs_tol=1e-15)
    lam = 0.94
    out = covariance_estimate(dict(META, assets=ASSETS, returns=returns, horizon_days=1, method="ewma", decay=lam))
    rec = np.outer(x[0], x[0])  # RiskMetrics recursion with exact finite-sample normalisation
    total_w = 1.0
    for row in x[1:]:
        rec, total_w = lam * total_w / (lam * total_w + 1) * rec + np.outer(row, row) / (lam * total_w + 1), lam * total_w + 1
    r.close("cov-ewma-recursion", "EWMA covariance against a normalised recursion, worst element",
            f"{REF}:37-48", 0.0, float(np.max(np.abs(np.array(out["covariance"]) - rec))), abs_tol=1e-15)

    factors = (rng.standard_normal((203, 2)) * 0.01).tolist()
    out = factor_exposure(dict(META, nav=1000.0, positions=POSITIONS, assets=ASSETS, returns=returns,
                               factors=["F1", "F2"], factor_returns=factors, horizon_days=1))
    design = np.column_stack([np.ones(203), factors])
    coef = np.linalg.solve(design.T @ design, design.T @ x)  # normal equations, not lstsq
    beta_err = max(abs(out["assets"][a]["betas"][f] - coef[k + 1, i])
                   for i, a in enumerate(ASSETS) for k, f in enumerate(["F1", "F2"]))
    r.close("factor-betas-normal-equations", "OLS betas against the normal equations, worst difference",
            f"{REF}:114-115", 0.0, beta_err, abs_tol=1e-12)
    v = out["variance"]
    r.close("factor-split-adds", "systematic + idiosyncratic = total variance in sample", f"{REF}:120-123",
            v["total"], v["systematic"] + v["idiosyncratic"], rel_tol=1e-10)
    return r.write()


if __name__ == "__main__":
    main()
