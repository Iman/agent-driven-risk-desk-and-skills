"""Render the dashboard views as self-contained HTML.

The charts come from riskdesk.report, not from a second implementation.
The styling is riskdesk.report's, plus a navigation strip. Nothing is
fetched: no script, no font, no stylesheet and no image is loaded from
anywhere, so the page renders identically on a machine with no network and
cannot quietly show something other than what it was given.

Every view prints the sign convention and the degraded flag, whether or not
the flag is set, because a loss figure without them is unreadable and a
page that only mentions degradation when degraded trains a reader to stop
looking for it.
"""
import html

from riskdesk.dashboard import data as desk_data
from riskdesk.dashboard import maths
from riskdesk.report import (STYLE, contribution_svg, gross_share_svg, money,
                             net_by_asset_svg, tail_svg)

NAV_STYLE = """
nav { display: flex; flex-wrap: wrap; gap: 4px; margin: 0 0 18px 0;
      border-bottom: 1px solid #d4d4d8; padding-bottom: 10px; }
nav a { font-size: 13px; text-decoration: none; color: #1d1d1f;
        padding: 6px 12px; border-radius: 4px; border: 1px solid #d4d4d8; }
nav a.here { background: #1d1d1f; color: #ffffff; border-color: #1d1d1f; }
nav a.empty { color: #6a6a70; border-style: dashed; }
.absent { border-left: 3px solid #b08838; background: #fbf5e9;
          padding: 10px 14px; font-size: 13px; }
.counts { font-size: 13px; }
.counts strong { font-variant-numeric: tabular-nums; }
.pathline { font-size: 11px; color: #5a5a60; word-break: break-all; }
code { font-size: 12px; background: #f2f2f4; padding: 1px 4px;
       border-radius: 3px; }
pre { font-size: 12px; background: #f2f2f4; padding: 10px;
      overflow-x: auto; border-radius: 4px; }
"""


def _shell(payload, slug, body):
    """The frame every view shares: title, provenance, flag, convention."""
    esc = html.escape
    title = next(v["title"] for v in payload["views"] if v["slug"] == slug)
    flag = "degraded" if payload["degraded"] else "ok"
    label = "degraded" if payload["degraded"] else "not degraded"
    out = ["<!DOCTYPE html>", '<html lang="en"><head><meta charset="utf-8">',
           '<meta name="viewport" content="width=device-width, '
           'initial-scale=1">',
           "<title>Risk Desk dashboard: {}</title>".format(esc(title)),
           "<style>" + STYLE + NAV_STYLE + "</style></head><body>"]
    out.append("<h1>Risk Desk dashboard</h1>")
    out.append('<p class="meta">As of {} &middot; base currency {} &middot; '
               'data mode {} &middot; riskdesk {} &middot; local only, no '
               'request leaves this machine</p>'.format(
                   esc(payload["as_of"]), esc(payload["currency"]),
                   esc(payload["data_mode"]),
                   esc(payload["riskdesk_version"])))
    out.append("<nav>")
    for view in payload["views"]:
        classes = ["here"] if view["slug"] == slug else []
        if desk_data.absent_reason(view["slug"], payload):
            classes.append("empty")
        out.append('<a class="{}" href="/{}">{}</a>'.format(
            " ".join(classes), view["slug"], esc(view["title"])))
    out.append("</nav>")
    out.append('<p><span class="flag {}">{}</span></p>'.format(flag, label))
    if payload["degraded_reason"]:
        out.append('<p class="meta">Degraded reason: {}</p>'.format(
            esc(payload["degraded_reason"])))
    out.append('<div class="convention"><strong>Sign convention.</strong> '
               "{}</div>".format(esc(payload["sign_convention"])))
    out.append("<h2>{}</h2>".format(esc(title)))
    out.extend(body)
    out.append("<footer>Research software. Historical loss measures are not "
               "risk-neutral valuation, an explicit scenario is not a "
               "forecast, and a reproducing regression value is not model "
               "validation. No order is placed by this tool, and this "
               "server makes no outbound request.</footer>")
    out.append("</body></html>")
    return "\n".join(out) + "\n"


def _absent(reason, extra=None):
    body = ['<div class="absent">{}</div>'.format(html.escape(reason))]
    if extra:
        body.append(extra)
    return body


