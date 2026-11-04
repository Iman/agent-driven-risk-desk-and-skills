"""LangChain bindings for Risk Desk.

A language layer over riskdesk.server: the registered MCP tools become
LangChain tools, their results become documents, and a question is answered
only from what the tools returned. It computes no number of its own.
"""

from riskdesk_agent.artifacts import context_for, documents
from riskdesk_agent.prompts import REPORTING_RULES, build_answer_prompt, build_router_prompt
from riskdesk_agent.tools import desk_tools, read_only_names, tool_specs

# The graph needs langgraph, an optional extra, so it is imported on first use.
__lazy__ = ("build_answer_graph", "ask", "ungrounded_numbers")


def __getattr__(name):
    if name in __lazy__:
        from riskdesk_agent import graph

        return getattr(graph, name)
    raise AttributeError(name)


__version__ = "0.2.0"

__all__ = ["context_for", "documents", "desk_tools", "read_only_names", "tool_specs",
           "build_answer_prompt", "build_router_prompt", "REPORTING_RULES",
           "build_answer_graph", "ask", "ungrounded_numbers", "__version__"]
