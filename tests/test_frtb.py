"""FRTB capital (MAR21, MAR32, MAR33). Each calculation is checked against an
independent route: arithmetic written out by hand, a closed form, a brute-force
loop, or a separate library calculation. Constants are re-quoted here from the
BIS text rather than imported, so a changed constant fails a test."""
import json
import math
import runpy
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest

from riskdesk import frtb

pytestmark = pytest.mark.unit
ROOT = Path(__file__).resolve().parent.parent


def meta():
    return dict(as_of="2026-11-04", currency="USD", source="synthetic test", data_mode="synthetic")


def flat(value):
    """A cascade where only ES_T(P) is non-zero: every risk factor has a 10-day horizon."""
    return [value, 0, 0, 0, 0]


# ------------------------------------------------------------ MAR33.4, .6, .15

def test_liquidity_adjusted_es_matches_the_hand_calculation():
    # sqrt(100^2 + (80*sqrt(10/10))^2 + (60*sqrt(20/10))^2 + (40*sqrt(20/10))^2 + (20*sqrt(60/10))^2)
    # = sqrt(10000 + 6400 + 7200 + 3200 + 2400) = sqrt(29200)
    assert frtb.liquidity_adjusted_es([100, 80, 60, 40, 20]) == pytest.approx(math.sqrt(29200), rel=1e-15)


@pytest.mark.parametrize("horizon,cascade", [
    (10, [7, 0, 0, 0, 0]), (20, [7, 7, 0, 0, 0]), (40, [7, 7, 7, 0, 0]),
    (60, [7, 7, 7, 7, 0]), (120, [7, 7, 7, 7, 7])])
def test_a_book_on_one_horizon_scales_by_square_root_of_time(horizon, cascade):
    """Closed form: if every risk factor has liquidity horizon LH, every subset up to
    LH equals ES_T(P) and the cascade telescopes to ES_T * sqrt(LH / 10)."""
    assert frtb.liquidity_adjusted_es(cascade) == pytest.approx(7 * math.sqrt(horizon / 10), rel=1e-14)


def test_large_cascades_do_not_overflow_in_the_squares():
    # 1e200 squared overflows a float; the result itself, 1e200 * sqrt(12), does not.
    assert frtb.liquidity_adjusted_es([1e200] * 5) == pytest.approx(1e200 * math.sqrt(12), rel=1e-14)


def imcc_request():
    return dict(**meta(), base_horizon_days=10,
                portfolio=dict(reduced_stressed=flat(300), full_current=flat(120), reduced_current=flat(100)),
                risk_classes=dict(
                    equity=dict(reduced_stressed=flat(200), full_current=flat(80), reduced_current=flat(100)),
                    fx=dict(reduced_stressed=flat(100), full_current=flat(110), reduced_current=flat(100))))


def test_imcc_matches_the_hand_calculation():
    result = frtb.frtb_imcc(imcc_request())
    # Portfolio: 300 * 120/100 = 360. Equity: ratio 0.8 floored to 1 -> 200. FX: 100 * 1.1 = 110.
    # IMCC = 0.5 * 360 + 0.5 * (200 + 110) = 335.
    assert result["imcc_unconstrained"] == pytest.approx(360)
    assert result["risk_classes"]["equity"]["ratio"] == pytest.approx(0.8)
    assert result["risk_classes"]["equity"]["imcc"] == pytest.approx(200)
    assert result["risk_classes"]["fx"]["imcc"] == pytest.approx(110)
    assert result["imcc_constrained_sum"] == pytest.approx(310)
    assert result["imcc"] == pytest.approx(335)
    assert result["rho"] == 0.5
    assert result["base_horizon_days"] == 10
    assert result["degraded"] is False


def test_the_stress_ratio_is_floored_at_one_for_the_portfolio():
    request = imcc_request()
    request["portfolio"]["full_current"] = flat(50)
    result = frtb.frtb_imcc(request)
    assert result["portfolio"]["ratio"] == pytest.approx(0.5)
    assert result["portfolio"]["ratio_floored"] == 1.0
    assert result["imcc_unconstrained"] == pytest.approx(300)


@pytest.mark.parametrize("change,message", [
    (lambda r: r["portfolio"].update(reduced_current=flat(0)), "ratio is undefined"),
    (lambda r: r["portfolio"].update(full_current=[1e308] * 5, reduced_current=[1e308] * 5), "numerical limits"),
    (lambda r: r["portfolio"].update(full_current=[1, 2, 3]), "at least 5"),
    (lambda r: r["portfolio"].update(full_current=[-1, 0, 0, 0, 0]), "greater than or equal to 0"),
    (lambda r: r.update(base_horizon_days=1), "10"),
    (lambda r: r.update(risk_classes={}), "at least 1"),
    (lambda r: r["risk_classes"].update(vol={"reduced_stressed": flat(1), "full_current": flat(1), "reduced_current": flat(1)}), "vol"),
])
def test_imcc_refuses_invalid_input(change, message):
    request = imcc_request()
    change(request)
    with pytest.raises(ValueError, match=message):
        frtb.frtb_imcc(request)


