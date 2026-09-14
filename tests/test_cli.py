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


@pytest.mark.parametrize("command,example,key", [
    ("tail", "tail.json", "var"),
    ("exposure", "portfolio.json", "gross_exposure"),
    ("stress", "stress.json", "scenarios"),
])
def test_each_command_prints_its_envelope_and_exits_zero(command, example,
                                                         key, capsys):
    assert cli.main([command, "--input", str(EXAMPLES / example)]) == 0
    result = read(capsys)
    assert key in result
    assert result["degraded"] in (True, False)
    assert "input_sha256" in result


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
