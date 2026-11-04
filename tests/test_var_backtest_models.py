"""Tail models checked against independent calculations, not against themselves."""
import math

import numpy as np
import pytest
from pydantic import ValidationError
from scipy import integrate, stats

from optiondesk_engine.simulation.garch import GarchPosterior
from riskdesk import tail_models as tm
from riskdesk.analytics import tail_risk

pytestmark = pytest.mark.unit

PV = 1_000_000.0


def request(pnl, confidence=0.99):
    return dict(as_of="2026-09-12", currency="USD", source="synthetic test", data_mode="synthetic",
                pnl=[float(v) for v in pnl], confidence=confidence, horizon_days=1, portfolio_value=PV)


def garch_t_series(n, seed=7, omega=2e-6, alpha=0.08, beta=0.9, nu=5.0):
    rng = np.random.default_rng(seed)
    variance, out = omega/(1 - alpha - beta), []
    for _ in range(n):
        e = math.sqrt(variance)*rng.standard_t(nu)*math.sqrt((nu - 2)/nu)
        out.append(e)
        variance = omega + alpha*e*e + beta*variance
    return np.asarray(out)


@pytest.fixture(scope="module")
def fitted():
    """One GARCH fit for the module: Option Desk's sampler takes about two seconds."""
    pnl = garch_t_series(500)*PV
    return pnl, tm.tail_models(request(pnl))


def test_normal_es_matches_numerical_integration_of_the_quantile():
    losses = stats.norm.rvs(0.001, 0.02, size=400, random_state=1)
    out = tm._normal(losses, 0.975)
    assert out["mean_loss"] == pytest.approx(np.mean(losses))
    assert out["std_loss"] == pytest.approx(np.std(losses))  # MLE, ddof 0
    ppf = lambda u: stats.norm.ppf(u, out["mean_loss"], out["std_loss"])
    assert out["var"] == pytest.approx(ppf(0.975))
    assert out["expected_shortfall"] == pytest.approx(integrate.quad(ppf, 0.975, 1)[0]/0.025, rel=1e-7)


@pytest.mark.parametrize("q", [0.95, 0.99])
def test_student_t_es_matches_numerical_integration_of_the_density(q):
    losses = stats.t.rvs(4, loc=0.001, scale=0.01, size=2000, random_state=2)
    out = tm._student_t(losses, q)
    dist = stats.t(out["dof"], out["loc"], out["scale"])
    assert out["var"] == pytest.approx(dist.ppf(q))
    tail = integrate.quad(lambda x: x*dist.pdf(x), out["var"], np.inf)[0]/(1 - q)
    assert out["expected_shortfall"] == pytest.approx(tail, rel=1e-6)
    assert out["dof"] == pytest.approx(4, rel=0.35)  # MLE recovers the simulated dof


def test_student_t_with_dof_at_most_one_reports_no_es(monkeypatch):
    monkeypatch.setattr(tm.stats.t, "fit", lambda losses: (0.9, 0.0, 1.0))
    out = tm._student_t([0.0, 1.0], 0.99)
    assert out["expected_shortfall"] is None and out["var"] == pytest.approx(stats.t.ppf(0.99, 0.9))


def test_evt_quantile_inverts_the_tail_estimator_and_es_integrates_the_gpd():
    losses = stats.t.rvs(4, size=1000, random_state=4)
    out, reason = tm._pot(losses, 0.99)
    assert reason is None and out["exceedances"] == 100
    assert out["threshold"] == np.sort(losses)[::-1][100]
    gpd = stats.genpareto(out["xi"], scale=out["beta"])
    # McNeil and Frey eq. (9): the estimated tail probability at the VaR is 1 - q.
    assert 100/1000*gpd.sf(out["var"] - out["threshold"]) == pytest.approx(0.01, rel=1e-9)
    excess = out["var"] - out["threshold"]
    mean_excess = integrate.quad(gpd.sf, excess, np.inf)[0]/gpd.sf(excess)
    assert out["expected_shortfall"] == pytest.approx(out["var"] + mean_excess, rel=1e-6)


