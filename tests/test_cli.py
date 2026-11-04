"""The command layer, called in process.

main() takes its argv, so the dispatch, the failure envelope and the exit
codes can be checked without starting a process. The subprocess round trip
stays in the integration tests, where it belongs; running it here would
make the fast suite slow and would not check anything more.
"""
import io
import json
from pathlib import Path

import pytest

from riskdesk import cli, summaries

EXAMPLES = Path(__file__).resolve().parent.parent / "examples"

pytestmark = pytest.mark.unit


def read(capsys):
    return json.loads(capsys.readouterr().out)


CASES = [
    ("tail", "tail.json", "var"),
    ("exposure", "portfolio.json", "gross_exposure"),
    ("stress", "stress.json", "scenarios"),
    ("tail-models", "tail.json", "methods"),
    ("backtest", "var_backtest_energy.json", "exceptions"),
    ("derivatives-greeks", "derivatives_book.json", "by_underlying"),
    ("derivatives-grid", "derivatives_grid.json", "cells"),
    ("derivatives-historical", "derivatives_historical.json", "tail"),
    ("covariance", "decomposition_covariance.json", "covariance"),
    ("var-attribution", "decomposition_parametric.json", "var"),
    ("es-attribution", "decomposition_historical.json", "expected_shortfall"),
    ("factors", "decomposition_factor.json", "systematic_share"),
    ("limits", "limits_check.json", "overall_status"),
    ("what-if", "limits_what_if.json", "limits_after"),
    ("liquidity", "liquidity_book.json", "liquidity_adjusted_var"),
    ("replay", "stress_replay.json", "shocks"),
    ("reverse-stress", "stress_reverse.json", "mahalanobis_distance"),
    ("scale-scenario", "stress_scale.json", "multiple"),
    ("saccr", "counterparty_saccr.json", "ead"),
    ("exposure-profile", "counterparty_profile.json", "effective_epe"),
    ("credit-asrf", "credit_asrf.json", "credit_var"),
    ("credit-copula", "credit_copula.json", "credit_var"),
    ("frtb-imcc", "frtb_imcc.json", "imcc"),
    ("frtb-capital", "frtb_ima_capital.json", "aggregate_capital"),
    ("frtb-pla", "frtb_pla.json", "zone"),
    ("frtb-backtest", "frtb_backtest.json", "passes"),
    ("frtb-sbm-fx", "frtb_sbm_fx.json", "capital"),
]


@pytest.mark.parametrize("command,example,key", CASES)
def test_each_command_prints_its_envelope_and_exits_zero(command, example,
                                                         key, capsys):
    assert cli.main([command, "--input", str(EXAMPLES / example)]) == 0
    result = read(capsys)
    assert key in result
    assert result["degraded"] in (True, False)
    assert "input_sha256" in result


def test_every_input_command_has_a_case():
    """A command added to HANDLERS without a shipped example run here would
    be the one nobody has seen work."""
    assert set(cli.HANDLERS) == {command for command, _, _ in CASES}


def test_the_scenario_library_command_takes_no_input(capsys):
    assert cli.main(["scenarios"]) == 0
    library = read(capsys)
    assert library["windows"]
    assert all(window["sources"] for window in library["windows"])


def test_a_failure_is_a_json_envelope_and_a_nonzero_code(tmp_path, capsys):
    bad = tmp_path / "bad.json"
    bad.write_text("{}")
    assert cli.main(["tail", "--input", str(bad)]) == 1
    assert read(capsys)["error"] == "ValidationError"


def test_an_unreadable_file_is_reported_rather_than_traced(tmp_path, capsys):
    assert cli.main(["tail", "--input", str(tmp_path / "absent.json")]) == 1
    assert read(capsys)["error"] == "FileNotFoundError"


def test_report_writes_the_page_and_reports_what_reached_it(tmp_path, capsys):
    output = tmp_path / "deep" / "page.html"
    assert cli.main(["report",
                     "--input", str(EXAMPLES / "energy_stress.json"),
                     "--tail", str(EXAMPLES / "energy_tail.json"),
                     "--output", str(output)]) == 0
    summary = read(capsys)
    assert summary["tail_included"] is True
    assert summary["bytes"] == len(output.read_text(encoding="utf-8")
                                   .encode("utf-8"))


