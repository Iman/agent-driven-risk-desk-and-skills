"""A question answered through Risk Desk tools, as a state graph.

route -> act -> answer, with three checks a model cannot talk its way past:

- route: the model, bound to the registry's read-only tools, picks tool
  calls. A call whose arguments hold a number the question does not contain
  is refused before it runs, because that number was invented.
- act: runs the calls through the registry, up to a budget. A call that
  fails, or a name the registry does not have, ends the run as failed.
- answer: the model writes from the tool results under the reporting rules,
  and every number it writes must appear in a tool result. If one does not,
  its text is withheld and the tool results are returned instead.

Outcomes: answered, declined (no tool was called), failed, ungrounded.
Requires langgraph, which is an optional extra of this package.
"""

import json
import operator
import re
from typing import Annotated, TypedDict

from riskdesk_agent.artifacts import context_for

DEFAULT_BUDGET = 8

# A number not glued to a word or a decimal point, so "MAR33" and the "11" in
# "2026-11-04" are read the same way in an answer and in a tool result.
_NUMBER = re.compile(r"(?<![\w.])-?\d[\d,]*(?:\.\d+)?")


class AnswerState(TypedDict, total=False):
    question: str
    budget: int
    tool_calls: list
    results: list
    log: Annotated[list, operator.add]
    failures: Annotated[list, operator.add]
    ungrounded: list
    answer: str
    outcome: str


def _source_numbers(value, out):
    """Every number in a JSON value: numeric leaves and numbers inside strings."""
    if isinstance(value, bool):
        return out
    if isinstance(value, (int, float)):
        out.add(float(value))
    elif isinstance(value, str):
        out.update(float(token.replace(",", "")) for token in _NUMBER.findall(value))
    elif isinstance(value, dict):
        for key, item in value.items():
            _source_numbers(key, out)
            _source_numbers(item, out)
    elif isinstance(value, (list, tuple)):
        for item in value:
            _source_numbers(item, out)
    return out


def ungrounded_numbers(text, source):
    """Numbers in text that no number in source accounts for.

    A token is grounded when some source number, as is, times 100 or divided
    by 100 (a percentage), equals it after rounding to the token's own
    decimals. A token written without a minus may match a negative source
    number, which is how "a gain of 50" reports a VaR of -50; a token written
    with a minus must match a negative number, so a flipped sign is caught.
    """
    candidates = _source_numbers(source, set())
    missing = []
    for token in _NUMBER.findall(text or ""):
        value = float(token.replace(",", ""))
        decimals = len(token.split(".")[1]) if "." in token else 0
        if not any(round(scaled, decimals) == value
                   or (value >= 0 and round(-scaled, decimals) == value)
                   for number in candidates
                   for scaled in (number, number * 100, number / 100)):
            missing.append(token)
    return missing


def build_answer_graph(model=None, tools=None):
    """Compile the routine.

    tools defaults to the registry's read-only tools, so a model routing a
    question is never handed the tool that writes an ORE output. model is
    needed to route a question and optional for the answer: with tool_calls
    supplied and no model, the answer is the tool results themselves.
    """
    from langgraph.graph import END, START, StateGraph

    from riskdesk_agent.prompts import build_answer_prompt, build_router_prompt
    from riskdesk_agent.tools import desk_tools, read_only_names

    if tools is None:
        tools = desk_tools(include=read_only_names())
    by_name = {tool.name: tool for tool in tools}

    def route(state: AnswerState) -> AnswerState:
        if state.get("tool_calls") is not None:
            return {"log": ["route: {} call(s) supplied by the caller".format(
                len(state["tool_calls"]))]}
        if model is None:
            return {"tool_calls": [], "failures": [
                "no model to route the question and no tool calls supplied"]}
        reply = model.bind_tools(tools).invoke(
            build_router_prompt().format_messages(question=state["question"]))
        calls = [{"name": call["name"], "args": call["args"]}
                 for call in reply.tool_calls]
        invented = sorted({token for call in calls
                           for token in ungrounded_numbers(
                               json.dumps(call["args"]), state["question"])})
        update = {"tool_calls": calls, "log": ["route: chose {}".format(
            ", ".join(call["name"] for call in calls) or "no tool")]}
        if invented:
            update["failures"] = ["the router put numbers in a tool call that "
                                  "the question does not contain: " + ", ".join(invented)]
        return update

    def after_route(state: AnswerState) -> str:
        return "act" if state.get("tool_calls") and not state.get("failures") else "answer"

    def act(state: AnswerState) -> AnswerState:
        calls, budget = state["tool_calls"], state.get("budget", DEFAULT_BUDGET)
        if len(calls) > budget:
            return {"failures": ["{} tool calls exceed the budget of {}; none "
                                 "were run".format(len(calls), budget)]}
        results, failures, log = [], [], []
        for call in calls:
            tool = by_name.get(call["name"])
            if tool is None:
                failures.append("no tool named {}".format(call["name"]))
                break
            try:
                result = tool.invoke(call["args"])
            except Exception as exc:
                failures.append("{} failed: {}: {}".format(
                    call["name"], type(exc).__name__, exc))
                break
            results.append({"tool": call["name"], "arguments": call["args"],
                            "result": result})
            log.append("act: ran {}{}".format(call["name"], " (degraded)"
                                              if result.get("degraded") else ""))
        return {"results": results, "failures": failures, "log": log}

    def answer(state: AnswerState) -> AnswerState:
        results = state.get("results") or []
        context = context_for(results)
        if state.get("failures"):
            text = "\n".join(["No answer: the run failed.", ""]
                             + ["  " + failure for failure in state["failures"]]
                             + ["", context])
            return {"answer": text, "outcome": "failed"}
        if not results:
            return {"answer": "No Risk Desk tool was called for this question, "
                              "so there is no result to report.",
                    "outcome": "declined"}
        if model is None:
            return {"answer": context, "outcome": "answered"}
        text = model.invoke(build_answer_prompt().format_messages(
            question=state["question"], context=context)).content
        missing = ungrounded_numbers(text, [record["result"] for record in results])
        if missing:
            return {"answer": "The model's answer was withheld: it quoted numbers "
                              "that appear in no tool result ({}). The tool "
                              "results follow.\n\n{}".format(", ".join(missing), context),
                    "outcome": "ungrounded", "ungrounded": missing}
        return {"answer": text, "outcome": "answered", "ungrounded": []}

    graph = StateGraph(AnswerState)
    graph.add_node("route", route)
    graph.add_node("act", act)
    graph.add_node("answer", answer)
    graph.add_edge(START, "route")
    graph.add_conditional_edges("route", after_route, {"act": "act", "answer": "answer"})
    graph.add_edge("act", "answer")
    graph.add_edge("answer", END)
    return graph.compile()


def ask(question, model=None, tools=None, tool_calls=None, budget=DEFAULT_BUDGET):
    """Run the routine once and return the final state."""
    state = {"question": question, "budget": budget, "log": [], "failures": []}
    if tool_calls is not None:
        state["tool_calls"] = tool_calls
    return build_answer_graph(model=model, tools=tools).invoke(state)