# ------------------------------------------------------------ MAR33.41-.46, MAR32.9

def capital_request(**overrides):
    request = dict(**meta(), imcc_latest=100, ses_latest=20, imcc_average_60d=90, ses_average_60d=15,
                   bankwide_backtesting_exceptions=6, qualitative_addon=0.1, drc_latest=30, drc_average_12w=25,
                   desks=[dict(desk="A", pla_zone="green", sa=150), dict(desk="B", pla_zone="amber", sa=50)],
                   sa_green_amber=260, sa_out_of_scope=40, sa_all_desks=320)
    request.update(overrides)
    return request


def test_ima_capital_matches_the_hand_calculation():
    result = frtb.frtb_ima_capital(capital_request())
    # m_c = 1.76 + 0.1 = 1.86; C_A = max(100 + 20, 1.86*90 + 15) = 182.4; DRC = max(25, 30) = 30
    # IMA_G,A = 212.4; k = 0.5 * 50/200 = 0.125; surcharge = 0.125 * (260 - 212.4) = 5.95
    # ACR = min(212.4 + 5.95 + 40, 320) + max(0, 212.4 - 260) = 258.35; RWA = 12.5 * 258.35
    assert result["multiplier"] == pytest.approx(1.86)
    assert result["c_a"] == pytest.approx(182.4)
    assert result["drc"] == 30
    assert result["ima_green_amber"] == pytest.approx(212.4)
    assert result["k"] == pytest.approx(0.125)
    assert result["capital_surcharge"] == pytest.approx(5.95)
    assert result["aggregate_capital"] == pytest.approx(258.35)
    assert result["rwa"] == pytest.approx(3229.375)
    assert result["backtesting_zone"] == "amber"


def test_ima_capital_cap_and_excess_branches():
    # IMA_G,A 212.4 exceeds SA_G,A 200: surcharge 0, excess 12.4; min(212.4 + 0 + 40, 230) = 230; ACR = 242.4
    result = frtb.frtb_ima_capital(capital_request(sa_green_amber=200, sa_all_desks=230))
    assert result["capital_surcharge"] == 0
    assert result["aggregate_capital"] == pytest.approx(242.4)


def test_latest_observation_binds_when_it_exceeds_the_scaled_average():
    result = frtb.frtb_ima_capital(capital_request(imcc_latest=500))
    assert result["c_a"] == pytest.approx(520)


def test_drc_is_the_greater_of_the_12_week_average_and_the_latest():
    assert frtb.frtb_ima_capital(capital_request(drc_latest=20, drc_average_12w=25))["drc"] == 25


def test_no_amber_desk_means_no_surcharge():
    result = frtb.frtb_ima_capital(capital_request(desks=[dict(desk="A", pla_zone="green", sa=150)]))
    assert result["k"] == 0
    assert result["capital_surcharge"] == 0


@pytest.mark.parametrize("exceptions,zone,multiplier", [
    (0, "green", 1.50), (4, "green", 1.50), (5, "amber", 1.70), (6, "amber", 1.76), (7, "amber", 1.83),
    (8, "amber", 1.88), (9, "amber", 1.92), (10, "red", 2.00), (250, "red", 2.00)])
def test_backtesting_multiplier_is_mar32_table_1(exceptions, zone, multiplier):
    assert frtb.backtesting_multiplier(exceptions) == (zone, multiplier)


@pytest.mark.parametrize("overrides,message", [
    (dict(bankwide_backtesting_exceptions=251), "less than or equal to 250"),
    (dict(bankwide_backtesting_exceptions=2.0), "integer"),
    (dict(sa_all_desks=-1), "greater than or equal to 0"),
    (dict(desks=[dict(desk="A", pla_zone="green", sa=1), dict(desk="A", pla_zone="amber", sa=1)]), "unique"),
    (dict(desks=[dict(desk="A", pla_zone="red", sa=1)]), "green"),
    (dict(desks=[dict(desk="A", pla_zone="amber", sa=1e308), dict(desk="B", pla_zone="amber", sa=1e308)]), "numerical limits"),
    (dict(imcc_average_60d=1e308), "numerical limits"),
])
def test_ima_capital_refuses_invalid_input(overrides, message):
    with pytest.raises(ValueError, match=message):
        frtb.frtb_ima_capital(capital_request(**overrides))