def test_evt_estimates_a_known_t_quantile_within_simulation_error():
    """Brute force: across 40 samples of n=1000 from t(4), the mean EVT 99% quantile is near the truth."""
    estimates = [tm._pot(stats.t.rvs(4, size=1000, random_state=s), 0.99)[0]["var"] for s in range(40)]
    assert np.mean(estimates) == pytest.approx(stats.t.ppf(0.99, 4), rel=0.05)


def test_evt_refuses_a_quantile_inside_the_threshold():
    out, reason = tm._pot(np.arange(100.0), 0.85)
    assert out is None and "q > 1 - k/n" in reason


def test_historical_column_is_the_existing_skfolio_result(fitted):
    pnl, out = fitted
    reference = tail_risk(request(pnl))
    assert out["methods"]["historical"]["var"] == reference["var"]
    assert out["methods"]["historical"]["expected_shortfall"] == reference["expected_shortfall"]


def test_garch_filter_matches_option_desk_last_variance(fitted):
    pnl, out = fitted
    params = [out["garch"]["posterior_mean"][k] for k in GarchPosterior.NAMES]
    posterior = GarchPosterior([params], {}, (pnl/PV).tolist())
    assert out["methods"]["filtered_historical"]["sigma_next"] == pytest.approx(
        math.sqrt(posterior.last_variance(params)), rel=1e-12)


def test_every_method_reports_a_finite_monetary_loss_with_es_at_least_var(fitted):
    _, out = fitted
    assert set(out["methods"]) == {"historical", "normal", "student_t", "evt_pot",
                                   "filtered_historical", "garch_evt", "garch_t_monte_carlo"}
    assert out["unavailable"] == {}
    for name, row in out["methods"].items():
        assert math.isfinite(row["var"]) and row["expected_shortfall"] >= row["var"], name
    assert out["methods"]["garch_t_monte_carlo"]["paths"] == 20000
    assert out["currency"] == "USD" and out["horizon_days"] == 1 and out["observations"] == 500


def test_garch_columns_are_reproducible(fitted):
    pnl, out = fitted
    again = tm.tail_models(request(pnl))
    for name in ("filtered_historical", "garch_evt", "garch_t_monte_carlo"):
        assert again["methods"][name] == out["methods"][name]


def test_short_history_drops_garch_methods_and_is_degraded():
    out = tm.tail_models(request(garch_t_series(40)*PV))
    assert set(out["unavailable"]) == set(tm.GARCH_METHODS)
    assert "at least 60 returns" in out["unavailable"]["garch_evt"]
    assert out["degraded"] and "filtered_historical unavailable" in out["degraded_reason"]


def test_constant_series_is_refused():
    with pytest.raises(ValueError, match="constant"):
        tm.tail_models(request([5.0]*100))


@pytest.mark.parametrize("change", [{"pnl": [1, float("nan")]}, {"confidence": 1}, {"surprise": 1}])
def test_invalid_inputs_are_refused_by_the_contract(change):
    payload = request([1.0, 2.0, 3.0]); payload.update(change)
    with pytest.raises(ValidationError):
        tm.tail_models(payload)


def test_the_tail_checker_passes_a_real_result_and_fails_a_tampered_one(fitted, tmp_path, capsys):
    import importlib.util
    import json
    from pathlib import Path
    path = Path(__file__).resolve().parent.parent / "plugins/risk-desk/skills/risk-tail/scripts/check_artifact.py"
    spec = importlib.util.spec_from_file_location("check_risk_tail", path)
    checker = importlib.util.module_from_spec(spec); spec.loader.exec_module(checker)
    _, out = fitted
    artifact = tmp_path / "r.json"
    artifact.write_text(json.dumps(out))
    assert checker.main(str(artifact)) == 0
    assert capsys.readouterr().out.split()[0] == ("DEGRADED" if out["degraded"] else "OK")
    tampered = json.loads(json.dumps(out)); tampered["methods"]["normal"]["expected_shortfall"] = -1.0
    artifact.write_text(json.dumps(tampered))
    assert checker.main(str(artifact)) == 1 and "normal: ES below VaR" in capsys.readouterr().out
    artifact.write_text(json.dumps(tail_risk(request(np.arange(-50.0, 50.0)))))
    assert checker.main(str(artifact)) == 0
