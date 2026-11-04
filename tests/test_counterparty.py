"""SA-CCR and exposure-profile tests.

The SA-CCR figures are the published worked examples of the Basel Framework,
CRE99.20 to CRE99.97 (version effective 1 January 2023), which repeat BCBS 279
Annex 4a (March 2014). Those documents round intermediate values and the
final EAD to whole thousands, so the comparisons are at that rounding.
"""
import json
import math
from pathlib import Path

import pytest
from pydantic import ValidationError
from scipy.stats import norm

from riskdesk.counterparty import exposure_profile_summary, saccr_ead

pytestmark = pytest.mark.unit


def meta(**extra):
    return dict(as_of="2026-11-04", currency="USD", source="synthetic test",
                data_mode="synthetic", **extra)


def ir(id, notional, value, maturity, position, ccy, start, end, **extra):
    return dict(id=id, asset_class="interest_rate", notional=notional, market_value=value,
                maturity=maturity, position=position, hedging_set=ccy, start=start, end=end,
                **extra)


# CRE99.22 table: two swaps and a physically settled 1 into 10 year swaption.
EXAMPLE_1 = [ir("1", 10_000, 30, 10, "long", "USD", 0, 10),
             ir("2", 10_000, -20, 4, "short", "USD", 0, 4),
             ir("3", 5_000, 50, 11, "long", "EUR", 1, 11, option="put",
                underlying_price=0.06, strike=0.05, exercise=1)]
# CRE99.41 table: long AA single name, short BBB single name, long IG index.
EXAMPLE_2 = [dict(id="4", asset_class="credit", notional=10_000, market_value=20, maturity=3,
                  position="long", reference="Firm A", rating="AA", start=0, end=3),
             dict(id="5", asset_class="credit", notional=10_000, market_value=-40, maturity=6,
                  position="short", reference="Firm B", rating="BBB", start=0, end=6),
             dict(id="6", asset_class="credit", notional=10_000, market_value=0, maturity=5,
                  position="long", reference="CDX.IG 5y", index=True, rating="IG",
                  start=0, end=5)]
# CRE99.59 table: WTI long 9 months, Brent short 2 years, silver long 5 years.
EXAMPLE_3 = [dict(id="7", asset_class="commodity", notional=10_000, market_value=-50,
                  maturity=0.75, position="long", hedging_set="energy", reference="crude oil"),
             dict(id="8", asset_class="commodity", notional=20_000, market_value=-30,
                  maturity=2, position="short", hedging_set="energy", reference="crude oil"),
             dict(id="9", asset_class="commodity", notional=10_000, market_value=100,
                  maturity=5, position="long", hedging_set="metals", reference="silver")]
# CRE99 example 5 margin terms: weekly margining, TH 0, MTA 5, NICA 150, net collateral 200.
WEEKLY = dict(margined=True, collateral=200, threshold=0, minimum_transfer_amount=5, nica=150,
              remargining_period_business_days=5, mpor_business_days=14)


def run(trades, **extra):
    return saccr_ead(meta(netting_set="NS", trades=trades, **extra))


def test_example_1_interest_rate_matches_cre99_40():
    result = run(EXAMPLE_1)
    trades = {t["id"]: t for t in result["trades"]}
    # CRE99.29 adjusted notionals and CRE99.32 delta and effective notional
    assert [round(trades[i]["adjusted_notional"]) for i in "123"] == [78_694, 36_254, 37_428]
    assert round(trades["3"]["supervisory_delta"], 4) == -0.2694
    assert round(trades["3"]["effective_notional"]) == -10_083
    sets = {h["hedging_set"]: h for h in result["hedging_sets"]}
    usd, eur = sets["USD"], sets["EUR"]
    assert round(usd["effective_notional"]) == 59_270           # CRE99.37
    assert round(eur["effective_notional"]) == 10_083
    assert usd["addon"] == pytest.approx(296.35, abs=0.005)      # CRE99.38
    assert eur["addon"] == pytest.approx(50.415, abs=0.0005)
    assert round(result["addon_aggregate"]) == 347               # CRE99.39
    assert result["replacement_cost"] == 60 and result["multiplier"] == 1
    assert round(result["ead"]) == 569                           # CRE99.40
    assert result["degraded"] is False


def test_example_2_credit_matches_cre99_58():
    result = run(EXAMPLE_2)
    trades = {t["id"]: t for t in result["trades"]}
    assert [round(trades[i]["adjusted_notional"]) for i in "456"] == [27_858, 51_836, 44_240]
    entities = {e["reference"]: e["addon"] for e in result["hedging_sets"][0]["entities"]}
    assert {k: round(v) for k, v in entities.items()} == {
        "Firm A": 106, "Firm B": -280, "CDX.IG 5y": 168}
    assert round(result["addon_aggregate"]) == 282               # CRE99.55
    assert round(result["multiplier"], 3) == 0.965               # CRE99.57
    assert result["replacement_cost"] == 0
    assert round(result["ead"]) == 381                           # CRE99.58


