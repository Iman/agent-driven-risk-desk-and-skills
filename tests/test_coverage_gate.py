"""The coverage gate, checked the only way a gate can be: by failing it.

The gate cannot run the coverage tool from inside the suite it measures,
so what is pinned here is its judgement: which reports it passes, which it
refuses, and that it refuses rather than ignores a production file that
never appeared in the run. A report missing a file looks like nothing, and
an aggregate computed over what remains would pass by leaving it out.

The measured figure itself is produced by the documented command and
recorded, with its date, in docs/IMPLEMENTATION.md.
"""
import importlib.util
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent

pytestmark = pytest.mark.validation


@pytest.fixture(scope="module")
def gate():
    spec = importlib.util.spec_from_file_location(
        "riskdesk_coverage_gate", ROOT / "scripts" / "check_unit_coverage.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def report(*files):
    return {"files": {name: {"summary": {"covered_lines": covered,
                                         "num_statements": total}}
                      for name, covered, total in files}}


def test_a_package_above_the_floor_passes(gate):
    _, total = gate.assess(report(("src/riskdesk/a.py", 90, 100)))
    assert total["passed"] is True
    assert total["percent"] == pytest.approx(90.0)


def test_a_package_below_the_floor_fails(gate):
    _, total = gate.assess(report(("src/riskdesk/a.py", 79, 100)))
    assert total["passed"] is False


def test_exactly_the_floor_passes(gate):
    """80 percent means 80 is enough. A gate that rejected its own
    documented threshold would be a different gate."""
    _, total = gate.assess(report(("src/riskdesk/a.py", 80, 100)))
    assert total["passed"] is True


def test_one_well_covered_file_cannot_hide_an_empty_one(gate):
    rows, total = gate.assess(report(("src/riskdesk/a.py", 100, 100),
                                     ("src/riskdesk/b.py", 0, 100)))
    assert total["passed"] is False
    assert [row["name"] for row in rows] == ["src/riskdesk/a.py",
                                             "src/riskdesk/b.py"]


def test_files_outside_the_package_are_not_counted(gate):
    _, total = gate.assess(report(("src/riskdesk/a.py", 40, 100),
                                  ("tests/test_a.py", 100, 100)))
    assert total["total"] == 100
    assert total["passed"] is False


@pytest.mark.parametrize("payload", [
    {"files": {}},
    {"files": {"tests/test_a.py": {"summary": {"covered_lines": 1,
                                               "num_statements": 1}}}},
    {"files": {"src/riskdesk/a.py": {"summary": {"covered_lines": 5,
                                                 "num_statements": 1}}}},
    {"files": {"src/riskdesk/a.py": {"summary": {"covered_lines": "9",
                                                 "num_statements": 10}}}},
])
def test_an_unusable_report_is_refused_not_averaged(gate, payload):
    with pytest.raises(ValueError):
        gate.assess(payload)


def test_a_production_file_absent_from_the_run_fails_the_gate(gate, tmp_path,
                                                              capsys):
    present = sorted(p.relative_to(ROOT).as_posix()
                     for p in (ROOT / gate.PACKAGE).rglob("*.py"))
    assert len(present) > 1
    path = tmp_path / "unit.json"
    path.write_text(json.dumps(report(*[(name, 100, 100)
                                        for name in present[1:]])))
    assert gate.main([str(path)]) == 1
    printed = capsys.readouterr().out
    assert "missing from coverage" in printed
    assert present[0] in printed


def test_a_complete_report_at_the_floor_passes_the_command(gate, tmp_path,
                                                           capsys):
    present = sorted(p.relative_to(ROOT).as_posix()
                     for p in (ROOT / gate.PACKAGE).rglob("*.py"))
    path = tmp_path / "unit.json"
    path.write_text(json.dumps(report(*[(name, 80, 100)
                                        for name in present])))
    assert gate.main([str(path)]) == 0
    assert "PASS, minimum 80%" in capsys.readouterr().out


def test_a_missing_report_file_is_a_failure_not_a_pass(gate, tmp_path,
                                                       capsys):
    assert gate.main([str(tmp_path / "absent.json")]) == 1
    assert "Coverage gate failed" in capsys.readouterr().out