def test_an_amber_desk_with_zero_standardised_charge_adds_no_surcharge():
    result = frtb.frtb_ima_capital(capital_request(desks=[dict(desk="A", pla_zone="amber", sa=0)]))
    assert result["k"] == 0


# ------------------------------------------------------------ MAR32 PLA

def pla_request(rtpl, hpl):
    return dict(**meta(), desk="d", rtpl=list(map(float, rtpl)), hpl=list(map(float, hpl)))


def test_spearman_and_ks_match_independent_calculations():
    rng = np.random.default_rng(7)
    hpl = rng.normal(0, 1e5, 250)
    rtpl = hpl + rng.normal(0, 6e4, 250)
    result = frtb.frtb_pla(pla_request(rtpl, hpl))
    # Spearman by hand: ranks from argsort (continuous draws, no ties), then Pearson on ranks.
    ranks = lambda x: np.argsort(np.argsort(x)) + 1
    assert result["spearman"] == pytest.approx(np.corrcoef(ranks(rtpl), ranks(hpl))[0, 1], rel=1e-12)
    # KS by brute force, MAR32.39-41: 0.004 times the count at or below each P&L value.
    points = np.concatenate([rtpl, hpl])
    brute = max(abs(0.004 * np.sum(rtpl <= x) - 0.004 * np.sum(hpl <= x)) for x in points)
    assert result["ks"] == pytest.approx(brute, abs=1e-12)


@pytest.mark.parametrize("shift,zone", [(0, "green"), (22, "green"), (23, "amber"), (30, "amber"), (31, "red")])
def test_ks_boundaries_are_exact(shift, zone):
    """rtpl = 0..249 and hpl = rtpl + shift give rank correlation 1 and KS exactly shift/250,
    so 22 (0.088) is green, 23 (0.092) is not, 30 (0.12) is not red, 31 (0.124) is."""
    result = frtb.frtb_pla(pla_request(range(250), np.arange(250) + shift))
    assert result["spearman"] == pytest.approx(1)
    assert result["ks_count"] == shift
    assert result["zone"] == zone


@pytest.mark.parametrize("rho,ks_count,zone", [
    (0.81, 22, "green"), (0.80, 22, "amber"), (0.81, 23, "amber"), (0.70, 30, "amber"),
    (0.6999, 0, "red"), (0.95, 31, "red"), (0.75, 10, "amber")])
def test_pla_zone_follows_mar32_42(rho, ks_count, zone):
    assert frtb.pla_zone(rho, ks_count) == zone


def test_pla_refuses_wrong_length_and_constant_series():
    with pytest.raises(ValueError, match="250"):
        frtb.frtb_pla(pla_request(range(249), range(249)))
    with pytest.raises(ValueError, match="undefined"):
        frtb.frtb_pla(pla_request([1.0] * 250, range(250)))


# ------------------------------------------------------------ MAR32 backtesting

def backtest_request(level="desk", apl_losses=0, hpl_losses=0, var=10.0, **extra):
    apl = [-11.0] * apl_losses + [1.0] * (250 - apl_losses)
    hpl = [-11.0] * hpl_losses + [1.0] * (250 - hpl_losses)
    request = dict(**meta(), level=level, apl=apl, hpl=hpl, var_99=[var] * 250)
    if level == "desk":
        request["var_975"] = [var] * 250
    request.update(extra)
    return request


def test_exceptions_are_counted_separately_and_the_greater_is_used():
    result = frtb.frtb_backtest(backtest_request(apl_losses=3, hpl_losses=5))
    assert result["exceptions_99"] == dict(apl=3, hpl=5, overall=5)
    assert result["passes"] is True


def test_a_loss_equal_to_var_is_not_an_exception_and_a_gap_is():
    request = backtest_request()
    request["apl"][0] = -10.0
    request["hpl"][1] = None
    request["var_99"][2] = None
    result = frtb.frtb_backtest(request)
    # Day 1 HPL missing (hpl only); day 2 VaR missing (both). apl 1, hpl 2.
    assert result["exceptions_99"] == dict(apl=1, hpl=2, overall=2)


@pytest.mark.parametrize("n99,n975,passes", [(12, 30, True), (13, 13, False), (0, 31, False)])
def test_desk_limits_are_mar32_19(n99, n975, passes):
    apl = [-20.0] * n99 + [-11.0] * (n975 - min(n99, n975)) + [1.0] * (250 - max(n99, n975))
    request = dict(**meta(), level="desk", apl=apl, hpl=[1.0] * 250, var_99=[15.0] * 250, var_975=[10.0] * 250)
    result = frtb.frtb_backtest(request)
    assert result["exceptions_99"]["overall"] == n99
    assert result["exceptions_975"]["overall"] == max(n99, n975)
    assert result["passes"] is passes