def test_report_takes_an_exposure_input_and_draws_it(tmp_path, capsys):
    output = tmp_path / "page.html"
    assert cli.main(["report",
                     "--input", str(EXAMPLES / "energy_stress.json"),
                     "--exposure", str(EXAMPLES / "energy_book.json"),
                     "--output", str(output)]) == 0
    summary = read(capsys)
    assert summary["exposure_included"] is True
    assert summary["tail_included"] is False
    document = output.read_text(encoding="utf-8")
    assert 'class="bar long"' in document
    assert 'class="bar short"' in document
    assert 'class="bar share"' in document


def test_report_without_an_exposure_says_so_rather_than_inventing_one(
        tmp_path, capsys):
    output = tmp_path / "page.html"
    assert cli.main(["report", "--input", str(EXAMPLES / "stress.json"),
                     "--output", str(output)]) == 0
    assert read(capsys)["exposure_included"] is False
    assert "No exposure result was supplied" in output.read_text(
        encoding="utf-8")


def test_report_without_a_tail_says_so_rather_than_inventing_one(tmp_path,
                                                                 capsys):
    output = tmp_path / "page.html"
    assert cli.main(["report", "--input", str(EXAMPLES / "stress.json"),
                     "--output", str(output)]) == 0
    assert read(capsys)["tail_included"] is False
    assert "No tail result was supplied" in output.read_text(encoding="utf-8")


def test_xva_passes_its_four_arguments_through_unchanged(monkeypatch, capsys):
    seen = {}

    def fake(project, config, output, data_mode):
        seen.update(project=project, config=config, output=output,
                    data_mode=data_mode)
        return {"backend": "stub", "errors": []}

    monkeypatch.setattr(cli, "run_ore", fake)
    assert cli.main(["xva", "--project", "P", "--config", "Input/ore.xml",
                     "--output", "O", "--data-mode", "user-licensed"]) == 0
    assert seen == {"project": "P", "config": "Input/ore.xml", "output": "O",
                    "data_mode": "user-licensed"}
    assert read(capsys)["backend"] == "stub"


def test_an_ore_failure_does_not_become_a_zero_exit(monkeypatch, capsys):
    def fake(*args):
        raise RuntimeError("ORE reported errors")

    monkeypatch.setattr(cli, "run_ore", fake)
    assert cli.main(["xva", "--project", "P", "--config", "c", "--output",
                     "O", "--data-mode", "synthetic"]) == 1
    assert read(capsys)["error"] == "RuntimeError"


def test_a_missing_subcommand_is_refused():
    with pytest.raises(SystemExit):
        cli.main([])


def test_the_summariser_reads_stdin_and_prints_lines(monkeypatch, capsys):
    from riskdesk.analytics import tail_risk

    result = tail_risk(json.loads((EXAMPLES / "tail.json")
                                  .read_text(encoding="utf-8")))
    monkeypatch.setattr("sys.stdin", io.StringIO(json.dumps(result)))
    assert summaries.main(["tail"]) == 0
    out = capsys.readouterr().out
    assert "loss is positive" in out
    assert "DEGRADED:" in out


def test_the_summariser_refuses_an_error_envelope_with_a_nonzero_code(
        monkeypatch, capsys):
    monkeypatch.setattr("sys.stdin", io.StringIO(
        json.dumps({"error": "ValidationError", "message": "no"})))
    assert summaries.main(["stress"]) == 1
    assert "could not summarise" in capsys.readouterr().out


def test_an_unknown_result_kind_is_refused():
    with pytest.raises(ValueError):
        summaries.summarise("greeks", {})


