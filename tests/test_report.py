"""The HTML report: shaping in process, the file itself through the CLI."""
import json
from pathlib import Path
import re
import subprocess
import sys

import pytest

from riskdesk.analytics import portfolio_exposure, stress_test, tail_risk
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


def exposure_request():
    """A long, a short and a position marked at zero, which is the set of
    signs the ladder has to draw differently from each other."""
    return dict(**meta(), nav=1000, positions=[
        {"id": "long", "asset": "A", "market_value": 600,
         "instrument_type": "linear"},
        {"id": "short", "asset": "B", "market_value": -200,
         "instrument_type": "linear"},
        {"id": "flat", "asset": "C", "market_value": 0,
         "instrument_type": "linear"}])


def exposure_payload():
    return report_payload(stress_test(stress_request()), None, None,
                          portfolio_exposure(exposure_request()))["exposure"]


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


@pytest.mark.unit
def test_net_by_asset_is_ordered_longs_first_then_shorts():
    """Descending signed value, so the ladder separates the two sides
    rather than interleaving them by name."""
    rows = exposure_payload()["net_by_asset"]
    values = [row["value"] for row in rows]
    assert values == sorted(values, reverse=True)
    assert values == [600.0, 0.0, -200.0]
    assert [row["asset"] for row in rows] == ["A", "C", "B"]


@pytest.mark.unit
def test_gross_shares_are_ordered_largest_first_and_never_negative():
    rows = exposure_payload()["gross_shares"]
    shares = [row["share"] for row in rows]
    assert shares == sorted(shares, reverse=True)
    assert all(share >= 0 for share in shares)
    assert rows[0]["asset"] == "A"
    assert sum(shares) == pytest.approx(1.0)


@pytest.mark.unit
def test_the_exposure_panel_carries_its_own_provenance():
    exposure = exposure_payload()
    assert exposure["input_sha256"]
    assert exposure["input_sha256"] != stress_test(
        stress_request())["input_sha256"]
    assert exposure["source"] == "synthetic test"
    assert exposure["nav"] == 1000
    assert exposure["gross_exposure"] == 800
    assert exposure["net_exposure"] == 400
    assert exposure["gross_leverage"] == pytest.approx(0.8)
    assert exposure["net_leverage"] == pytest.approx(0.4)


@pytest.mark.unit
def test_a_short_is_drawn_on_the_other_side_of_the_zero_line():
    """The whole point of the ladder: a reader must not have to read the
    minus sign to see that B is short."""
    from riskdesk.report import _net_by_asset_svg

    document = _net_by_asset_svg(exposure_payload(), "USD")
    long_bar = re.search(r'<rect x="([\d.]+)"[^>]*class="bar long"', document)
    short_bar = re.search(r'<rect x="([\d.]+)"[^>]*class="bar short"',
                          document)
    assert long_bar and short_bar
    assert float(short_bar.group(1)) < float(long_bar.group(1))
    assert ">short<" in document and ">long<" in document


@pytest.mark.unit
def test_a_zero_position_is_neither_long_nor_short():
    """A one-pixel bar on either side would claim a direction the input
    does not have."""
    from riskdesk.report import _net_by_asset_svg

    document = _net_by_asset_svg(exposure_payload(), "USD")
    assert document.count('class="bar flat"') == 1
    assert document.count('class="bar long"') == 1
    assert document.count('class="bar short"') == 1


@pytest.mark.unit
def test_both_exposure_charts_name_the_base_currency():
    from riskdesk.report import _gross_share_svg, _net_by_asset_svg

    exposure = exposure_payload()
    ladder = _net_by_asset_svg(exposure, "USD")
    shares = _gross_share_svg(exposure, "USD")
    assert "net market value, signed, in USD" in ladder
    assert "share of gross exposure, 800.00 USD in total" in shares
    assert "75.0%" in shares


@pytest.mark.unit
def test_an_exposure_result_in_another_currency_is_refused():
    other = exposure_request()
    other["currency"] = "EUR"
    with pytest.raises(ValueError, match="one currency"):
        report_payload(stress_test(stress_request()), None, None,
                       portfolio_exposure(other))