def test_example_3_commodity_matches_cre99_76():
    result = run(EXAMPLE_3)
    trades = {t["id"]: t for t in result["trades"]}
    assert trades["7"]["maturity_factor"] == pytest.approx(math.sqrt(9 / 12))  # CRE99.65
    energy, metals = result["hedging_sets"]
    assert round(energy["entities"][0]["effective_notional"]) == -11_340      # CRE99.68
    assert round(energy["addon"]) == 2_041 and round(metals["addon"]) == 1_800
    assert round(result["addon_aggregate"]) == 3_841                         # CRE99.74
    assert round(result["ead"]) == 5_406                                     # CRE99.76


def test_example_4_combined_rates_and_credit_matches_bcbs279():
    result = run(EXAMPLE_1 + EXAMPLE_2)
    assert result["replacement_cost"] == 40                                 # CRE99.77
    assert round(result["addon_aggregate"]) == 629
    assert round(result["ead"]) == 936                                       # BCBS 279 Annex 4a


def test_example_5_margined_matches_cre99_97():
    result = run(EXAMPLE_1 + EXAMPLE_3, **WEEKLY)
    trades = {t["id"]: t for t in result["trades"]}
    assert trades["1"]["maturity_factor"] == pytest.approx(1.5 * math.sqrt(14 / 250))  # CRE99.84
    assert [round(trades[i]["effective_notional"]) for i in "123"] == [27_934, -12_869, -3_579]
    assert round(result["addon_by_asset_class"]["interest_rate"]) == 123     # CRE99.89
    assert round(result["addon_by_asset_class"]["commodity"]) == 1_278       # CRE99.94
    assert round(result["addon_aggregate"]) == 1_401                         # CRE99.95
    assert round(result["multiplier"], 3) == 0.958                           # CRE99.96
    assert result["replacement_cost"] == 0
    assert round(result["ead"]) == 1_879                                     # CRE99.97
    assert result["cap_applied"] is False and result["unmargined_ead"] > result["ead"]


@pytest.mark.parametrize("v,c,mta,nica,rc", [
    (80, 90, 1, 10, 0),        # CRE99.99 to 99.101
    (80, 79.5, 1, 0, 1),       # CRE99.102 to 99.104
    (-50, -50, 0, 0, 0),       # CRE99.106 to 99.109
    (-50, -60, 0, -10, 10),    # CRE99.110 to 99.112
    (50, 80, 0, 20, 0),        # CRE99.113 to 99.115
])
def test_margined_replacement_cost_matches_cre99_margin_examples(v, c, mta, nica, rc):
    trade = ir("x", 1_000, v, 5, "long", "EUR", 0, 5)
    result = run([trade], margined=True, collateral=c, threshold=0, minimum_transfer_amount=mta,
                 nica=nica, remargining_period_business_days=1, mpor_business_days=10)
    assert result["replacement_cost"] == pytest.approx(rc)


def test_fx_hedging_sets_offset_within_a_pair_only():
    # CRE52.59 by hand: EUR/USD D = 100*sqrt(0.5) - 40, GBP/USD D = 50; SF 4%.
    trades = [dict(id="a", asset_class="fx", notional=100, market_value=1, maturity=0.5,
                   position="long", hedging_set="EUR/USD"),
              dict(id="b", asset_class="fx", notional=40, market_value=-3, maturity=2,
                   position="short", hedging_set="EUR/USD"),
              dict(id="c", asset_class="fx", notional=50, market_value=4, maturity=3,
                   position="short", hedging_set="GBP/USD")]
    addon = 0.04 * abs(100 * math.sqrt(0.5) - 40) + 0.04 * 50
    result = run(trades)
    assert {h["hedging_set"]: h["addon"] for h in result["hedging_sets"]} == pytest.approx(
        {"EUR/USD": 0.04 * abs(100 * math.sqrt(0.5) - 40), "GBP/USD": 0.04 * 50})
    assert result["addon_aggregate"] == pytest.approx(addon)
    assert result["ead"] == pytest.approx(1.4 * (2 + addon))


