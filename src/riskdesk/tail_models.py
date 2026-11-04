"""VaR and Expected Shortfall of one P&L history under several models, side by side.

Formulas and sources are in plugins/risk-desk/skills/risk-tail/reference.md.
The GARCH-t model is Option Desk's (optiondesk_engine), called, not copied.
"""
import math

import numpy as np
from optiondesk_engine.simulation.garch import fit_garch_t
from optiondesk_engine.simulation.paths import simulate_paths
from scipy import stats

from riskdesk.analytics import envelope, tail_risk
from riskdesk.models import TailRequest

# McNeil and Frey (2000), sections 2.3 and 3: k = 100 exceedances in windows of n = 1000.
EVT_TAIL_FRACTION = 0.10
# McNeil and Frey (2000), section 2.3: the GPD quantile is robust "as long as k is greater than about 50".
EVT_MIN_EXCEEDANCES = 50
GARCH_METHODS = ("filtered_historical", "garch_evt", "garch_t_monte_carlo")


def _normal(losses, q):
    mean, sd = stats.norm.fit(losses)
    z = stats.norm.ppf(q)
    return dict(var=mean + sd*z, expected_shortfall=mean + sd*stats.norm.pdf(z)/(1-q),
                mean_loss=mean, std_loss=sd)


def _student_t(losses, q):
    dof, loc, scale = stats.t.fit(losses)
    x = stats.t.ppf(q, dof)
    # ES is infinite at or below one degree of freedom.
    es = loc + scale*stats.t.pdf(x, dof)/(1-q)*(dof + x*x)/(dof - 1) if dof > 1 else None
    return dict(var=loc + scale*x, expected_shortfall=es, dof=dof, loc=loc, scale=scale)


def _pot(losses, q):
    """Peaks over threshold, McNeil and Frey eq. (10) and (14). Returns (result, reason)."""
    n = len(losses)
    k = int(EVT_TAIL_FRACTION*n)
    if k < 2 or q <= 1 - k/n:
        return None, "EVT needs the target quantile beyond the threshold (q > 1 - k/n) and k >= 2; n={}, k={}".format(n, k)
    ordered = np.sort(losses)[::-1]
    u = ordered[k]  # (k+1)th largest loss
    excess = ordered[:k] - u
    if not excess.max() > 0:
        return None, "EVT excesses over the threshold are all zero"
    xi, _, beta = stats.genpareto.fit(excess, floc=0)
    log_ratio = math.log((1 - q)/(k/n))
    var = u + beta*(math.expm1(-xi*log_ratio)/xi if xi else -log_ratio)
    es = (var + beta - xi*u)/(1 - xi) if xi < 1 else None
    return dict(var=var, expected_shortfall=es, threshold=u, exceedances=k, xi=xi, beta=beta), None


def _historical(request, pnl):
    """The existing skfolio estimator, so every empirical column uses one quantile rule."""
    result = tail_risk(dict(request.model_dump(mode="json"), pnl=pnl.tolist()))
    return result, dict(var=result["var"], expected_shortfall=result["expected_shortfall"])


def _money(result, scale, offset=0.0):
    out = dict(result)
    for key in ("var", "expected_shortfall"):
        out[key] = None if result[key] is None else (offset + result[key]*scale)
    return out


