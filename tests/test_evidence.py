"""The documentation check, and proof that it can fail.

A check that has never been seen to fail is indistinguishable from a check
that cannot. So this file does both halves: it runs the real check over the
real documents, and it then edits one digit in a copy of them and requires
the same check to reject it.
"""
import importlib.util
import json
from pathlib import Path
import shutil

import pytest

ROOT = Path(__file__).resolve().parent.parent

pytestmark = pytest.mark.validation


def load_evidence_module():
    spec = importlib.util.spec_from_file_location(
        "riskdesk_evidence", ROOT / "scripts" / "evidence.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def evidence():
    return load_evidence_module()


def test_the_recorded_file_exists_and_names_its_provenance(evidence):
    payload = json.loads(evidence.EVIDENCE.read_text(encoding="utf-8"))
    figures = payload["figures"]
    assert figures, "no figures recorded"
    for key, entry in figures.items():
        assert entry["kind"] in ("measured", "pinned"), key
        assert entry["documents"], key
        if entry["kind"] == "pinned":
            assert entry["observed"], key
            assert entry["provenance"], key


def test_the_documents_still_match_the_recorded_figures(evidence, capsys):
    assert evidence.check() == 0, capsys.readouterr().out


def test_the_check_rejects_a_document_that_drifted(tmp_path, evidence,
                                                   monkeypatch):
    """Change one digit of one quoted number and the check must fail. This
    is the whole point of the file: a build that lets the prose drift is a
    build that certifies nothing."""
    for name in ("README.md",):
        shutil.copy2(ROOT / name, tmp_path / name)
    shutil.copytree(ROOT / "docs", tmp_path / "docs")
    monkeypatch.setattr(evidence, "ROOT", tmp_path)
    monkeypatch.setattr(evidence, "EVIDENCE", tmp_path / "docs"
                        / "evidence.json")
    assert evidence.check() == 0

    figures = json.loads((tmp_path / "docs" / "evidence.json")
                         .read_text(encoding="utf-8"))["figures"]
    sentence = figures["ore_cva"]["documents"]["docs/ORE.md"]
    target = tmp_path / "docs" / "ORE.md"
    drifted = sentence.replace("42600", "42601")
    assert drifted != sentence
    target.write_text(target.read_text(encoding="utf-8")
                      .replace(sentence, drifted), encoding="utf-8")
    assert evidence.check() == 1


def test_a_missing_document_is_a_failure_not_a_pass(tmp_path, evidence,
                                                    monkeypatch):
    shutil.copy2(ROOT / "README.md", tmp_path / "README.md")
    shutil.copytree(ROOT / "docs", tmp_path / "docs")
    monkeypatch.setattr(evidence, "ROOT", tmp_path)
    monkeypatch.setattr(evidence, "EVIDENCE", tmp_path / "docs"
                        / "evidence.json")
    (tmp_path / "docs" / "ORE.md").unlink()
    assert evidence.check() == 1


def test_a_stray_dot_file_is_not_counted_as_an_upstream_notice(evidence,
                                                              tmp_path,
                                                              monkeypatch):
    """A .DS_Store in notices/ was counted as a notice while this was being
    written, which would have put 80 into the README for 79 notices."""
    notices = tmp_path / "notices"
    (notices / "somepkg").mkdir(parents=True)
    (notices / "somepkg" / "LICENSE").write_text("x")
    (notices / ".DS_Store").write_text("x")
    (notices / ".hidden").mkdir()
    monkeypatch.setattr(evidence, "ROOT", tmp_path)
    assert evidence.measure_notice_files() == 1
    assert evidence.measure_notice_distributions() == 1


def test_every_measured_figure_still_matches_the_repository(evidence):
    """The recorded value is a claim about this checkout. Re-measuring the
    cheap ones here means a stale evidence file fails the suite rather than
    quietly certifying itself."""
    figures = json.loads(evidence.EVIDENCE.read_text(encoding="utf-8"))[
        "figures"]
    for key in ("skills", "mcp_tools", "notice_files",
                "notice_distributions", "examples"):
        assert figures[key]["value"] == evidence.MEASURES[key](), key