def test_commodity_types_offset_partially_within_a_hedging_set():
    # CRE52.70 by hand: crude oil SF 18%, electricity SF 40%, rho 0.4 for both, energy set.
    trades = [dict(id="a", asset_class="commodity", notional=1_000, market_value=0, maturity=1,
                   position="long", hedging_set="energy", reference="crude oil"),
              dict(id="b", asset_class="commodity", notional=500, market_value=0, maturity=1,
                   position="short", hedging_set="energy", reference="power", electricity=True),
              dict(id="c", asset_class="commodity", notional=300, market_value=0, maturity=1,
                   position="long", hedging_set="agricultural", reference="corn")]
    oil, power = 0.18 * 1_000, 0.40 * -500
    energy = math.sqrt((0.4 * oil + 0.4 * power) ** 2 + 0.84 * oil ** 2 + 0.84 * power ** 2)
    result = run(trades)
    assert {h["hedging_set"]: h["addon"] for h in result["hedging_sets"]} == pytest.approx(
        {"energy": energy, "agricultural": 0.18 * 300})
    assert result["addon_aggregate"] == pytest.approx(energy + 54)


def test_equity_single_factor_aggregation_by_hand():
    # CRE52.66: single name SF 32% rho 0.5, index SF 20% rho 0.8.
    trades = [dict(id="a", asset_class="equity", notional=1_000, market_value=0, maturity=1,
                   position="long", reference="ACME"),
              dict(id="b", asset_class="equity", notional=400, market_value=0, maturity=1,
                   position="short", reference="ACME"),
              dict(id="c", asset_class="equity", notional=2_000, market_value=0, maturity=1,
                   position="short", reference="SPX", index=True)]
    single, index = 0.32 * 600, 0.20 * -2_000
    addon = math.sqrt((0.5 * single + 0.8 * index) ** 2
                      + (1 - 0.25) * single ** 2 + (1 - 0.64) * index ** 2)
    result = run(trades)
    assert result["addon_aggregate"] == pytest.approx(addon)
    assert result["multiplier"] == 1


def test_option_deltas_follow_cre52_40_signs_and_parity():
    def delta(option, position, shift=0.0, price=100, strike=100, **kw):
        trade = dict(id="o", asset_class="equity", notional=100, market_value=0, maturity=1,
                     position=position, reference="X", option=option, underlying_price=price,
                     strike=strike, exercise=1, **kw)
        return run([trade])["trades"][0]["supervisory_delta"]
    d1 = 0.5 * 1.2  # at the money: ln(P/K) = 0, sigma 120% single-name equity, T = 1
    assert delta("call", "long") == pytest.approx(norm.cdf(d1))
    assert delta("call", "short") == pytest.approx(-norm.cdf(d1))
    assert delta("put", "long") == pytest.approx(-norm.cdf(-d1))
    assert delta("put", "short") == pytest.approx(norm.cdf(-d1))
    assert delta("call", "long") - delta("put", "long") == pytest.approx(1.0)


def test_negative_rate_option_uses_the_faq2_shift():
    trade = ir("o", 1_000, 0, 6, "long", "EUR", 1, 6, option="call",
               underlying_price=-0.002, strike=0.001, exercise=1, shift=0.01)
    d1 = (math.log(0.008 / 0.011) + 0.5 * 0.25) / 0.5
    assert run([trade])["trades"][0]["supervisory_delta"] == pytest.approx(norm.cdf(d1))


def test_floors_and_maturity_buckets():
    short = ir("s", 1_000, 0, 0.01, "long", "USD", 0, 0.01)
    result = run([short])["trades"][0]
    assert result["supervisory_duration"] == pytest.approx(10 / 250)     # CRE52.34 floor
    assert result["maturity_factor"] == pytest.approx(math.sqrt(10 / 250))  # CRE52.48 floor
    for end, bucket in ((0.99, 0), (1, 1), (5, 1), (5.01, 2)):
        hs = run([ir("b", 1_000, 0, end, "long", "USD", 0, end)])["hedging_sets"][0]
        assert [i for i, d in enumerate(hs["bucket_effective_notionals"]) if d] == [bucket]


def test_three_maturity_buckets_use_the_cre52_57_offset_formula():
    trades = [ir("1", 1_000, 0, 0.5, "long", "USD", 0, 0.5),
              ir("2", 1_000, 0, 3, "short", "USD", 0, 3),
              ir("3", 1_000, 0, 10, "long", "USD", 0, 10)]
    sd = [(1 - math.exp(-0.05 * e)) / 0.05 for e in (0.5, 3, 10)]
    d1, d2, d3 = 1_000 * sd[0] * math.sqrt(0.5), -1_000 * sd[1], 1_000 * sd[2]
    en = math.sqrt(d1 ** 2 + d2 ** 2 + d3 ** 2 + 1.4 * d1 * d2 + 1.4 * d2 * d3 + 0.6 * d1 * d3)
    assert run(trades)["addon_aggregate"] == pytest.approx(0.005 * en)