@pytest.mark.unit
def test_an_absent_exposure_is_stated_rather_than_read_as_zero():
    document = render_html(report_payload(stress_test(stress_request())))
    assert "No exposure result was supplied" in document
    assert "not because the exposure is zero" in document
    assert 'class="bar long"' not in document


@pytest.mark.unit
def test_the_page_prints_the_exposure_sign_convention_and_flag():
    document, _ = build_report(stress_request(), None, exposure_request())
    assert "a negative net value is a short position" in document
    assert ">not degraded<" in document
    assert "Exposure input SHA-256" in document


@pytest.mark.unit
def test_asset_names_cannot_inject_markup_into_the_exposure_charts():
    request = exposure_request()
    request["positions"][0]["asset"] = "<script>alert(1)</script>"
    document, _ = build_report(stress_request(), None, request)
    assert "<script>alert(1)</script>" not in document
    assert "&lt;script&gt;" in document


def run_report(output, *extra):
    return subprocess.run(
        [sys.executable, "-m", "riskdesk.cli", "report",
         "--input", str(ROOT / "examples" / "energy_stress.json"),
         "--output", str(output), *extra],
        capture_output=True, text=True, cwd=str(ROOT),
        env=dict(PATH="/usr/bin:/bin", PYTHONPATH=str(ROOT / "src")))


@pytest.mark.integration
def test_the_cli_writes_a_page_with_all_three_panels(tmp_path):
    output = tmp_path / "nested" / "report.html"
    finished = run_report(
        output,
        "--tail", str(ROOT / "examples" / "energy_tail.json"),
        "--exposure", str(ROOT / "examples" / "energy_book.json"))
    assert finished.returncode == 0, finished.stdout + finished.stderr
    summary = json.loads(finished.stdout)
    assert summary["tail_included"] is True
    assert summary["exposure_included"] is True
    assert summary["degraded"] is False
    assert summary["scenarios"] == ["european_gas_supply_dislocation_shape",
                                    "global_energy_demand_collapse_shape"]
    document = output.read_text(encoding="utf-8")
    assert document.startswith("<!DOCTYPE html>")
    assert "european_gas_supply_dislocation_shape" in document
    assert "Expected Shortfall" in document
    assert "<svg" in document


@pytest.mark.integration
def test_the_written_file_contains_both_exposure_charts(tmp_path):
    output = tmp_path / "report.html"
    finished = run_report(
        output, "--exposure", str(ROOT / "examples" / "energy_book.json"))
    assert finished.returncode == 0, finished.stdout + finished.stderr
    document = output.read_text(encoding="utf-8")
    assert "Signed net exposure by asset" in document
    assert "Share of gross exposure by asset" in document
    assert document.count("<svg") == 4          # two scenarios, two exposure
    assert 'class="bar long"' in document
    assert 'class="bar short"' in document
    assert 'class="bar share"' in document
    assert "14,100,000.00 USD" in document      # gross exposure
    assert "6,000,000.00 USD" in document       # net exposure
    assert "1.175x" in document                 # gross leverage
    assert "29.8%" in document                  # largest gross share
    assert "-2,600,000.00 USD" in document      # the short leg, still signed
    assert "http://" not in document and "https://" not in document


@pytest.mark.integration
def test_an_absent_exposure_input_still_writes_a_valid_page(tmp_path):
    output = tmp_path / "report.html"
    finished = run_report(
        output, "--tail", str(ROOT / "examples" / "energy_tail.json"))
    assert finished.returncode == 0, finished.stdout + finished.stderr
    assert json.loads(finished.stdout)["exposure_included"] is False
    document = output.read_text(encoding="utf-8")
    assert document.startswith("<!DOCTYPE html>")
    assert document.rstrip().endswith("</html>")
    assert "No exposure result was supplied" in document
    assert "not because the exposure is zero" in document
    assert 'class="bar long"' not in document
    assert "Expected Shortfall" in document


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