def test_the_server_tools_call_the_same_functions_as_the_cli():
    """The README says an agent and a person get the same numbers. That is
    only true while both entry points call one implementation."""
    from riskdesk import server
    from riskdesk.analytics import portfolio_exposure, stress_test, tail_risk

    request = json.loads((EXAMPLES / "tail.json").read_text(encoding="utf-8"))
    assert server.risk_tail(request) == tail_risk(request)
    book = json.loads((EXAMPLES / "energy_book.json")
                      .read_text(encoding="utf-8"))
    assert server.risk_exposure(book) == portfolio_exposure(book)
    stress = json.loads((EXAMPLES / "energy_stress.json")
                        .read_text(encoding="utf-8"))
    assert server.risk_stress(stress) == stress_test(stress)


# MCP tool name -> CLI command. Both call one function.
TOOLS = {"risk_tail": "tail", "risk_exposure": "exposure", "risk_stress": "stress",
         "risk_tail_models": "tail-models", "risk_backtest": "backtest",
         "risk_derivatives_greeks": "derivatives-greeks", "risk_derivatives_grid": "derivatives-grid",
         "risk_derivatives_historical": "derivatives-historical", "risk_covariance": "covariance",
         "risk_var_attribution": "var-attribution", "risk_es_attribution": "es-attribution",
         "risk_factor_exposure": "factors", "risk_limits": "limits", "risk_what_if": "what-if",
         "risk_liquidity": "liquidity", "risk_stress_replay": "replay",
         "risk_reverse_stress": "reverse-stress", "risk_scenario_scale": "scale-scenario",
         "risk_saccr": "saccr", "risk_exposure_profile": "exposure-profile",
         "risk_credit_asrf": "credit-asrf", "risk_credit_copula": "credit-copula",
         "risk_frtb_imcc": "frtb-imcc", "risk_frtb_ima_capital": "frtb-capital",
         "risk_frtb_pla": "frtb-pla", "risk_frtb_backtest": "frtb-backtest",
         "risk_frtb_sbm_fx": "frtb-sbm-fx"}


@pytest.mark.parametrize("tool,command", sorted(TOOLS.items()))
def test_each_tool_returns_what_its_command_returns(tool, command):
    from riskdesk import server
    example = {c: e for c, e, _ in CASES}[command]
    request = json.loads((EXAMPLES / example).read_text(encoding="utf-8"))
    assert getattr(server, tool)(request) == cli.HANDLERS[command](request)


def test_the_scenario_library_tool_is_the_command():
    from riskdesk import server
    assert server.risk_scenario_library() == cli.scenarios.scenario_library()


def skill_script(skill):
    import importlib.util
    path = EXAMPLES.parent / "plugins/risk-desk/skills" / skill / "scripts/check_artifact.py"
    spec = importlib.util.spec_from_file_location(skill.replace("-", "_") + "_check", path)
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    return module


def test_the_import_validator_accepts_every_example_and_reports_every_error(tmp_path, capsys):
    check = skill_script("risk-data-import")
    models = check.request_models()
    assert set(models) == set(TOOLS)                   # every tool that takes a request, and no other
    for tool, command in TOOLS.items():
        example = json.loads((EXAMPLES / {c: e for c, e, _ in CASES}[command]).read_text(encoding="utf-8"))
        assert check.errors(models[tool], example) == [], tool
    book = json.loads((EXAMPLES / "portfolio.json").read_text(encoding="utf-8"))
    book.update(currency="usd", as_of="04/11/2026", book="x")
    book["positions"][0]["market_value"] = "1,250,000"
    path = tmp_path / "request.json"; path.write_text(json.dumps(book))
    assert check.main("risk_exposure", str(path)) == 1
    out = capsys.readouterr().out.splitlines()
    assert out[0] == "FAIL risk_exposure: 4 error(s) against PortfolioRequest"
    assert sorted(line.split(":")[0].strip() for line in out[1:]) == [
        "as_of", "book", "currency", "positions.0.market_value"]
    book = json.loads((EXAMPLES / "portfolio.json").read_text(encoding="utf-8"))
    book["positions"][1]["id"] = book["positions"][0]["id"]   # a cross-field rule
    [problem] = check.errors(models["risk_exposure"], book)
    assert problem.startswith("request: Value error, position ids must be unique (found {")
    assert check.main("risk_xva", str(path)) == 2