def test_bank_level_reports_the_zone_and_multiplier():
    result = frtb.frtb_backtest(backtest_request(level="bank", hpl_losses=7))
    assert (result["zone"], result["backtesting_multiplier"]) == ("amber", 1.83)
    assert "passes" not in result


@pytest.mark.parametrize("request_,message", [
    (backtest_request(level="bank", var_975=[1.0] * 250), "99% only"),
    (dict(backtest_request(), var_975=None), "var_975"),
    (backtest_request(var=-1.0), "negative VaR"),
    (dict(backtest_request(), apl=[1.0] * 249), "250"),
])
def test_backtest_refuses_invalid_input(request_, message):
    with pytest.raises(ValueError, match=message):
        frtb.frtb_backtest(request_)


# ------------------------------------------------------------ MAR21 SBM FX

def fx_request(delta=(), vega=(), reduce=False, currency="USD"):
    request = dict(**meta(), apply_specified_pair_reduction=reduce,
                   delta=[dict(currency=c, sensitivity=s) for c, s in delta],
                   vega=[dict(currency=c, option_maturity_years=t, sensitivity=s) for c, t, s in vega])
    request["currency"] = currency
    return request


def test_one_fx_delta_bucket_is_fifteen_percent_of_the_net_sensitivity():
    result = frtb.frtb_sbm_fx(fx_request(delta=[("EUR", 600), ("EUR", 400)]))
    assert result["delta_weighted_sensitivities"] == {"EUR": pytest.approx(150)}
    assert result["capital"] == pytest.approx(150)
    assert result["degraded"] is False


@pytest.mark.parametrize("ccy,reporting,reduced", [
    ("EUR", "USD", True), ("USD", "BRL", True), ("AUD", "EUR", True), ("ARS", "USD", False), ("EUR", "ARS", False)])
def test_specified_pair_reduction_follows_mar21_88(ccy, reporting, reduced):
    result = frtb.frtb_sbm_fx(fx_request(delta=[(ccy, 1000)], reduce=True, currency=reporting))
    assert result["capital"] == pytest.approx(150 / math.sqrt(2) if reduced else 150)


def test_two_fx_buckets_across_the_three_correlation_scenarios():
    result = frtb.frtb_sbm_fx(fx_request(delta=[("EUR", 1000), ("JPY", -500)]))
    # WS = 150 and -75. gamma medium 0.60, high 0.75, low max(2*0.6 - 1, 0.75*0.6) = 0.45.
    # charge^2 = 150^2 + 75^2 + 2 gamma (150)(-75) = 28125 - 22500 gamma
    expected = {"medium": math.sqrt(28125 - 22500 * 0.60), "high": math.sqrt(28125 - 22500 * 0.75),
                "low": math.sqrt(28125 - 22500 * 0.45)}
    for name, value in expected.items():
        assert result["scenarios"][name]["delta"] == pytest.approx(value)
    assert result["binding_scenario"] == "low"
    assert result["capital"] == pytest.approx(math.sqrt(18000))


def test_fx_vega_within_bucket_correlation_uses_option_maturity():
    result = frtb.frtb_sbm_fx(fx_request(vega=[("EUR", 1, 100), ("EUR", 3, -50)]))
    rho = math.exp(-0.01 * 2 / 1)  # MAR21.93, rho_delta = 1 within one currency pair
    scenarios = {"medium": rho, "high": min(1.25 * rho, 1), "low": max(2 * rho - 1, 0.75 * rho)}
    for name, r in scenarios.items():
        assert result["scenarios"][name]["vega"] == pytest.approx(math.sqrt(12500 - 10000 * r))
    assert result["capital"] == pytest.approx(math.sqrt(12500 - 10000 * scenarios["low"]))
    assert result["degraded"] is True
    assert "curvature" in result["degraded_reason"]


def brute_force(buckets, gamma):
    """MAR21.4(4)-(5) written as explicit loops, independent of the matrix form."""
    k, s = [], []
    for ws, rho in buckets:
        q = sum(ws[i] ** 2 for i in range(len(ws))) + sum(
            rho[i][j] * ws[i] * ws[j] for i in range(len(ws)) for j in range(len(ws)) if i != j)
        k.append(math.sqrt(max(0, q)))
        s.append(sum(ws))
    n = len(k)
    total = sum(x ** 2 for x in k) + sum(gamma * s[b] * s[c] for b in range(n) for c in range(n) if b != c)
    if total < 0:
        s = [max(min(s[b], k[b]), -k[b]) for b in range(n)]
        total = sum(x ** 2 for x in k) + sum(gamma * s[b] * s[c] for b in range(n) for c in range(n) if b != c)
    return math.sqrt(total)


