"""Tool results as documents: degraded first, provenance stated, nothing invented."""
import json
from pathlib import Path

import pytest

from riskdesk.analytics import portfolio_exposure, tail_risk
from riskdesk_agent.artifacts import context_for, documents, summarise

ROOT = Path(__file__).resolve().parent.parent
pytestmark = pytest.mark.unit


def record(tool, handler, name):
    request = json.loads((ROOT / "examples" / name).read_text(encoding="utf-8"))
    return {"tool": tool, "arguments": {"request": request}, "result": handler(request)}


def test_a_degraded_result_says_so_before_any_figure():
    text = summarise(record("risk_tail", tail_risk, "tail.json"))
    first, rest = text.split("\n", 1)
    assert first.startswith("DEGRADED: Fewer than 20 observations")
    assert '"var": 50.0' in rest


def test_currency_horizon_as_of_and_data_mode_are_stated():
    text = summarise(record("risk_tail", tail_risk, "tail.json"))
    for phrase in ("currency USD", "horizon days 1", "as of 2026-09-12", "data mode synthetic"):
        assert phrase in text, phrase
    assert "not stated" not in text


def test_a_result_without_a_horizon_says_it_is_not_stated():
    text = summarise(record("risk_exposure", portfolio_exposure, "portfolio.json"))
    assert "not stated: horizon days" in text
    assert text.startswith("degraded: ")


def test_a_result_that_does_not_state_degraded_is_not_called_clean():
    text = summarise({"tool": "risk_scenario_library", "result": {"windows": []}})
    assert text.startswith("degraded: not stated by risk_scenario_library")


def test_a_missing_result_quotes_nothing():
    assert "nothing is quoted" in summarise({"tool": "risk_tail", "result": None})


def test_an_empty_run_says_nothing_was_supplied():
    assert context_for([]).startswith("No tool result is available")


def test_documents_carry_the_degraded_flag_and_provenance():
    records = [record("risk_tail", tail_risk, "tail.json"),
               record("risk_exposure", portfolio_exposure, "portfolio.json")]
    docs = documents(records)
    assert [d.metadata["tool"] for d in docs] == ["risk_tail", "risk_exposure"]
    assert docs[0].metadata["degraded"] is True
    assert docs[0].metadata["currency"] == "USD"
    assert docs[0].metadata["input_sha256"] == records[0]["result"]["input_sha256"]
    assert context_for(records) == "\n\n".join(d.page_content for d in docs)