def overview(payload):
    esc = html.escape
    currency = payload["currency"]
    body = ["<p>Every figure below was computed by the same functions the "
            "CLI and the MCP tools call. This page recomputes nothing.</p>"]
    body.append("<table><tr><th>View</th><th>State</th><th>Headline</th>"
                "</tr>")

    exposure = payload["exposure"]
    if exposure is None:
        body.append("<tr><td>Exposure</td><td>input absent</td><td>nothing "
                    "to show, which is not the same as zero</td></tr>")
    else:
        counts = exposure["counts"]
        body.append("<tr><td>Exposure</td><td>loaded</td><td>gross {}, net "
                    "{}, {} long and {} short of {} legs</td></tr>".format(
                        esc(money(exposure["gross_exposure"], currency)),
                        esc(money(exposure["net_exposure"], currency)),
                        counts["long"], counts["short"],
                        len(exposure["net_by_asset"])))

    worst = payload["worst_scenario"]
    body.append("<tr><td>Stress</td><td>loaded</td><td>{} scenarios, worst "
                "loss {} in {}</td></tr>".format(
                    len(payload["scenarios"]),
                    esc(money(worst["loss"], currency)),
                    esc(worst["name"])) if worst else
                "<tr><td>Stress</td><td>loaded</td><td>no scenarios</td></tr>")

    tail = payload["tail"]
    if tail is None:
        body.append("<tr><td>Tail risk</td><td>input absent</td><td>nothing "
                    "to show, which is not the same as zero</td></tr>")
    else:
        body.append("<tr><td>Tail risk</td><td>loaded</td><td>VaR {}, ES {} "
                    "at {} over {} day(s)</td></tr>".format(
                        esc(money(tail["var"], currency)),
                        esc(money(tail["expected_shortfall"], currency)),
                        maths.percent(tail["confidence"], 4),
                        tail["horizon_days"]))

    xva = payload["xva"]
    if xva["available"]:
        body.append("<tr><td>Counterparty XVA</td><td>loaded</td><td>{} rows "
                    "from {} {}</td></tr>".format(
                        xva["row_count"], esc(str(xva["backend"])),
                        esc(str(xva["backend_version"]))))
    else:
        body.append("<tr><td>Counterparty XVA</td><td>input absent</td><td>no "
                    "ORE result supplied; this view never runs ORE</td></tr>")
    body.append("</table>")

    body.append("<h3>Where these came from</h3><ul>")
    for name, path in payload["paths"].items():
        body.append('<li>{}: <span class="pathline">{}</span></li>'.format(
            esc(name), esc(path) if path else "not supplied"))
    body.append("</ul>")
    body.append('<p class="meta">Stress input SHA-256: {}</p>'.format(
        esc(payload["input_sha256"])))
    body.append('<p class="meta">Input source: {}</p>'.format(
        esc(payload["source"])))
    return _shell(payload, "overview", body)


def exposure(payload):
    reason = desk_data.absent_reason("exposure", payload)
    if reason:
        return _shell(payload, "exposure", _absent(reason))
    esc = html.escape
    view = payload["exposure"]
    currency = payload["currency"]
    counts = view["counts"]
    body = ["<p>Method: {}. Gross counts absolute position values before "
            "offsetting; net does not. Leverage divides by the supplied "
            "NAV.</p>".format(esc(view["method"]))]
    body.append('<p class="counts">Of {} legs, <strong>{}</strong> are long, '
                "<strong>{}</strong> are short and <strong>{}</strong> are "
                "flat.</p>".format(len(view["net_by_asset"]), counts["long"],
                                   counts["short"], counts["flat"]))
    body.append("<table><tr><th>Measure</th><th>Value</th>"
                "<th>Against NAV</th></tr>")
    body.append("<tr><td>NAV</td><td>{}</td><td></td></tr>".format(
        esc(money(view["nav"], currency))))
    body.append("<tr><td>Gross exposure</td><td>{}</td><td>{}</td></tr>"
                .format(esc(money(view["gross_exposure"], currency)),
                        esc(view["gross_leverage_text"])))
    body.append("<tr><td>Net exposure</td><td>{}</td><td>{}</td></tr>".format(
        esc(money(view["net_exposure"], currency)),
        esc(view["net_leverage_text"])))
    body.append("</table>")
    body.append("<h3>Net exposure by asset</h3>")
    body.append(net_by_asset_svg(view, currency))
    body.append("<h3>Share of gross exposure</h3>")
    body.append(gross_share_svg(view, currency))
    body.append('<p class="meta">Exposure input source: {}</p>'.format(
        esc(view["source"])))
    body.append('<p class="meta">Exposure input SHA-256: {}</p>'.format(
        esc(view["input_sha256"])))
    return _shell(payload, "exposure", body)