def test_excess_collateral_drives_the_multiplier_to_its_floor():
    result = run(EXAMPLE_1, collateral=1e9)
    assert result["multiplier"] == pytest.approx(0.05)
    assert result["replacement_cost"] == 0


def test_large_positive_value_with_a_tiny_addon_does_not_overflow():
    trade = ir("t", 1e-6, 1e12, 1, "long", "USD", 0, 1)
    result = run([trade])
    assert result["multiplier"] == 1 and result["replacement_cost"] == 1e12


def test_margined_ead_is_capped_at_the_unmargined_ead():
    # CRE52.2 FAQ1: maturity under ten business days makes the margined MF larger.
    trade = ir("t", 1_000_000, 0, 0.02, "long", "USD", 0, 0.02)
    result = run([trade], margined=True, threshold=0, minimum_transfer_amount=0, nica=0,
                 remargining_period_business_days=1, mpor_business_days=10)
    assert result["cap_applied"] is True
    assert result["ead"] == pytest.approx(result["unmargined_ead"])


@pytest.mark.parametrize("change", [
    {"trades": []},
    {"trades": [EXAMPLE_1[0], EXAMPLE_1[0]]},
    {"trades": [dict(EXAMPLE_1[0], start=None)]},
    {"trades": [dict(EXAMPLE_1[0], end=0)]},
    {"trades": [dict(EXAMPLE_1[0], hedging_set="usd")]},
    {"trades": [dict(EXAMPLE_1[0], notional=0)]},
    {"trades": [dict(EXAMPLE_1[0], market_value=float("nan"))]},
    {"trades": [dict(EXAMPLE_1[0], rating="AA")]},
    {"trades": [dict(EXAMPLE_1[0], shift=0.01)]},
    {"trades": [dict(EXAMPLE_1[2], strike=None)]},
    {"trades": [dict(EXAMPLE_1[2], exercise=12)]},
    {"trades": [dict(EXAMPLE_2[0], rating="IG")]},
    {"trades": [dict(EXAMPLE_2[2], rating="AA")]},
    {"trades": [dict(EXAMPLE_2[0], reference=None)]},
    {"trades": [dict(EXAMPLE_3[0], hedging_set="oil")]},
    {"trades": [dict(EXAMPLE_3[2], electricity=True)]},
    {"trades": [dict(id="f", asset_class="fx", notional=1, market_value=0, maturity=1,
                     position="long", hedging_set="USD/USD")]},
    {"trades": [EXAMPLE_2[0], dict(EXAMPLE_2[1], reference="Firm A")]},
    {"margined": True},
    {"threshold": 0},
    dict(WEEKLY, mpor_business_days=13),
    {"surprise": 1},
])
def test_invalid_netting_sets_are_refused(change):
    payload = meta(netting_set="NS", trades=EXAMPLE_1)
    payload.update(change)
    with pytest.raises(ValueError):
        saccr_ead(payload)


def profile(times, ee, pfe=None, **extra):
    return meta(rows=[dict(NettingSet="CPTY_A", Date=None, Time=t, EPE=None, ENE=None,
                           PFE=(pfe or ee)[i], ExpectedCollateral=None, BaselEE=ee[i],
                           BaselEEE=None, TimeWeightedBaselEPE=None,
                           TimeWeightedBaselEEPE=None)
                      for i, t in enumerate(times)], **extra)


def test_profile_summary_by_hand():
    # EE 10, 30, 20, 25 at 0, 0.25, 0.5, 1.0: Effective EE 10, 30, 30, 30.
    result = exposure_profile_summary(profile([0, 0.25, 0.5, 1.0, 2.0], [10, 30, 20, 25, 40],
                                              pfe=[10, 60, 70, 65, 50]))
    assert [r["effective_ee"] for r in result["effective_ee"]] == [10, 30, 30, 30, 40]
    assert result["epe"] == pytest.approx(30 * 0.25 + 20 * 0.25 + 25 * 0.5)
    assert result["effective_epe"] == pytest.approx(30.0)
    assert (result["peak_pfe"], result["peak_pfe_time"]) == (70, 0.5)
    assert result["averaging_horizon_years"] == 1.0 and result["dates_in_first_year"] == 3
    assert result["netting_set"] == "CPTY_A" and result["degraded"] is False


