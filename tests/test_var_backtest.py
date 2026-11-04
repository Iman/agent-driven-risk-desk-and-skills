"""Backtests checked against independent calculations and a published table."""
import numpy as np
import pytest
from pydantic import ValidationError
from scipy import stats

from riskdesk import backtest as bt

pytestmark = pytest.mark.unit


def request(pnl, var, confidence=0.99, **extra):
    return dict(as_of="2026-09-12", currency="USD", source="synthetic test", data_mode="synthetic",
                pnl=[float(v) for v in pnl], var=[float(v) for v in var], confidence=confidence,
                horizon_days=1, **extra)


def from_hits(hits):
    """P&L that breaches a VaR of 10 exactly where hits is true."""
    hits = np.asarray(hits, dtype=bool)
    return np.where(hits, -11.0, 5.0), np.full(len(hits), 10.0)


@pytest.mark.parametrize("x,n,p", [(0, 250, 0.01), (3, 250, 0.01), (11, 250, 0.01), (60, 1000, 0.05), (250, 250, 0.01)])
def test_kupiec_equals_the_binomial_likelihood_ratio(x, n, p):
    expected = 2*(stats.binom.logpmf(x, n, x/n) - stats.binom.logpmf(x, n, p))
    assert bt._kupiec(x, n, p)["lr"] == pytest.approx(max(expected, 0), abs=1e-9)


def test_kupiec_size_under_the_null_is_near_five_percent():
    rng = np.random.default_rng(5)
    rejected = [bt._kupiec(int(rng.binomial(1000, 0.05)), 1000, 0.05)["p_value"] < 0.05 for _ in range(4000)]
    assert 0.035 < np.mean(rejected) < 0.07


def brute_markov_loglik(hits, pi0, pi1):
    total = 0.0
    for a, b in zip(hits[:-1], hits[1:]):
        prob = pi1 if a else pi0
        total += np.log(prob if b else 1 - prob)
    return total


def test_christoffersen_matches_a_brute_force_markov_likelihood():
    hits = np.random.default_rng(6).random(500) < 0.04
    hits[[100, 101, 300, 301, 302]] = True
    ind, cc = bt._christoffersen(hits, 0.01)
    markov = brute_markov_loglik(hits, ind["pi0"], ind["pi1"])
    pi = hits[1:].mean()
    iid = brute_markov_loglik(hits, pi, pi)
    null = brute_markov_loglik(hits, 0.01, 0.01)
    assert ind["lr"] == pytest.approx(-2*(iid - markov), rel=1e-10)
    assert cc["lr"] == pytest.approx(-2*(null - markov), rel=1e-10)
    # Christoffersen's decomposition on the n-1 transitions: LR_cc = LR_uc + LR_ind.
    assert cc["lr"] == pytest.approx(bt._kupiec(int(hits[1:].sum()), 499, 0.01)["lr"] + ind["lr"], rel=1e-10)


def test_clustered_exceptions_fail_independence_and_scattered_ones_pass():
    clustered = np.zeros(500, bool); clustered[200:205] = True
    scattered = np.zeros(500, bool); scattered[::100] = True
    assert bt.var_backtest(request(*from_hits(clustered), confidence=0.99))["christoffersen_independence"]["p_value"] < 0.01
    assert bt.var_backtest(request(*from_hits(scattered), confidence=0.99))["christoffersen_independence"]["p_value"] > 0.5


def test_basel_zones_reproduce_mar99_table_2():
    """Basel Framework MAR99.17, Table 2: 250 observations at 99% coverage."""
    table = {0: ("green", 8.11), 1: ("green", 28.58), 2: ("green", 54.32), 3: ("green", 75.81),
             4: ("green", 89.22), 5: ("amber", 95.88), 6: ("amber", 98.63), 7: ("amber", 99.60),
             8: ("amber", 99.89), 9: ("amber", 99.97), 10: ("red", 99.99)}
    for x, (zone, cumulative) in table.items():
        hits = np.zeros(250, bool); hits[:x] = True
        out = bt.var_backtest(request(*from_hits(hits)))["basel_traffic_light"]
        assert out["zone"] == zone, x
        assert round(100*out["cumulative_probability"], 2) == cumulative, x
        assert (out["amber_from"], out["red_from"]) == (5, 10)
    hits = np.zeros(250, bool); hits[:14] = True
    assert bt.var_backtest(request(*from_hits(hits)))["basel_traffic_light"]["zone"] == "red"


@pytest.mark.parametrize("confidence,horizon", [(0.975, 1), (0.99, 10)])
def test_basel_zone_is_withheld_outside_one_day_99_percent(confidence, horizon):
    payload = request(*from_hits(np.zeros(250, bool)), confidence=confidence); payload["horizon_days"] = horizon
    out = bt.var_backtest(payload)
    assert out["basel_traffic_light"] is None and "MAR99" in out["basel_traffic_light_unavailable"]


def normal_forecasts(n, sd, c=0.975):
    z = stats.norm.ppf(c)
    return z*sd, stats.norm.pdf(z)/(1 - c)*sd


def test_z2_has_mean_zero_under_the_model_it_tests():
    """Acerbi and Szekely: E[Z2] = 0 when P&L follows the forecast distribution. Brute force, 4000 samples."""
    rng = np.random.default_rng(8)
    sd = rng.uniform(5, 20, 250)
    var, es = normal_forecasts(250, sd)
    pnl = rng.standard_normal((4000, 250))*sd
    assert np.mean(bt._z2(pnl, var, es, 0.025)) == pytest.approx(0, abs=0.03)


