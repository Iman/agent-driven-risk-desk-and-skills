"""The answer graph with a scripted chat model: no network, no API key.

The model is a stand-in that returns AIMessages in order and records what
it was bound to and shown. The tools are the real registry, run in process
on the shipped examples, so a grounded answer is grounded in a real result.
"""
import contextlib
import importlib
import json
from pathlib import Path
import sys

import pytest
from langchain_core.messages import AIMessage

from riskdesk_agent.graph import DEFAULT_BUDGET, ask, build_answer_graph, ungrounded_numbers
from riskdesk_agent.prompts import REPORTING_RULES
from riskdesk_agent.tools import read_only_names

ROOT = Path(__file__).resolve().parent.parent
pytestmark = pytest.mark.unit

TAIL = json.loads((ROOT / "examples" / "tail.json").read_text(encoding="utf-8"))
QUESTION = "What are the VaR and ES of this book? " + json.dumps(TAIL)


class ScriptedModel:
    """Returns the scripted replies in order; records bindings and prompts."""

    def __init__(self, *replies):
        self.replies, self.bound, self.prompts = list(replies), None, []

    def bind_tools(self, tools):
        self.bound = [tool.name for tool in tools]
        return self

    def invoke(self, messages):
        self.prompts.append(messages)
        return self.replies.pop(0)


def call(name, args):
    return AIMessage(content="", tool_calls=[{"name": name, "args": args, "id": name}])


GROUNDED = ("The result is DEGRADED: fewer than 20 observations of tail probability "
            "mass. As of 2026-09-12, USD, synthetic data, 1-day horizon: VaR 50.00 "
            "and ES 83.33 at 62.5% confidence, a loss of 50.")


# ----------------------------------------------------------------- routing

def test_the_router_picks_a_tool_and_the_real_tool_runs():
    model = ScriptedModel(call("risk_tail", {"request": TAIL}), AIMessage(content=GROUNDED))
    final = ask(QUESTION, model=model)
    assert final["outcome"] == "answered", final
    assert [r["tool"] for r in final["results"]] == ["risk_tail"]
    assert final["results"][0]["result"]["var"] == 50.0
    assert "route: chose risk_tail" in final["log"]
    assert "act: ran risk_tail (degraded)" in final["log"]


def test_the_router_is_bound_to_the_read_only_registry():
    """Catches the router being handed the ORE writer, or a hand-picked subset."""
    model = ScriptedModel(AIMessage(content="No tool fits."))
    ask("Should I buy crude?", model=model)
    assert model.bound == read_only_names()
    assert "risk_xva" not in model.bound


def test_a_router_that_calls_no_tool_declines_without_a_second_model_call():
    model = ScriptedModel(AIMessage(content="That is a question about what to do."))
    final = ask("Should I hedge?", model=model)
    assert final["outcome"] == "declined"
    assert len(model.prompts) == 1
    assert "no result to report" in final["answer"]


def test_a_router_that_invents_an_input_is_refused_before_any_tool_runs():
    """Catches a model filling in P&L the question never supplied."""
    invented = dict(TAIL, pnl=[-120.5, 30.0, 12.0, -7.0])
    model = ScriptedModel(call("risk_tail", {"request": invented}))
    final = ask(QUESTION, model=model)
    assert final["outcome"] == "failed"
    assert final.get("results") in (None, [])
    assert "-120.5" in final["failures"][0] and "the question does not contain" in final["failures"][0]


# --------------------------------------------------------------- grounding

def test_a_grounded_answer_is_returned_and_given_the_rules_and_results():
    model = ScriptedModel(call("risk_tail", {"request": TAIL}), AIMessage(content=GROUNDED))
    final = ask(QUESTION, model=model)
    assert final["answer"] == GROUNDED and final["ungrounded"] == []
    system, human = model.prompts[1][0].content, model.prompts[1][-1].content
    assert REPORTING_RULES in system
    assert "DEGRADED: Fewer than 20 observations" in human and '"var": 50.0' in human


