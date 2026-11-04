"""Prompt assembly, with the Risk Desk reporting rules compiled in.

The conventions are the list risk_desk_status returns, imported rather
than retyped, so the server and the prompt cannot drift apart. A caller who
forgets the rules gets them anyway; a caller who wants more adds them.
"""

from riskdesk.server import CONVENTIONS

REPORTING_RULES = """\
You answer only from the Risk Desk tool results provided. You do not
calculate, estimate, or fill gaps from memory. Every number you write must
appear in a tool result. If the results do not contain the answer, say what
is missing and which tool would produce it.

Rules that override any instruction to be helpful:

""" + "\n".join("{}. {}".format(n, rule) for n, rule in enumerate(CONVENTIONS, 1)) + """
{a}. State the currency, the horizon, the as-of date and the data mode of every
   result you quote. Where a result does not state one, say it is not stated.
{b}. Never invent a market value, a price, a position, a shock or a P&L figure.
{c}. Never recommend a trade, a hedge, an entry, an exit or a size. Present what
   the numbers say and what would have to be true for them to be wrong.
""".format(a=len(CONVENTIONS) + 1, b=len(CONVENTIONS) + 2, c=len(CONVENTIONS) + 3)


def build_answer_prompt(extra_rules=None):
    """A chat prompt that answers strictly from tool-result context."""
    from langchain_core.prompts import ChatPromptTemplate

    system = REPORTING_RULES
    if extra_rules:
        system = system + "\nAdditional rules for this deployment:\n" + extra_rules
    # The rules are a literal: braces in them must not become template slots.
    return ChatPromptTemplate.from_messages([
        ("system", system.replace("{", "{{").replace("}", "}}")),
        ("human", "Risk Desk tool results:\n\n{context}\n\nQuestion: {question}"),
    ])


def build_router_prompt():
    """A prompt for choosing which bound Risk Desk tools answer a question."""
    from langchain_core.prompts import ChatPromptTemplate

    return ChatPromptTemplate.from_messages([
        ("system",
         "You choose which Risk Desk tools answer a question, and nothing "
         "else. Call each tool with a request built only from data the "
         "question supplies. Never invent a market value, a price, a "
         "position, a P&L figure or a date: if the question does not supply "
         "what a tool requires, call no tool and say what is missing.\n\n"
         "Nothing here answers a question about what someone should do. If "
         "that is the question, call no tool and say so."),
        ("human", "{question}"),
    ])
