"""Tool results as retrievable text, degraded status first.

A record is one tool call: {"tool", "arguments", "result"}. Risk Desk
results are small JSON envelopes, so the whole result is kept in the text
and nothing is summarised away; the lines above it put the degraded flag
and the provenance where a reader meets them before any figure.
"""

import json

# The four a reader must be told; a result that lacks one says so.
STATED = (("currency", "currency"), ("horizon_days", "horizon days"),
          ("as_of", "as of"), ("data_mode", "data mode"))


def summarise(record):
    """One block per tool result. Never raises for a JSON-shaped record."""
    tool, result = record.get("tool", "unknown tool"), record.get("result")
    if not isinstance(result, dict):
        return "{} returned no result object, so nothing is quoted from it.".format(tool)
    if result.get("degraded"):
        lines = ["DEGRADED: {}".format(result.get("degraded_reason") or "no reason given")]
    elif "degraded" in result:
        lines = ["degraded: no"]
    else:
        lines = ["degraded: not stated by {}".format(tool)]
    stated = ["{} {}".format(label, result[key]) for key, label in STATED if key in result]
    absent = [label for key, label in STATED if key not in result]
    lines.append("{} result: {}{}".format(
        tool, ", ".join(stated) or "no provenance fields",
        "; not stated: " + ", ".join(absent) if absent else ""))
    if "source" in result:
        lines.append("source: {}".format(result["source"]))
    lines.append("result: " + json.dumps(result, sort_keys=True))
    return "\n".join(lines)


def context_for(records):
    """All results as one prompt context, in call order."""
    if not records:
        return ("No tool result is available for this request. Nothing can "
                "be answered from data that was not supplied.")
    return "\n\n".join(summarise(record) for record in records)


def documents(records):
    """LangChain documents, one per tool result."""
    from langchain_core.documents import Document

    out = []
    for record in records:
        result = record.get("result") if isinstance(record.get("result"), dict) else {}
        out.append(Document(page_content=summarise(record), metadata={
            "tool": record.get("tool"), "degraded": bool(result.get("degraded")),
            "currency": result.get("currency"), "as_of": result.get("as_of"),
            "data_mode": result.get("data_mode"),
            "input_sha256": result.get("input_sha256")}))
    return out
