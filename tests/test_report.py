"""The HTML report: shaping in process, the file itself through the CLI."""
import json
from pathlib import Path
import subprocess
import sys

import pytest

from riskdesk.analytics import stress_test, tail_risk
from riskdesk.report import (SIGN_CONVENTION, build_report, histogram,
                             render_html, report_payload)

ROOT = Path(__file__).resolve().parent.parent


def meta():
    return dict(as_of="2026-09-12", currency="USD", source="synthetic test",
                data_mode="synthetic")


def stress_request():
    return dict(**meta(), nav=1000, positions=[
        {"id": "long", "asset": "A", "market_value": 600,
         "instrument_type": "linear"},
        {"id": "short", "asset": "B", "market_value": -200,
         "instrument_type": "linear"}],
        scenarios=[{"name": "down", "shocks": {"A": -.1, "B": -.2}}])


def tail_request():
    return dict(**meta(), pnl=[-100, -50, 0, 50], confidence=.625,
                horizon_days=1, portfolio_value=1000)


@pytest.mark.unit
def test_histogram_counts_every_observation_once():
    bins = histogram([1, 2, 3, 4, 5, 6, 7, 8], bins=4)
    assert sum(b["count"] for b in bins) == 8
    assert bins[0]["low"] == 1 and bins[-1]["high"] == 8
    assert all(b["low"] < b["high"] for b in bins)


@pytest.mark.unit
def test_histogram_puts_the_largest_value_in_the_last_bin():
    """The top edge is inclusive; without that the maximum falls outside."""
    bins = histogram([0, 10], bins=2)
    assert [b["count"] for b in bins] == [1, 1]


@pytest.mark.unit
def test_identical_observations_still_produce_a_drawable_range():
    bins = histogram([5.0, 5.0, 5.0], bins=3)
    assert sum(b["count"] for b in bins) == 3
    assert bins[0]["low"] < bins[-1]["high"]


@pytest.mark.unit
@pytest.mark.parametrize("values", [[1.0], [1.0, float("inf")]])
def test_undrawable_observations_are_refused(values):
    with pytest.raises(ValueError):
        histogram(values)


@pytest.mark.unit
def test_contributions_are_ordered_worst_loss_first():
    payload = report_payload(stress_test(stress_request()))
    values = [row["value"] for row in payload["scenarios"][0]["contributions"]]
    assert values == sorted(values)
    assert payload["scenarios"][0]["top_losses"][0]["id"] == "long"


@pytest.mark.unit
def test_a_tail_result_without_its_observations_is_refused():
    stress = stress_test(stress_request())
    with pytest.raises(ValueError):
        report_payload(stress, tail_risk(tail_request()))


@pytest.mark.unit
def test_two_currencies_are_never_printed_under_one_heading():
    stress = stress_test(stress_request())
    other = tail_request()
    other["currency"] = "EUR"
    with pytest.raises(ValueError, match="one currency"):
        report_payload(stress, tail_risk(other), other["pnl"])


@pytest.mark.unit
def test_a_degraded_tail_degrades_the_whole_page():
    """The stress input is clean and the tail input is not. A page that
    reported "not degraded" would be reassuring and wrong."""
    request = tail_request()
    stress = stress_test(stress_request())
    assert not stress["degraded"]
    payload = report_payload(stress, tail_risk(request), request["pnl"])
    assert payload["degraded"]
    assert "Fewer than 20 observations" in payload["degraded_reason"]


@pytest.mark.unit
def test_the_page_prints_the_sign_convention_and_the_degraded_flag():
    request = tail_request()
    document = render_html(report_payload(
        stress_test(stress_request()), tail_risk(request), request["pnl"]))
    assert SIGN_CONVENTION.split(";")[0] in document
    assert ">degraded<" in document
    assert "Fewer than 20 observations" in document


@pytest.mark.unit
def test_an_absent_tail_is_stated_rather_than_left_blank():
    document = render_html(report_payload(stress_test(stress_request())))
    assert "No tail result was supplied" in document
    assert "not because the risk is zero" in document


@pytest.mark.unit
def test_the_page_loads_nothing_from_anywhere():
    request = tail_request()
    document, _ = build_report(stress_request(), request)
    assert "http://" not in document
    assert "https://" not in document
    assert "<script" not in document.lower()


@pytest.mark.unit
def test_position_identifiers_cannot_inject_markup():
    request = stress_request()
    request["positions"][0]["id"] = "<script>alert(1)</script>"
    document, _ = build_report(request)
    assert "<script>alert(1)</script>" not in document
    assert "&lt;script&gt;" in document


@pytest.mark.integration
def test_the_cli_writes_a_page_with_both_panels(tmp_path):
    output = tmp_path / "nested" / "report.html"
    finished = subprocess.run(
        [sys.executable, "-m", "riskdesk.cli", "report",
         "--input", str(ROOT / "examples" / "energy_stress.json"),
         "--tail", str(ROOT / "examples" / "energy_tail.json"),
         "--output", str(output)],
        capture_output=True, text=True, cwd=str(ROOT),
        env=dict(PATH="/usr/bin:/bin", PYTHONPATH=str(ROOT / "src")))
    assert finished.returncode == 0, finished.stdout + finished.stderr
    summary = json.loads(finished.stdout)
    assert summary["tail_included"] is True
    assert summary["degraded"] is False
    assert summary["scenarios"] == ["european_gas_supply_dislocation_shape",
                                    "global_energy_demand_collapse_shape"]
    document = output.read_text(encoding="utf-8")
    assert document.startswith("<!DOCTYPE html>")
    assert "european_gas_supply_dislocation_shape" in document
    assert "Expected Shortfall" in document
    assert "<svg" in document


@pytest.mark.integration
def test_the_cli_reports_a_bad_report_input_as_json_and_nonzero(tmp_path):
    bad = tmp_path / "bad.json"
    bad.write_text("{}")
    finished = subprocess.run(
        [sys.executable, "-m", "riskdesk.cli", "report",
         "--input", str(bad), "--output", str(tmp_path / "out.html")],
        capture_output=True, text=True, cwd=str(ROOT),
        env=dict(PATH="/usr/bin:/bin", PYTHONPATH=str(ROOT / "src")))
    assert finished.returncode == 1
    assert json.loads(finished.stdout)["error"] == "ValidationError"
    assert not (tmp_path / "out.html").exists()