def tail_models(payload):
    request = TailRequest.model_validate(payload)
    pnl = np.asarray(request.pnl, dtype=float)
    pv, q = request.portfolio_value, request.confidence
    returns = pnl/pv
    if not np.isfinite(returns).all():
        raise ValueError("normalised P&L exceeds numerical limits")
    if np.ptp(returns) == 0:
        raise ValueError("P&L series is constant; no distribution can be fitted")
    losses = -returns
    warnings, unavailable = [], {}

    historical, methods = _historical(request, pnl)
    methods = {"historical": methods}
    if historical["degraded"]:
        warnings.append(historical["degraded_reason"])
    methods["normal"] = _money(_normal(losses, q), pv)
    methods["student_t"] = _money(_student_t(losses, q), pv)
    if methods["student_t"]["expected_shortfall"] is None:
        warnings.append("Student-t fit has at most one degree of freedom; its Expected Shortfall is infinite and is not reported.")
    pot, reason = _pot(losses, q)
    if pot is None:
        unavailable["evt_pot"] = reason
    else:
        methods["evt_pot"] = _money(pot, pv)

    garch = None
    try:
        posterior = fit_garch_t(returns.tolist())
    except ValueError as exc:
        unavailable.update({m: "GARCH-t fit refused: {}".format(exc) for m in GARCH_METHODS})
    else:
        mu, omega, alpha, beta, nu = params = np.mean(posterior.draws, axis=0).tolist()
        variance, sigma = omega/(1 - alpha - beta), []
        for r in returns:  # the same filter as GarchPosterior.last_variance, keeping each step
            sigma.append(math.sqrt(variance))
            variance = omega + alpha*(r - mu)**2 + beta*variance
        sigma_next = math.sqrt(variance)
        z = (returns - mu)/np.asarray(sigma)
        _, methods["filtered_historical"] =_historical(request, (mu + sigma_next*z)*pv)
        methods["filtered_historical"]["sigma_next"] = sigma_next
        evt, reason = _pot(-z, q)
        if evt is None:
            unavailable["garch_evt"] = reason
        else:
            methods["garch_evt"] = _money(evt, sigma_next*pv, offset=-mu*pv)
        simulation = simulate_paths(posterior, 1.0, 1)
        # spot 1 and one step: log(terminal) is exactly mu + sigma*z for that path.
        _, methods["garch_t_monte_carlo"] = _historical(request, np.log(simulation["terminal"])*pv)
        methods["garch_t_monte_carlo"].update(paths=simulation["paths"],
                                              discarded_paths=simulation["discarded_paths"])
        diagnostics = posterior.diagnostics
        garch = dict(posterior_mean=dict(zip(posterior.NAMES, params)), converged=diagnostics["converged"],
                     rhat=diagnostics["rhat"], ess=diagnostics["ess"],
                     acceptance_rate=diagnostics["acceptance_rate"], chains=diagnostics["chains"],
                     draws_per_chain=diagnostics["draws_per_chain"], burn_in=diagnostics["burn_in"])
        if not diagnostics["converged"]:
            warnings.append("GARCH-t posterior did not converge (split R-hat or effective sample size gate failed); "
                            "filtered historical, GARCH-EVT and Monte Carlo columns are not reliable.")
    for name in ("evt_pot", "garch_evt"):
        if name in methods and methods[name]["exceedances"] < EVT_MIN_EXCEEDANCES:
            warnings.append("{} uses {} exceedances; McNeil and Frey found the GPD quantile robust above about {}.".format(
                name, methods[name]["exceedances"], EVT_MIN_EXCEEDANCES))
        if name in methods and methods[name]["expected_shortfall"] is None:
            warnings.append("{} tail index is at least one; Expected Shortfall is infinite and is not reported.".format(name))
    warnings += ["{} unavailable: {}".format(m, r) for m, r in unavailable.items()]

    for name, row in methods.items():
        if not all(v is None or (isinstance(v, (int, float)) and math.isfinite(v)) for v in row.values()):
            raise ValueError("{} produced a non-finite result".format(name))
    result = envelope(request, "VaR and Expected Shortfall under several tail models", [
        "Each P&L sample spans the stated horizon and the series is in time order, oldest first; no square-root-of-time scaling.",
        "Loss is positive; negative VaR or ES denotes a gain. Values are not floored at zero.",
        "Normal and Student-t parameters are maximum likelihood fits (scipy) to loss divided by portfolio value.",
        "EVT fits a generalised Pareto distribution by maximum likelihood to the k = floor(0.10 n) largest losses over the (k+1)th.",
        "GARCH(1,1)-t is Option Desk's Bayesian fit; filtered historical and GARCH-EVT use the posterior mean parameters, "
        "the Monte Carlo column draws one posterior parameter set per path.",
        "The forecast is one sample period ahead of the last observation; model accuracy is not tested here."], warnings)
    result.update(confidence=q, horizon_days=request.horizon_days, portfolio_value=pv,
                  observations=len(pnl), methods=methods, unavailable=unavailable, garch=garch)
    return result
