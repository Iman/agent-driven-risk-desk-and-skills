"""Credit VaR tests against published figures, exact distributions and brute force."""
import json
import math
from pathlib import Path

import numpy as np
import pytest
from scipy.stats import binom, norm

from riskdesk.credit import asrf_credit_var, copula_credit_var

pytestmark = pytest.mark.unit


def meta(**extra):
    return dict(as_of="2026-11-04", currency="EUR", source="synthetic test",
                data_mode="synthetic", horizon_days=365, **extra)


def pool(n, pd, lgd, **obligor):
    return [dict(id=str(i), exposure=1.0, pd=pd, lgd=lgd, **obligor) for i in range(n)]


# CRE99 Table 1 (version effective 1 January 2023), corporate exposures, LGD 40%,
# turnover EUR 50 million (no firm-size adjustment), M = 2.5 years: PD -> risk weight %.
CRE99_TABLE_1 = {0.0005: 17.47, 0.001: 26.36, 0.0025: 43.97, 0.004: 55.75, 0.005: 61.88,
                 0.0075: 73.58, 0.01: 82.06, 0.013: 89.73, 0.015: 93.86, 0.02: 102.09,
                 0.025: 108.58, 0.03: 114.17, 0.04: 124.07, 0.05: 133.20, 0.06: 141.88,
                 0.10: 171.63, 0.15: 196.92, 0.20: 211.76}


@pytest.mark.parametrize("pd,published", sorted(CRE99_TABLE_1.items()))
def test_asrf_reproduces_the_cre99_illustrative_irb_risk_weights(pd, published):
    # CRE31.5: corporate correlation and maturity adjustment; RW = 12.5 * K, K = UL/EAD * MA.
    weight = (1 - math.exp(-50 * pd)) / (1 - math.exp(-50))
    correlation = 0.12 * weight + 0.24 * (1 - weight)
    b = (0.11852 - 0.05478 * math.log(pd)) ** 2
    result = asrf_credit_var(meta(confidence=0.999, obligors=[
        dict(id="x", exposure=1.0, pd=pd, lgd=0.40, correlation=correlation)]))
    risk_weight = 12.5 * result["unexpected_loss"] / (1 - 1.5 * b) * 100
    assert risk_weight == pytest.approx(published, abs=0.005)  # table is rounded to 0.01


def test_asrf_quantile_matches_brute_force_over_the_factor():
    obligors = [dict(id="a", exposure=100, pd=0.002, lgd=0.6, correlation=0.10),
                dict(id="b", exposure=40, pd=0.03, lgd=0.4, correlation=0.20),
                dict(id="c", exposure=70, pd=0.08, lgd=0.25, correlation=0.05)]
    result = asrf_credit_var(meta(confidence=0.99, obligors=obligors))
    z = np.random.default_rng(1).standard_normal(1_000_000)
    loss = sum(o["exposure"] * o["lgd"] * norm.cdf(
        (norm.ppf(o["pd"]) - math.sqrt(o["correlation"]) * z) / math.sqrt(1 - o["correlation"]))
        for o in obligors)
    assert result["credit_var"] == pytest.approx(np.quantile(loss, 0.99), rel=0.01)
    assert result["expected_loss"] == pytest.approx(100 * .6 * .002 + 40 * .4 * .03 + 70 * .25 * .08)
    assert sum(result["contributions"].values()) == pytest.approx(result["credit_var"])


def finite_pool(n, pd, rho, lgd, q):
    """Exact VaR and ES of a homogeneous pool: binomial mixed over the factor by quadrature."""
    nodes, weights = np.polynomial.legendre.leggauss(400)
    z = 10 * nodes
    density = 10 * weights * norm.pdf(z)
    p = norm.cdf((norm.ppf(pd) - math.sqrt(rho) * z) / math.sqrt(1 - rho))
    k = np.arange(n + 1)
    pmf = binom.pmf(k[:, None], n, p[None, :]) @ density
    cdf = np.cumsum(pmf)
    var_k = int(np.searchsorted(cdf, q))
    tail = math.fsum(pmf[var_k + 1:] * k[var_k + 1:]) + (cdf[var_k] - q) * var_k
    return var_k * lgd, tail / (1 - q) * lgd


def test_monte_carlo_matches_the_exact_finite_pool_distribution():
    n, pd, rho, lgd, q = 1_000, 0.01, 0.12, 0.45, 0.99
    var, es = finite_pool(n, pd, rho, lgd, q)
    result = copula_credit_var(meta(confidence=q, scenarios=200_000, seed=7,
                                    obligors=pool(n, pd, lgd, factor_loading=math.sqrt(rho))))
    # 2,000 tail scenarios: the quantile lands within two defaults of the exact one.
    assert abs(result["credit_var"] - var) <= 2 * lgd
    assert result["expected_shortfall"] == pytest.approx(es, rel=0.02)
    standard_error = result["loss_standard_deviation"] / math.sqrt(200_000)
    assert abs(result["expected_loss"] - n * pd * lgd) < 4 * standard_error
    assert result["unexpected_loss"] == pytest.approx(result["credit_var"] - result["expected_loss"])
    assert result["degraded"] is False


