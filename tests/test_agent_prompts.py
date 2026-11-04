"""The answer prompt carries the Risk Desk reporting rules, verbatim and whole."""
import pytest

from riskdesk.server import CONVENTIONS
from riskdesk_agent import prompts
from riskdesk_agent.prompts import REPORTING_RULES, build_answer_prompt, build_router_prompt

pytestmark = pytest.mark.unit


def system_text(prompt, **values):
    values.setdefault("context", "a tool result")
    values.setdefault("question", "what is the VaR")
    return prompt.format_messages(**values)[0].content


def test_every_server_convention_reaches_the_model_verbatim():
    """Catches the prompt and risk_desk_status drifting apart."""
    text = system_text(build_answer_prompt())
    assert REPORTING_RULES in text
    for rule in CONVENTIONS:
        assert rule in text, rule


@pytest.mark.parametrize("phrase", [
    "Report degraded and degraded_reason before any figure.",
    "Loss is positive",
    "State the currency, the horizon, the as-of date and the data mode",
    "Never invent a market value",
    "not investment advice",
    "Historical loss forecasts are not risk-neutral valuation",
    "Every number you write must\nappear in a tool result.",
])
def test_each_required_rule_is_in_the_prompt(phrase):
    assert phrase in system_text(build_answer_prompt())


def test_context_and_question_reach_the_human_message():
    human = build_answer_prompt().format_messages(
        context="risk_tail result: currency USD", question="where is ES")[-1].content
    assert "risk_tail result: currency USD" in human and "where is ES" in human
    assert set(build_answer_prompt().input_variables) == {"context", "question"}


def test_extra_rules_are_appended_after_the_base_rules():
    text = system_text(build_answer_prompt(extra_rules="Never name a counterparty {id}."))
    assert REPORTING_RULES in text
    assert text.index("Never name a counterparty {id}.") > text.index("Never recommend")
    assert "Additional rules" not in system_text(build_answer_prompt())


def test_building_a_prompt_does_not_mutate_the_shared_rules():
    before = REPORTING_RULES
    build_answer_prompt(extra_rules="House rule.")
    assert prompts.REPORTING_RULES == before


def test_the_router_refuses_advice_and_invented_inputs():
    text = system_text(build_router_prompt())
    assert "Nothing here answers a question about what someone should do." in text
    assert "Never invent a market value" in text
    assert build_router_prompt().input_variables == ["question"]