def test_an_answer_with_an_invented_number_is_withheld():
    """Catches a model's number reaching the reader without a tool behind it."""
    model = ScriptedModel(call("risk_tail", {"request": TAIL}),
                          AIMessage(content="VaR is 51.2 USD and ES 83.33."))
    final = ask(QUESTION, model=model)
    assert final["outcome"] == "ungrounded"
    assert final["ungrounded"] == ["51.2"]
    assert "VaR is 51.2" not in final["answer"]
    assert final["answer"].startswith("The model's answer was withheld")
    assert "DEGRADED: Fewer than 20 observations" in final["answer"]


@pytest.mark.parametrize("text, missing", [
    ("VaR 50", []), ("ES 83.3", []), ("ES 83.33", []), ("62.5% confidence", []),
    ("as of 2026-09-12", []), ("a gain of 50", []),
    ("VaR -50", ["-50"]), ("ES 84", ["84"]), ("ES 83.34", ["83.34"]),
    ("1,000.00 of value", []), ("7 days", ["7"]),
])
def test_the_grounding_rule(text, missing):
    result = {"var": 50.0, "expected_shortfall": 83.33333333333334, "confidence": 0.625,
              "as_of": "2026-09-12", "portfolio_value": 1000.0, "horizon_days": 1}
    assert ungrounded_numbers(text, result) == missing


def test_a_negative_result_must_be_quoted_with_its_sign_or_as_a_gain():
    assert ungrounded_numbers("VaR -12.5", {"var": -12.5}) == []
    assert ungrounded_numbers("a gain of 12.5", {"var": -12.5}) == []


# ----------------------------------------------------------------- failures

def test_a_failing_tool_names_itself_and_the_error():
    bad = dict(TAIL)
    del bad["currency"]
    final = ask("x", tool_calls=[{"name": "risk_tail", "args": {"request": bad}}])
    assert final["outcome"] == "failed"
    assert final["failures"][0].startswith("risk_tail failed: ToolError")


def test_an_unknown_tool_is_a_failure_not_a_skip():
    final = ask("x", tool_calls=[{"name": "risk_xva", "args": {}}])
    assert final["outcome"] == "failed"
    assert final["failures"] == ["no tool named risk_xva"]


def test_calls_over_the_budget_run_nothing():
    calls = [{"name": "risk_scenario_library", "args": {}}] * 2
    final = ask("x", tool_calls=calls, budget=1)
    assert final["outcome"] == "failed"
    assert final.get("results") in (None, [])
    assert "exceed the budget of 1" in final["failures"][0]
    assert DEFAULT_BUDGET >= 1


def test_routing_without_a_model_or_calls_fails_plainly():
    final = ask("What is my VaR?")
    assert final["outcome"] == "failed"
    assert "no model to route" in final["answer"]


def test_without_a_model_the_answer_is_the_tool_results():
    final = ask("x", tool_calls=[{"name": "risk_tail", "args": {"request": TAIL}}])
    assert final["outcome"] == "answered"
    assert final["answer"].startswith("DEGRADED: Fewer than 20 observations")


def test_the_graph_has_three_nodes_and_one_conditional_branch():
    edges = build_answer_graph(tools=[]).get_graph().edges
    assert {(e.source, e.target) for e in edges} == {
        ("__start__", "route"), ("route", "act"), ("route", "answer"),
        ("act", "answer"), ("answer", "__end__")}


# ------------------------------------------------- langgraph is an extra

@contextlib.contextmanager
def langgraph_absent():
    saved = {n: m for n, m in sys.modules.items()
             if n.split(".")[0] in ("langgraph", "riskdesk_agent")}
    for name in saved:
        del sys.modules[name]
    sys.modules["langgraph"] = None
    try:
        yield
    finally:
        for name in [n for n in sys.modules if n.split(".")[0] in ("langgraph", "riskdesk_agent")]:
            del sys.modules[name]
        sys.modules.update(saved)


def test_the_package_imports_and_works_without_langgraph():
    with langgraph_absent():
        package = importlib.import_module("riskdesk_agent")
        assert package.__version__ == "0.2.0"
        assert "riskdesk_agent.graph" not in sys.modules
        assert package.desk_tools(include=["risk_tail"])[0].name == "risk_tail"
        with pytest.raises(ImportError) as caught:
            package.build_answer_graph()
        assert "langgraph" in str(caught.value)
    assert importlib.import_module("riskdesk_agent.graph") is not None