def test_monte_carlo_converges_to_vasicek_for_a_large_homogeneous_pool():
    n, pd, rho, lgd, q = 5_000, 0.01, 0.12, 0.45, 0.99
    vasicek = asrf_credit_var(meta(confidence=q, obligors=pool(n, pd, lgd, correlation=rho)))
    simulated = copula_credit_var(meta(confidence=q, scenarios=40_000, seed=11,
                                       obligors=pool(n, pd, lgd, factor_loading=math.sqrt(rho))))
    exact = {size: finite_pool(size, pd, rho, lgd, q)[0] / size for size in (100, 1_000, n)}
    gaps = [exact[size] / (vasicek["credit_var"] / n) - 1 for size in (100, 1_000, n)]
    assert gaps[0] > gaps[1] > gaps[2] > 0     # granularity gap shrinks towards zero
    # Measured on 2026-11-04: exact gap 0.5% at 5,000 names; 400 tail scenarios add noise.
    assert simulated["credit_var"] == pytest.approx(vasicek["credit_var"], rel=0.02)


def test_monte_carlo_is_reproducible_by_seed():
    payload = meta(confidence=0.99, scenarios=5_000, seed=3,
                   obligors=pool(50, 0.02, 0.5, factor_loading=0.4))
    assert copula_credit_var(payload)["credit_var"] == copula_credit_var(payload)["credit_var"]
    first = copula_credit_var(payload)
    payload["seed"] = 4
    assert copula_credit_var(payload)["expected_loss"] != first["expected_loss"]


def test_thin_tail_is_reported_as_degraded():
    result = copula_credit_var(meta(confidence=0.995, scenarios=1_000, seed=1,
                                    obligors=pool(10, 0.05, 1.0, factor_loading=0.3)))
    assert result["degraded"] is True
    assert "Fewer than 20" in result["degraded_reason"]


@pytest.mark.parametrize("handler,obligor,change", [
    (asrf_credit_var, dict(correlation=0.1), {"confidence": 1}),
    (asrf_credit_var, dict(correlation=1.0), {}),
    (asrf_credit_var, dict(correlation=0.1, pd=0), {}),
    (asrf_credit_var, dict(correlation=0.1, lgd=1.2), {}),
    (asrf_credit_var, dict(correlation=0.1, exposure=float("inf")), {}),
    (asrf_credit_var, dict(correlation=0.1), {"duplicate": True}),
    (copula_credit_var, dict(factor_loading=1.0), {"scenarios": 1000, "seed": 1}),
    (copula_credit_var, dict(factor_loading=0.3), {"scenarios": 999, "seed": 1}),
    (copula_credit_var, dict(factor_loading=0.3), {"scenarios": 1000, "seed": -1}),
    (copula_credit_var, dict(factor_loading=0.3), {"scenarios": 1_000_001, "seed": 1}),
    (copula_credit_var, dict(factor_loading=0.3), {"scenarios": 1_000_000, "seed": 1, "n": 201}),
])
def test_invalid_credit_inputs_are_refused(handler, obligor, change):
    change = dict(change)
    duplicate, count = change.pop("duplicate", False), change.pop("n", 1)
    base = {**dict(exposure=1.0, pd=0.01, lgd=0.5), **obligor}
    obligors = [dict(base, id="x" if duplicate else str(i)) for i in range(2 if duplicate else count)]
    payload = meta(confidence=0.99, obligors=obligors)
    payload.update(change)
    with pytest.raises(ValueError):
        handler(payload)


def test_shipped_examples_run_and_are_not_degraded():
    examples = Path(__file__).resolve().parent.parent / "examples"
    for name, handler in (("credit_asrf.json", asrf_credit_var), ("credit_copula.json", copula_credit_var)):
        result = handler(json.loads((examples / name).read_text()))
        assert result["degraded"] is False and result["data_mode"] == "synthetic", name
        assert result["credit_var"] > result["expected_loss"] > 0, name


def load_checker(skill):
    import importlib.util
    path = (Path(__file__).resolve().parent.parent / "plugins" / "risk-desk" / "skills" / skill
            / "scripts" / "check_artifact.py")
    spec = importlib.util.spec_from_file_location("check_" + skill.replace("-", "_"), path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_check_artifact_accepts_results_and_rejects_tampering(tmp_path, capsys):
    checker = load_checker("risk-credit")
    asrf = asrf_credit_var(meta(confidence=0.99, obligors=pool(20, 0.02, 0.5, correlation=0.2)))
    copula = copula_credit_var(meta(confidence=0.99, scenarios=5_000, seed=2,
                                    obligors=pool(20, 0.02, 0.5, factor_loading=0.4)))
    for result in (asrf, copula):
        path = tmp_path / "ok.json"
        path.write_text(json.dumps(result))
        assert checker.main(str(path)) == 0, capsys.readouterr().out
    asrf["contributions"]["0"] += 1.0
    copula["expected_shortfall"] = copula["credit_var"] / 2
    for result in (asrf, copula):
        path = tmp_path / "bad.json"
        path.write_text(json.dumps(result))
        assert checker.main(str(path)) == 1
    assert "FAIL" in capsys.readouterr().out