def test_null_distribution_reproduces_the_forecast_var_and_es():
    """The location-scale null implied by (VaR, ES) has exactly those VaR and ES."""
    var, es, dof, c = 12.0, 17.0, 5.0, 0.975
    q = stats.t.ppf(c, dof); e = stats.t.pdf(q, dof)/(1 - c)*(dof + q*q)/(dof - 1)
    scale = (es - var)/(e - q); loc = var - scale*q
    dist = stats.t(dof, loc, scale)
    assert dist.ppf(c) == pytest.approx(var)
    assert dist.expect(lambda x: x, lb=dist.ppf(c))/(1 - c) == pytest.approx(es, rel=1e-6)


@pytest.mark.parametrize("es_null,dof", [("normal", None), ("student-t", 5.0)])
def test_es_backtest_rejects_understated_risk_and_accepts_the_true_model(es_null, dof):
    rng = np.random.default_rng(9)
    sd = np.full(500, 10.0)
    var, es = normal_forecasts(500, sd)
    if es_null == "student-t":
        q = stats.t.ppf(0.975, dof); scale = sd*np.sqrt((dof - 2)/dof)
        var, es = q*scale, stats.t.pdf(q, dof)/0.025*(dof + q*q)/(dof - 1)*scale
        true = rng.standard_t(dof, 500)*sd*np.sqrt((dof - 2)/dof)
    else:
        true = rng.standard_normal(500)*sd
    extra = dict(expected_shortfall=es.tolist(), es_null=es_null, es_null_dof=dof, seed=3)
    good = bt.var_backtest(request(-true, var, 0.975, **extra))["es_backtest"]
    bad = bt.var_backtest(request(-true*1.6, var, 0.975, **extra))["es_backtest"]
    # One true-model sample can fall below 5% by chance; the null p-values were measured uniform separately.
    assert bad["p_value"] < 0.01 < good["p_value"] and bad["z2"] < good["z2"]
    assert bt.var_backtest(request(-true, var, 0.975, **extra))["es_backtest"] == good  # seeded


def test_no_exceptions_gives_z2_of_one_and_p_value_of_one():
    pnl, var = from_hits(np.zeros(100, bool))
    out = bt.var_backtest(request(pnl, var, 0.975, expected_shortfall=[12.0]*100, es_null="normal"))
    assert out["es_backtest"]["z2"] == 1 and out["es_backtest"]["p_value"] == 1
    assert out["exceptions"] == 0 and out["kupiec_pof"]["lr"] > 0


@pytest.mark.parametrize("change", [
    {"var": [10.0]}, {"expected_shortfall": [12.0, 12.0]}, {"es_null": "normal"},
    {"expected_shortfall": [9.0, 12.0], "es_null": "normal"},
    {"expected_shortfall": [12.0, 12.0], "es_null": "student-t"},
    {"expected_shortfall": [12.0, 12.0], "es_null": "normal", "es_null_dof": 4.0},
    {"pnl": [1.0, float("inf")]}, {"surprise": 1}])
def test_invalid_backtest_inputs_are_refused(change):
    payload = request([1.0, -20.0], [10.0, 10.0]); payload.update(change)
    with pytest.raises(ValidationError):
        bt.var_backtest(payload)


def test_the_energy_example_reproduces_from_its_stated_recipe_and_runs():
    import json
    from pathlib import Path
    examples = Path(__file__).resolve().parent.parent / "examples"
    example = json.loads((examples / "var_backtest_energy.json").read_text(encoding="utf-8"))
    pnl = np.asarray(json.loads((examples / "energy_tail.json").read_text(encoding="utf-8"))["pnl"], float)
    mean, sd, z = pnl[:750].mean(), pnl[:750].std(), stats.norm.ppf(0.99)
    assert example["pnl"] == pnl[750:].tolist()
    assert example["var"] == [round(-mean + sd*z, 2)]*250
    assert example["expected_shortfall"] == [round(-mean + sd*stats.norm.pdf(z)/0.01, 2)]*250
    out = bt.var_backtest(example)
    assert out["data_mode"] == "synthetic" and out["degraded"] is False
    assert out["basel_traffic_light"]["zone"] in ("green", "amber", "red")


def load_checker(skill):
    import importlib.util
    from pathlib import Path
    path = Path(__file__).resolve().parent.parent / "plugins/risk-desk/skills" / skill / "scripts/check_artifact.py"
    spec = importlib.util.spec_from_file_location("check_" + skill.replace("-", "_"), path)
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    return module


def test_the_backtest_checker_passes_a_real_result_and_fails_a_tampered_one(tmp_path, capsys):
    import json
    checker = load_checker("risk-backtest")
    pnl, var = from_hits(np.zeros(250, bool))
    result = bt.var_backtest(request(pnl, var))
    path = tmp_path / "r.json"
    path.write_text(json.dumps(result))
    assert checker.main(str(path)) == 0 and capsys.readouterr().out.startswith("OK")
    result["basel_traffic_light"]["zone"] = "red"
    path.write_text(json.dumps(result))
    assert checker.main(str(path)) == 1 and "does not match" in capsys.readouterr().out


def test_a_loss_equal_to_var_is_not_an_exception():
    out = bt.var_backtest(request([-10.0, -10.5, 0.0], [10.0, 10.0, 10.0]))
    assert out["exceptions"] == 1