def test_fx_vega_matches_a_brute_force_loop_over_random_books():
    rng = np.random.default_rng(11)
    tenors = [0.5, 1.0, 3.0, 5.0, 10.0]
    for _ in range(50):
        vega = [(c, t, float(rng.normal(0, 1000))) for c in ("EUR", "JPY", "GBP") for t in tenors if rng.random() < 0.7]
        if not vega:
            continue
        result = frtb.frtb_sbm_fx(fx_request(vega=vega))
        buckets = []
        for c in sorted({v[0] for v in vega}):
            rows = [(t, s) for cc, t, s in vega if cc == c]
            rho = [[min(math.exp(-0.01 * abs(a - b) / min(a, b)), 1) for b, _ in rows] for a, _ in rows]
            buckets.append(([s for _, s in rows], rho))
        assert result["scenarios"]["medium"]["vega"] == pytest.approx(brute_force(buckets, 0.6), rel=1e-12)


def test_across_bucket_fallback_of_mar21_4_5_b():
    # K = (1, 1), S = (3, -3): 1 + 1 + 2*0.6*(3)(-3) = -8.8 < 0, so S becomes (1, -1): 2 - 1.2 = 0.8.
    gamma = np.array([[0, 0.6], [0.6, 0]])
    charge, alternative = frtb.across_buckets(np.array([1.0, 1.0]), np.array([3.0, -3.0]), gamma)
    assert alternative is True
    assert charge == pytest.approx(math.sqrt(0.8))


@pytest.mark.parametrize("request_,message", [
    (fx_request(), "at least one"),
    (fx_request(delta=[("USD", 1)]), "reporting currency"),
    (fx_request(vega=[("EUR", 2, 1)]), "0.5, 1, 3, 5 or 10"),
    (fx_request(delta=[("eur", 1)]), "pattern"),
    (fx_request(delta=[("EUR", 1e308), ("EUR", 1e308)]), "numerical limits"),
    (fx_request(delta=[("EUR", 1e308), ("JPY", 1e308)]), "numerical limits"),
])
def test_sbm_fx_refuses_invalid_input(request_, message):
    with pytest.raises(ValueError, match=message):
        frtb.frtb_sbm_fx(request_)


# ------------------------------------------------------------ examples and checker

EXAMPLES = [("frtb_imcc.json", frtb.frtb_imcc), ("frtb_ima_capital.json", frtb.frtb_ima_capital),
            ("frtb_pla.json", frtb.frtb_pla), ("frtb_backtest.json", frtb.frtb_backtest),
            ("frtb_sbm_fx.json", frtb.frtb_sbm_fx)]


@pytest.mark.parametrize("name,handler", EXAMPLES)
def test_examples_parse_and_produce_a_finite_result(name, handler):
    result = handler(json.loads((ROOT / "examples" / name).read_text(encoding="utf-8")))
    assert result["data_mode"] == "synthetic"
    assert result["currency"] == "USD"
    assert "not market data" in result["source"]


def load_checker():
    # run_path compiles from source without writing __pycache__ into the shipped skill directory.
    path = ROOT / "plugins" / "risk-desk" / "skills" / "risk-frtb" / "scripts" / "check_artifact.py"
    return SimpleNamespace(**runpy.run_path(str(path)))


@pytest.mark.parametrize("name,handler", EXAMPLES)
def test_the_checker_accepts_every_example_result_and_rejects_a_tampered_one(name, handler, tmp_path, capsys):
    checker = load_checker()
    result = handler(json.loads((ROOT / "examples" / name).read_text(encoding="utf-8")))
    good = tmp_path / "good.json"
    good.write_text(json.dumps(result), encoding="utf-8")
    assert checker.main(str(good)) == 0
    key = {"frtb_imcc.json": "imcc", "frtb_ima_capital.json": "aggregate_capital", "frtb_pla.json": "zone",
           "frtb_backtest.json": "passes", "frtb_sbm_fx.json": "capital"}[name]
    result[key] = {"zone": "red", "passes": not result.get("passes")}.get(key, 1.0)
    bad = tmp_path / "bad.json"
    bad.write_text(json.dumps(result), encoding="utf-8")
    assert checker.main(str(bad)) == 1
    assert "FAIL" in capsys.readouterr().out
