"""Independent checks of riskdesk.analytics.tail_risk and riskdesk.tail_models.tail_models.

Historical VaR and ES are recomputed from sorted losses with exact tail mass.
Closed-form ES (normal, Student-t, EVT) is checked by numerical integration
with scipy.integrate.quad, which is independent of the closed forms. The
Student-t and GPD parameters are the module's own maximum likelihood fits: the
fits are not re-estimated, only the formulas applied to them.
"""
from fractions import Fraction
import math
from pathlib import Path
from statistics import NormalDist, fmean, pstdev
import sys

import numpy as np
from scipy import integrate, stats

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from _review import Review  # noqa: E402
from riskdesk.analytics import tail_risk  # noqa: E402  (called for comparison only)
from riskdesk.tail_models import tail_models  # noqa: E402  (called for comparison only)

META = dict(as_of="2026-11-04", currency="USD", source="independent math review", data_mode="synthetic")
REF = "plugins/risk-desk/skills/risk-tail/reference.md"


def historical(losses, q):
    """VaR is the ceil(m)-th largest loss; ES averages the m largest with a fractional last weight."""
    ordered = sorted(losses, reverse=True)
    m = len(ordered) * (1 - Fraction(str(q)))
    whole = math.floor(m)
    tail = math.fsum(ordered[:whole]) + float(m - whole) * (ordered[whole] if whole < len(ordered) else 0.0)
    return ordered[math.ceil(m) - 1], tail / float(m)


def main():
    r = Review("tail", "Historical, parametric and EVT tail measures: independent numerical review", __file__)
    rng = np.random.default_rng(1104)
    for n, q in ((20, 0.95), (37, 0.9), (1000, 0.99), (250, 0.975)):
        pnl = (rng.standard_t(4, n) * 1000).tolist()
        out = tail_risk(dict(META, pnl=pnl, confidence=q, horizon_days=1, portfolio_value=1e6))
        var, es = historical([-x for x in pnl], q)
        src = "order statistic and fractional tail mass, analytics.py:32-48"
        r.close(f"hs-var-n{n}-q{q}", f"historical VaR, n={n}, q={q}", src, var, out["var"], rel_tol=1e-12)
        r.close(f"hs-es-n{n}-q{q}", f"historical ES, n={n}, q={q}", src, es, out["expected_shortfall"], rel_tol=1e-12)

    q, pv = 0.99, 1e6
    pnl = (rng.standard_t(4, 1000) * 0.01 * pv).tolist()
    out = tail_models(dict(META, pnl=pnl, confidence=q, horizon_days=1, portfolio_value=pv))
    methods = out["methods"]
    losses = [-x / pv for x in pnl]

    m, s, nd = fmean(losses), pstdev(losses), NormalDist()
    es_int = integrate.quad(lambda u: m + s * nd.inv_cdf(u), q, 1, limit=200)[0] / (1 - q)
    r.close("normal-var", "normal VaR from stdlib mean, divisor-n sd and inverse CDF", f"{REF}:22-25",
            (m + s * nd.inv_cdf(q)) * pv, methods["normal"]["var"], rel_tol=1e-9)
    r.close("normal-es-quadrature", "normal ES = integral of the fitted quantile over (q,1) / (1-q)",
            f"{REF}:9-10, 25", es_int * pv, methods["normal"]["expected_shortfall"], rel_tol=1e-7)

    t = methods["student_t"]
    nu, loc, scale = t["dof"], t["loc"], t["scale"]
    x = stats.t.ppf(q, nu)
    tail_mean = integrate.quad(lambda y: y * stats.t.pdf(y, nu), x, np.inf)[0] / (1 - q)
    r.close("student-t-es-integral", "Student-t ES by integrating y g(y) over the tail, module fit",
            f"{REF}:35-40", (loc + scale * tail_mean) * pv, t["expected_shortfall"], rel_tol=1e-7)

    e = methods["evt_pot"]
    xi, beta, u, k, n = e["xi"], e["beta"], e["threshold"], e["exceedances"], len(losses)
    survival = lambda y: (k / n) * (1 + xi * (y - u) / beta) ** (-1 / xi)  # McNeil and Frey eq. (9)
    var_evt = e["var"] / pv
    r.close("evt-var-inverts-eq9", "EVT VaR put back into eq. (9) gives 1-q", f"{REF}:53-56", 1 - q,
            survival(var_evt), rel_tol=1e-9)
    upper = u + beta / -xi if xi < 0 else np.inf
    es_evt = var_evt + integrate.quad(survival, var_evt, upper, limit=200)[0] / (1 - q)
    r.close("evt-es-integral", "EVT ES = VaR + integral of the GPD tail survival / (1-q)", f"{REF}:58-62",
            es_evt * pv, e["expected_shortfall"], rel_tol=1e-7)
    r.close("evt-threshold", "threshold is the (k+1)th largest loss, k = floor(0.10 n)", f"{REF}:48-50",
            sorted(losses, reverse=True)[int(0.10 * n)], u, rel_tol=0)

    g = out["garch"]["posterior_mean"]
    mu, omega, alpha, b = g["mu"], g["omega"], g["alpha"], g["beta"]
    variance = omega / (1 - alpha - b)
    for ret in (-y for y in losses):
        variance = omega + alpha * (ret - mu) ** 2 + b * variance
    r.close("garch-sigma-next", "one-step GARCH volatility by hand recursion from the posterior mean",
            f"{REF}:75-83", math.sqrt(variance), methods["filtered_historical"]["sigma_next"], rel_tol=1e-12)
    # The first version of this check asserted convergence and failed on this i.i.d. t(4) sample. The module
    # promises a degraded flag, not convergence (tail_models.py:125-127), so the contract is what is checked;
    # the observed convergence is recorded beside it.
    flagged = out["degraded"] and "did not converge" in (out["degraded_reason"] or "")
    r.equal("garch-nonconvergence-flagged", "degraded flag and reason track GARCH convergence "
            f"(observed converged={out['garch']['converged']}, max R-hat {max(out['garch']['rhat'].values()):.4g})",
            f"{REF}:78-79", not out["garch"]["converged"], flagged)
    return r.write()


if __name__ == "__main__":
    main()