def test_profile_summary_converges_to_the_closed_form_integrals():
    # EE(t) = sin(pi t): EPE = 2/pi, Effective EE = 1 after t = 0.5, Effective EPE = 1/pi + 0.5.
    n = 2_000
    times = [k / n for k in range(n + 1)]
    result = exposure_profile_summary(profile(times, [math.sin(math.pi * t) for t in times]))
    # Right-point sums of a function with bounded slope pi err by at most pi/n.
    assert result["epe"] == pytest.approx(2 / math.pi, abs=math.pi / n)
    assert result["effective_epe"] == pytest.approx(1 / math.pi + 0.5, abs=math.pi / n)


def test_short_netting_set_averages_to_its_last_date():
    result = exposure_profile_summary(profile([0, 0.25, 0.5], [0, 4, 2]))
    assert result["averaging_horizon_years"] == 0.5
    assert result["epe"] == pytest.approx((4 * 0.25 + 2 * 0.25) / 0.5)
    assert result["effective_epe"] == pytest.approx(4.0)
    assert result["degraded"] is False


def test_grid_without_a_one_year_date_is_degraded():
    result = exposure_profile_summary(profile([0, 0.5, 0.9, 1.1], [1, 2, 3, 4]))
    assert result["degraded"] is True
    assert "0.9 years" in result["degraded_reason"]


@pytest.mark.parametrize("times,ee,extra", [
    ([0.1, 0.5], [1, 1], {}),                 # first row is not the as-of date
    ([0, 0.5, 0.5], [1, 1, 1], {}),            # time not increasing
    ([0, 1.5], [1, 1], {}),                    # no date inside the first year
    ([0, 0.5], [1, -1], {}),                   # signed exposure
    ([0, 0.5], [1, None], {}),                 # ORE null
])
def test_unusable_profiles_are_refused(times, ee, extra):
    with pytest.raises(ValueError):
        exposure_profile_summary(profile(times, ee, **extra))


def test_profile_rows_from_two_netting_sets_are_refused():
    payload = profile([0, 0.5], [1, 1])
    payload["rows"][1]["NettingSet"] = "CPTY_B"
    with pytest.raises(ValueError):
        exposure_profile_summary(payload)


def test_trade_level_report_rows_are_refused():
    payload = profile([0, 0.5], [1, 1])
    payload["rows"][0]["AllocatedEPE"] = 1.0
    with pytest.raises(ValueError):
        exposure_profile_summary(payload)


def test_shipped_examples_run_and_are_not_degraded():
    examples = Path(__file__).resolve().parent.parent / "examples"
    saccr = saccr_ead(json.loads((examples / "counterparty_saccr.json").read_text()))
    assert round(saccr["ead"]) == 1_879 and saccr["data_mode"] == "synthetic"
    summary = exposure_profile_summary(json.loads((examples / "counterparty_profile.json").read_text()))
    assert summary["degraded"] is False and summary["averaging_horizon_years"] == 1.0


def load_checker(skill):
    import importlib.util
    path = (Path(__file__).resolve().parent.parent / "plugins" / "risk-desk" / "skills" / skill
            / "scripts" / "check_artifact.py")
    spec = importlib.util.spec_from_file_location("check_" + skill.replace("-", "_"), path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_check_artifact_accepts_results_and_rejects_tampering(tmp_path, capsys):
    checker = load_checker("risk-counterparty")
    margined = run(EXAMPLE_1 + EXAMPLE_3, **WEEKLY)
    summary = exposure_profile_summary(profile([0, 0.5, 1.0], [1, 3, 2]))
    for result in (margined, run(EXAMPLE_2), summary):
        path = tmp_path / "ok.json"
        path.write_text(json.dumps(result))
        assert checker.main(str(path)) == 0, capsys.readouterr().out
    margined["ead"] *= 1.01
    summary["effective_ee"][2]["effective_ee"] = 0.5
    for result in (margined, summary):
        path = tmp_path / "bad.json"
        path.write_text(json.dumps(result))
        assert checker.main(str(path)) == 1
    assert "FAIL" in capsys.readouterr().out


PARTIAL = "partially verified"


def test_fx_and_equity_add_ons_are_labelled_partially_verified_and_others_are_not():
    """The Basel Framework publishes no FX or equity worked example, so a
    result with those classes says so in its own assumptions."""
    assert not any(PARTIAL in a for a in run(EXAMPLE_1)["assumptions"])
    fx = dict(id="f", asset_class="fx", notional=100, market_value=1, maturity=0.5,
              position="long", hedging_set="EUR/USD")
    equity = dict(id="e", asset_class="equity", notional=1_000, market_value=0, maturity=1,
                  position="long", reference="Firm A")
    for trades in ([fx], [equity], EXAMPLE_1 + [fx]):
        assert sum(PARTIAL in a for a in run(trades)["assumptions"]) == 1