def stress(payload):
    esc = html.escape
    currency = payload["currency"]
    body = ["<p>Explicit shocks applied to every position. No probability "
            "is attached to any scenario, and a scenario named after a "
            "historical episode carries a shape somebody chose, not a "
            "fitted event.</p>"]
    body.append("<table><tr><th>Scenario</th><th>P&amp;L</th><th>Loss</th>"
                "<th>Stressed NAV</th></tr>")
    for scenario in payload["scenarios"]:
        body.append("<tr><td>{}</td><td>{}</td><td>{}</td><td>{}</td></tr>"
                    .format(esc(scenario["name"]),
                            esc(money(scenario["pnl"], currency)),
                            esc(money(scenario["loss"], currency)),
                            esc(money(scenario["stressed_nav"], currency))))
    body.append("</table>")
    for scenario in payload["scenarios"]:
        body.append("<h3>{}</h3>".format(esc(scenario["name"])))
        body.append(contribution_svg(scenario, currency))
    body.append('<p class="meta">Stress input SHA-256: {}</p>'.format(
        esc(payload["input_sha256"])))
    return _shell(payload, "stress", body)


def tail(payload):
    reason = desk_data.absent_reason("tail", payload)
    if reason:
        return _shell(payload, "tail", _absent(reason))
    esc = html.escape
    view = payload["tail"]
    currency = payload["currency"]
    body = ["<p>{} observations, {} confidence, {} day horizon, tail "
            "probability mass {:.6g} observations. Portfolio value "
            "{}.</p>".format(view["observations"],
                             maths.percent(view["confidence"], 4),
                             view["horizon_days"],
                             view["tail_probability_mass"],
                             esc(money(view["portfolio_value"], currency)))]
    body.append("<table><tr><th>Measure</th>"
                "<th>Value (loss positive)</th></tr>")
    body.append("<tr><td>VaR</td><td>{}</td></tr>".format(
        esc(money(view["var"], currency))))
    body.append("<tr><td>Expected Shortfall</td><td>{}</td></tr>".format(
        esc(money(view["expected_shortfall"], currency))))
    body.append("</table>")
    body.append(tail_svg(view, currency))
    body.append('<p class="meta">Tail input source: {}</p>'.format(
        esc(view["source"])))
    return _shell(payload, "tail", body)


def xva(payload):
    esc = html.escape
    view = payload["xva"]
    reason = desk_data.absent_reason("xva", payload)
    if reason:
        extra = "<p>Run the adapter yourself, then point the dashboard at " \
                "the file it writes:</p><pre>{}</pre>".format(
                    esc(view["command"]))
        return _shell(payload, "xva", _absent(reason, extra))
    body = ["<p>Reprinted from a result the adapter already wrote. This "
            "page did not run ORE. Netting-set and trade rows overlap, so "
            "they are never added together, and a zero in a column whose "
            "adjustment was not requested is a disabled calculation rather "
            "than a result.</p>"]
    body.append("<table><tr><th>Field</th><th>Value</th></tr>")
    for label, value in (("Backend", view["backend"]),
                         ("Backend version", view["backend_version"]),
                         ("Backend revision", view["backend_git_hash"]),
                         ("Currency", view["currency"]),
                         ("As of", view["as_of"]),
                         ("Data mode", view["data_mode"]),
                         ("XVA rows", view["row_count"]),
                         ("Errors reported", len(view["errors"]))):
        body.append("<tr><td>{}</td><td>{}</td></tr>".format(
            esc(str(label)),
            esc("unavailable" if value is None else str(value))))
    body.append("</table>")
    if view["requested_flags"]:
        body.append("<h3>Adjustments requested of ORE</h3><table><tr>"
                    "<th>Flag</th><th>Requested</th></tr>")
        for flag, value in sorted(view["requested_flags"].items()):
            body.append("<tr><td>{}</td><td>{}</td></tr>".format(
                esc(str(flag)),
                esc("unavailable" if value is None else str(value))))
        body.append("</table>")
    if view["exposure_reports"]:
        body.append("<p>Exposure reports present: {}.</p>".format(
            esc(", ".join(view["exposure_reports"]))))
    body.append('<p class="pathline">Read from {}</p>'.format(
        esc(str(view["path"]))))
    return _shell(payload, "xva", body)


RENDERERS = {"overview": overview, "exposure": exposure, "stress": stress,
             "tail": tail, "xva": xva}


def render(payload, slug):
    if slug not in RENDERERS:
        raise KeyError(slug)
    return RENDERERS[slug](payload)


def not_found(payload, wanted):
    body = _absent("There is no view called {!r}. This server serves a fixed "
                   "set of views and reads nothing else from disk.".format(
                       wanted))
    return _shell(payload, "overview", body)
