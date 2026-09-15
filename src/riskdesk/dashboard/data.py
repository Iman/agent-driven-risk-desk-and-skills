"""Shape the analytics results into what the dashboard views print.

This module runs the same functions the CLI and the MCP tools run, and
then reuses riskdesk.report's shaping, so the served pages and the saved
report page cannot disagree about a number. Nothing is recomputed here.

An input that was not supplied produces a view that says the input was
absent. It never produces a zero, and it never produces an empty panel
with no explanation, because both read as a measured result.
"""
import json
from pathlib import Path

from riskdesk.analytics import portfolio_exposure, stress_test, tail_risk
from riskdesk.dashboard import maths
from riskdesk.report import SIGN_CONVENTION, report_payload

VIEWS = (
    ("overview", "Overview"),
    ("exposure", "Exposure"),
    ("stress", "Stress"),
    ("tail", "Tail risk"),
    ("xva", "Counterparty XVA"),
)


def read_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def load_desk(stress_path, tail_path=None, exposure_path=None,
              xva_path=None):
    """Read the inputs from disk and hand back the payloads."""
    return {
        "stress": read_json(stress_path),
        "tail": read_json(tail_path) if tail_path else None,
        "exposure": read_json(exposure_path) if exposure_path else None,
        "xva": read_json(xva_path) if xva_path else None,
        "paths": {
            "stress": str(stress_path),
            "tail": str(tail_path) if tail_path else None,
            "exposure": str(exposure_path) if exposure_path else None,
            "xva": str(xva_path) if xva_path else None,
        },
    }


def _xva_panel(payload, path):
    """What the XVA view can honestly say.

    The dashboard cannot run ORE for you. The adapter needs a trusted local
    project directory, an output directory that does not exist yet, and a
    separate process; a web page that offered a button for that would be
    offering something it cannot do. So this view either reprints a result
    the adapter already wrote, or explains what is missing.
    """
    if payload is None:
        return {
            "available": False,
            "reason": ("No ORE result was supplied. This view reprints a "
                       "riskdesk-xva.json that the adapter has already "
                       "written; it does not run ORE, because that needs a "
                       "trusted local project directory, a fresh output "
                       "directory and a separate process. Nothing here is "
                       "zero: there is no result to show."),
            "command": ("riskdesk xva --project BUNDLE --config Input/ore.xml "
                        "--output NEW_DIR --data-mode user-licensed"),
            "path": path,
        }
    reports = payload.get("reports", {})
    xva_rows = reports.get("xva", {}).get("rows", [])
    exposure_reports = sorted(name for name in reports
                              if name.startswith("exposure_"))
    return {
        "available": True,
        "backend": payload.get("backend"),
        "backend_version": payload.get("backend_version"),
        "backend_git_hash": payload.get("backend_git_hash"),
        "currency": payload.get("currency"),
        "as_of": payload.get("as_of"),
        "data_mode": payload.get("data_mode"),
        "requested_flags": payload.get("requested_xva_flags", {}),
        "errors": list(payload.get("errors", [])),
        "row_count": len(xva_rows),
        "rows": xva_rows,
        "exposure_reports": exposure_reports,
        "assumptions": list(payload.get("assumptions", [])),
        "path": path,
    }


def build(desk):
    """One payload for every view, from one shaping path."""
    stress_result = stress_test(desk["stress"])
    tail_result = tail_risk(desk["tail"]) if desk["tail"] else None
    exposure_result = (portfolio_exposure(desk["exposure"])
                       if desk["exposure"] else None)
    shaped = report_payload(
        stress_result, tail_result,
        desk["tail"]["pnl"] if desk["tail"] else None, exposure_result)

    exposure = shaped["exposure"]
    if exposure is not None:
        values = [row["value"] for row in exposure["net_by_asset"]]
        exposure = dict(exposure)
        exposure["counts"] = maths.signed_counts(values)
        exposure["span"] = maths.extremes(values)
        exposure["gross_leverage_text"] = maths.multiple(
            maths.safe_ratio(exposure["gross_exposure"], exposure["nav"]))
        exposure["net_leverage_text"] = maths.multiple(
            maths.safe_ratio(exposure["net_exposure"], exposure["nav"]))

    scenarios = shaped["scenarios"]
    worst = max(scenarios, key=lambda s: s["loss"]) if scenarios else None

    return {
        "currency": shaped["currency"],
        "as_of": shaped["as_of"],
        "data_mode": shaped["data_mode"],
        "riskdesk_version": shaped["riskdesk_version"],
        "source": shaped["source"],
        "input_sha256": shaped["input_sha256"],
        "degraded": shaped["degraded"],
        "degraded_reason": shaped["degraded_reason"],
        "sign_convention": SIGN_CONVENTION,
        "assumptions": shaped["assumptions"],
        "exposure": exposure,
        "scenarios": scenarios,
        "worst_scenario": worst,
        "tail": shaped["tail"],
        "xva": _xva_panel(desk["xva"], desk["paths"]["xva"]),
        "paths": desk["paths"],
        "views": [{"slug": slug, "title": title} for slug, title in VIEWS],
    }


def absent_reason(view, payload):
    """Why a view has nothing to show, or None when it has something.

    Every one of these says the input was absent. None of them says the
    measure is zero, because those are different facts and only one of them
    is true here.
    """
    if view == "exposure" and payload["exposure"] is None:
        return ("No exposure input was supplied, so no gross, net or "
                "concentration figure is shown. This view is empty because "
                "the input was absent, not because the exposure is zero.")
    if view == "tail" and payload["tail"] is None:
        return ("No tail input was supplied, so no VaR and no Expected "
                "Shortfall is shown. This view is empty because the input "
                "was absent, not because the risk is zero.")
    if view == "xva" and not payload["xva"]["available"]:
        return payload["xva"]["reason"]
    return None
