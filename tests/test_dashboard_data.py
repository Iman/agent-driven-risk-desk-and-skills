"""Shaping. In process, no socket, no subprocess.

The property these tests exist to hold is that the dashboard and the saved
report page cannot disagree about a number, because both come from one
shaping path. A second implementation that agreed today would be free to
stop agreeing, and the disagreement would appear as two different figures
in front of the same person.
"""
import json
from pathlib import Path

import pytest

from riskdesk.analytics import portfolio_exposure, stress_test, tail_risk
from riskdesk.dashboard import data
from riskdesk.report import report_payload

EXAMPLES = Path(__file__).resolve().parent.parent / "examples"

pytestmark = pytest.mark.unit


@pytest.fixture
def desk():
    return data.load_desk(EXAMPLES / "energy_stress.json",
                          EXAMPLES / "energy_tail.json",
                          EXAMPLES / "energy_book.json")


@pytest.fixture
def payload(desk):
    return data.build(desk)


def test_the_dashboard_and_the_report_agree_by_construction(desk, payload):
    """Not "the numbers match today" but "there is one shaping path"."""
    shaped = report_payload(
        stress_test(desk["stress"]), tail_risk(desk["tail"]),
        desk["tail"]["pnl"], portfolio_exposure(desk["exposure"]))
    assert payload["tail"] == shaped["tail"]
    assert payload["scenarios"] == shaped["scenarios"]
    assert payload["input_sha256"] == shaped["input_sha256"]
    assert payload["sign_convention"] == shaped["sign_convention"]
    for key in ("gross_exposure", "net_exposure", "nav", "net_by_asset",
                "gross_shares"):
        assert payload["exposure"][key] == shaped["exposure"][key], key


def test_the_energy_book_shapes_into_the_figures_it_should(payload):
    exposure = payload["exposure"]
    assert exposure["gross_exposure"] == 14100000.0
    assert exposure["net_exposure"] == 6000000.0
    assert exposure["counts"] == {"long": 4, "short": 2, "flat": 0}
    assert exposure["gross_leverage_text"] == "1.175x"
    assert exposure["net_leverage_text"] == "0.5x"
    assert payload["degraded"] is False


def test_the_worst_scenario_is_the_biggest_loss_not_the_last_one(payload):
    worst = payload["worst_scenario"]
    assert worst["name"] == "global_energy_demand_collapse_shape"
    assert worst["loss"] == max(s["loss"] for s in payload["scenarios"])


def test_every_view_is_named_once_and_in_order(payload):
    slugs = [view["slug"] for view in payload["views"]]
    assert slugs == ["overview", "exposure", "stress", "tail", "xva"]
    assert len(set(slugs)) == len(slugs)


# Each absent view has to deny the reading a reader would otherwise take.
# An empty panel says zero unless something says otherwise, so every one of
# these messages carries its own denial, and the denial is what is pinned.
DENIALS = {
    "exposure": "not because the exposure is zero",
    "tail": "not because the risk is zero",
    "xva": "Nothing here is zero",
}


def test_an_absent_input_says_absent_and_denies_being_a_zero(desk):
    bare = data.load_desk(EXAMPLES / "energy_stress.json")
    payload = data.build(bare)
    assert payload["exposure"] is None
    assert payload["tail"] is None
    for view, denial in DENIALS.items():
        reason = data.absent_reason(view, payload)
        assert reason, view
        assert denial in reason, view


def test_a_loaded_input_has_no_absent_reason(payload):
    for view in ("overview", "exposure", "stress", "tail"):
        assert data.absent_reason(view, payload) is None


def test_the_xva_panel_refuses_to_pretend_it_can_run_ore(payload):
    """The adapter needs a local project directory, a fresh output
    directory and a separate process. A web page offering a button for
    that would be offering something it cannot do."""
    xva = payload["xva"]
    assert xva["available"] is False
    assert "does not run ORE" in xva["reason"]
    assert "Nothing here is zero" in xva["reason"]
    assert xva["command"].startswith("riskdesk xva --project")


def test_an_ore_result_is_reprinted_with_its_provenance(tmp_path):
    written = {
        "backend": "Open Source Risk Engine", "backend_version": "1.8.16.0",
        "backend_git_hash": "b1f2393", "currency": "EUR",
        "as_of": "2016-02-05", "data_mode": "upstream-example",
        "requested_xva_flags": {"cva": "Y", "mva": "N"},
        "errors": [],
        "reports": {"xva": {"rows": [{"NettingSetId": "n"}, {"TradeId": "t"}]},
                    "exposure_trade_Swap": {"rows": []},
                    "exposure_nettingset_n": {"rows": []}},
        "assumptions": ["Risk-neutral ORE valuation."],
    }
    path = tmp_path / "riskdesk-xva.json"
    path.write_text(json.dumps(written), encoding="utf-8")
    desk = data.load_desk(EXAMPLES / "energy_stress.json", xva_path=path)
    xva = data.build(desk)["xva"]
    assert xva["available"] is True
    assert xva["row_count"] == 2
    assert xva["backend_version"] == "1.8.16.0"
    assert xva["requested_flags"] == {"cva": "Y", "mva": "N"}
    assert xva["exposure_reports"] == ["exposure_nettingset_n",
                                       "exposure_trade_Swap"]


def test_a_degraded_input_degrades_the_whole_desk():
    desk = data.load_desk(EXAMPLES / "energy_stress.json",
                          EXAMPLES / "tail.json")
    payload = data.build(desk)
    assert payload["degraded"] is True
    assert "Fewer than 20 observations" in payload["degraded_reason"]


def test_the_paths_it_read_are_carried_for_the_page_to_print(desk, payload):
    assert payload["paths"]["stress"].endswith("energy_stress.json")
    assert payload["paths"]["exposure"].endswith("energy_book.json")
    assert payload["paths"]["xva"] is None
