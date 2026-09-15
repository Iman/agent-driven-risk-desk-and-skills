"""A self-contained HTML page built from exposure, stress and tail results.

The page is drawn with inline SVG and inline CSS on purpose. It loads no
script, no font and no stylesheet from anywhere, so it renders the same on
a machine with no network and cannot silently report a different number
than the JSON it was built from. No plotting dependency is added: the
shaping functions below are pure and the drawing is arithmetic.

Nothing here recomputes risk. It reads the envelopes produced by
riskdesk.analytics and reprints them, including the sign convention, the
degraded flag and the degraded reason.

The chart functions and `money` are public because the dashboard draws the
same charts. One charting path, so a fix to a sign or an axis reaches both
surfaces, and a reader comparing a saved page with a served one is looking
at the same arithmetic rather than two implementations that agree today.
"""
import html
import math

from riskdesk import design

SIGN_CONVENTION = (
    "Positive VaR and Expected Shortfall denote loss; a negative value "
    "denotes a gain and is not floored at zero. Stress P&L is signed, and "
    "loss is its negation, so a negative loss is a scenario the book gains "
    "in. P&L observations on the tail chart are profit-positive, which is "
    "why the VaR and ES markers sit on the negative side of that axis. "
    "Exposure market values are signed: a negative net value is a short "
    "position and is drawn on the short side of the zero line, while gross "
    "counts absolute values before any offsetting, so a share of gross is "
    "never negative."
)


def money(value, currency):
    return "{:,.2f} {}".format(value, currency)


def histogram(values, bins=None):
    """Equal-width bins over the supplied values, lowest edge first."""
    values = [float(v) for v in values]
    if len(values) < 2:
        raise ValueError("a histogram needs at least two observations")
    if not all(math.isfinite(v) for v in values):
        raise ValueError("histogram observations must be finite")
    if bins is None:
        bins = min(20, max(4, int(math.ceil(math.sqrt(len(values))))))
    if bins < 1:
        raise ValueError("bin count must be positive")
    low, high = min(values), max(values)
    if low == high:
        low, high = low - 0.5, high + 0.5
    width = (high - low) / bins
    counts = [0] * bins
    for value in values:
        index = int((value - low) / width)
        counts[min(index, bins - 1)] += 1
    return [{"low": low + i * width, "high": low + (i + 1) * width,
             "count": counts[i]} for i in range(bins)]


def report_payload(stress_result, tail_result=None, tail_pnl=None,
                   exposure_result=None):
    """Shape the envelopes into everything the page prints.

    The stress result carries the provenance for the page. The tail and
    exposure results are optional; when either is absent the page says so
    rather than leaving a gap. A result in another currency is refused,
    because the page prints one currency in its header and would otherwise
    mislabel a chart.

    `tail_pnl` is the observation list from the tail request. The tail
    envelope deliberately does not carry the caller's observations, so the
    histogram is drawn from the input rather than reconstructed from the
    two summary measures.
    """
    currency = stress_result["currency"]
    if tail_result is not None and tail_result["currency"] != currency:
        raise ValueError("tail and stress results must share one currency")
    if tail_result is not None and tail_pnl is None:
        raise ValueError("a tail result needs its supplied P&L observations")
    if exposure_result is not None and exposure_result["currency"] != currency:
        raise ValueError("exposure and stress results must share one "
                         "currency")
    scenarios = []
    for scenario in stress_result["scenarios"]:
        contributions = sorted(scenario["contributions"].items(),
                               key=lambda item: item[1])
        scenarios.append({
            "name": scenario["name"],
            "pnl": scenario["pnl"],
            "loss": scenario["loss"],
            "stressed_nav": scenario["stressed_nav"],
            "contributions": [{"id": key, "value": value}
                              for key, value in contributions],
            "top_losses": [{"id": key, "value": value}
                           for key, value in contributions[:3]],
        })
    payload = {
        "currency": currency,
        "as_of": stress_result["as_of"],
        "source": stress_result["source"],
        "data_mode": stress_result["data_mode"],
        "method": stress_result["method"],
        "degraded": bool(stress_result["degraded"]),
        "degraded_reason": stress_result["degraded_reason"],
        "input_sha256": stress_result["input_sha256"],
        "riskdesk_version": stress_result["riskdesk_version"],
        "sign_convention": SIGN_CONVENTION,
        "assumptions": list(stress_result["assumptions"]),
        "scenarios": scenarios,
        "tail": None,
        "exposure": None,
    }
    if exposure_result is not None:
        # Net descending, so the longs gather at the top of the ladder and
        # the shorts at the bottom, and a short is a short at a glance.
        # Gross shares descending, because a concentration chart nobody can
        # read in order is not a concentration chart.
        payload["exposure"] = {
            "method": exposure_result["method"],
            "nav": exposure_result["nav"],
            "gross_exposure": exposure_result["gross_exposure"],
            "net_exposure": exposure_result["net_exposure"],
            "gross_leverage": exposure_result["gross_leverage"],
            "net_leverage": exposure_result["net_leverage"],
            "net_by_asset": [
                {"asset": asset, "value": value} for asset, value
                in sorted(exposure_result["net_by_asset"].items(),
                          key=lambda item: (-item[1], item[0]))],
            "gross_shares": [
                {"asset": asset, "share": share} for asset, share
                in sorted(exposure_result["gross_shares"].items(),
                          key=lambda item: (-item[1], item[0]))],
            "degraded": bool(exposure_result["degraded"]),
            "degraded_reason": exposure_result["degraded_reason"],
            "source": exposure_result["source"],
            "as_of": exposure_result["as_of"],
            "input_sha256": exposure_result["input_sha256"],
            "assumptions": list(exposure_result["assumptions"]),
        }
        payload["degraded"] = (payload["degraded"]
                               or payload["exposure"]["degraded"])
        reasons = [r for r in (payload["degraded_reason"],
                               payload["exposure"]["degraded_reason"]) if r]
        payload["degraded_reason"] = "; ".join(reasons) or None
    if tail_result is not None:
        payload["tail"] = {
            "var": tail_result["var"],
            "expected_shortfall": tail_result["expected_shortfall"],
            "confidence": tail_result["confidence"],
            "horizon_days": tail_result["horizon_days"],
            "observations": tail_result["observations"],
            "tail_probability_mass": tail_result["tail_probability_mass"],
            "portfolio_value": tail_result["portfolio_value"],
            "degraded": bool(tail_result["degraded"]),
            "degraded_reason": tail_result["degraded_reason"],
            "source": tail_result["source"],
            "as_of": tail_result["as_of"],
            "bins": histogram(tail_pnl),
            "assumptions": list(tail_result["assumptions"]),
        }
        payload["degraded"] = payload["degraded"] or payload["tail"]["degraded"]
        reasons = [r for r in (payload["degraded_reason"],
                               payload["tail"]["degraded_reason"]) if r]
        payload["degraded_reason"] = "; ".join(reasons) or None
    return payload


def framed(svg):
    """Put a chart in its frame.

    Presentation only: the chart functions are untouched, so there is still
    one place a chart is drawn. The frame exists so a narrow screen scrolls
    the chart instead of shrinking its labels out of legibility.
    """
    return '<div class="chart-frame">' + svg + "</div>"


def net_by_asset_svg(exposure, currency):
    """Signed net exposure per asset, longs and shorts across a zero line.

    A short is the thing a reader most needs to see without arithmetic, so
    it is drawn on its own side of the line rather than as a minus sign in
    a column of numbers. A net of exactly zero is drawn as a mark straddling
    the line: it is neither a long nor a short, and giving it a one-pixel
    bar on either side would say it was.
    """
    rows = exposure["net_by_asset"]
    scale = max((abs(row["value"]) for row in rows), default=0.0) or 1.0
    row_height, label_width, axis_width, top = 28, 250, 380, 40
    height = top + row_height * len(rows) + 28
    width = label_width + axis_width + 190
    zero = label_width + axis_width / 2
    parts = ['<svg class="chart" viewBox="0 0 {} {}" role="img" '
             'aria-label="Signed net exposure by asset, shorts left of the '
             'zero line and longs right of it">'.format(width, height)]
    parts.append('<line x1="{0}" y1="{1}" x2="{0}" y2="{2}" '
                 'class="axis"/>'.format(zero, top - 22, height - 24))
    parts.append('<text x="{}" y="{}" class="tick" text-anchor="middle">'
                 'short</text>'.format(label_width + axis_width / 4, top - 26))
    parts.append('<text x="{}" y="{}" class="tick" text-anchor="middle">'
                 'long</text>'.format(label_width + 3 * axis_width / 4,
                                      top - 26))
    for index, row in enumerate(rows):
        y = top + index * row_height
        length = abs(row["value"]) / scale * (axis_width / 2 - 6)
        if row["value"] > 0:
            x, css, drawn = zero, "bar long", max(length, 1.0)
        elif row["value"] < 0:
            x, css, drawn = zero - max(length, 1.0), "bar short", \
                max(length, 1.0)
        else:
            x, css, drawn = zero - 1.0, "bar flat", 2.0
        parts.append('<text x="{}" y="{}" class="label">{}</text>'.format(
            label_width - 10, y + 15, html.escape(row["asset"])))
        parts.append('<rect x="{:.2f}" y="{}" width="{:.2f}" height="16" '
                     'class="{}"/>'.format(x, y + 3, drawn, css))
        parts.append('<text x="{}" y="{}" class="value">{}</text>'.format(
            label_width + axis_width + 10, y + 15,
            html.escape(money(row["value"], currency))))
    parts.append('<text x="{}" y="{}" class="tick" text-anchor="middle">'
                 'net market value, signed, in {}</text>'.format(
                     width / 2, height - 8, html.escape(currency)))
    parts.append("</svg>")
    return "".join(parts)


def gross_share_svg(exposure, currency):
    """Share of gross exposure per asset, largest first.

    Gross counts absolute values before offsetting, so every bar here runs
    the same way and none of them can be negative. The axis says what the
    shares are shares of, in the base currency, so the chart cannot be read
    as if the percentages were the whole story.
    """
    rows = exposure["gross_shares"]
    largest = max((row["share"] for row in rows), default=0.0) or 1.0
    row_height, label_width, axis_width, top = 26, 250, 420, 24
    height = top + row_height * len(rows) + 28
    width = label_width + axis_width + 110
    parts = ['<svg class="chart" viewBox="0 0 {} {}" role="img" '
             'aria-label="Share of gross exposure by asset, largest '
             'first">'.format(width, height)]
    parts.append('<line x1="{0}" y1="{1}" x2="{0}" y2="{2}" '
                 'class="axis"/>'.format(label_width, top - 8, height - 24))
    for index, row in enumerate(rows):
        y = top + index * row_height
        length = row["share"] / largest * axis_width
        parts.append('<text x="{}" y="{}" class="label">{}</text>'.format(
            label_width - 10, y + 15, html.escape(row["asset"])))
        parts.append('<rect x="{}" y="{}" width="{:.2f}" height="15" '
                     'class="bar share"/>'.format(label_width, y + 3,
                                                  max(length, 1.0)))
        parts.append('<text x="{}" y="{}" class="value">{:.1f}%</text>'.format(
            label_width + axis_width + 10, y + 15, row["share"] * 100))
    parts.append('<text x="{}" y="{}" class="tick" text-anchor="middle">'
                 'share of gross exposure, {} in total</text>'.format(
                     width / 2, height - 8,
                     html.escape(money(exposure["gross_exposure"],
                                        currency))))
    parts.append("</svg>")
    return "".join(parts)


def contribution_svg(scenario, currency):
    rows = scenario["contributions"]
    scale = max((abs(row["value"]) for row in rows), default=0.0) or 1.0
    row_height, label_width, axis_width, top = 28, 250, 380, 24
    height = top + row_height * len(rows) + 28
    width = label_width + axis_width + 170
    zero = label_width + axis_width / 2
    parts = ['<svg class="chart" viewBox="0 0 {} {}" role="img" '
             'aria-label="Position contributions to scenario {}">'.format(
                 width, height, html.escape(scenario["name"], quote=True))]
    parts.append('<line x1="{0}" y1="{1}" x2="{0}" y2="{2}" '
                 'class="axis"/>'.format(zero, top - 8, height - 24))
    parts.append('<text x="{}" y="{}" class="tick">loss</text>'.format(
        label_width + 4, height - 8))
    parts.append('<text x="{}" y="{}" class="tick" text-anchor="end">'
                 'gain</text>'.format(label_width + axis_width, height - 8))
    for index, row in enumerate(rows):
        y = top + index * row_height
        length = abs(row["value"]) / scale * (axis_width / 2 - 6)
        x = zero - length if row["value"] < 0 else zero
        css = "bar loss" if row["value"] < 0 else "bar gain"
        parts.append('<text x="{}" y="{}" class="label">{}</text>'.format(
            label_width - 10, y + 15, html.escape(row["id"])))
        parts.append('<rect x="{:.2f}" y="{}" width="{:.2f}" height="16" '
                     'class="{}"/>'.format(x, y + 3, max(length, 1.0), css))
        parts.append('<text x="{}" y="{}" class="value">{}</text>'.format(
            label_width + axis_width + 10, y + 15,
            html.escape(money(row["value"], currency))))
    parts.append("</svg>")
    return "".join(parts)


def tail_svg(tail, currency):
    bins = tail["bins"]
    low, high = bins[0]["low"], bins[-1]["high"]
    var_at, es_at = -tail["var"], -tail["expected_shortfall"]
    low, high = min(low, var_at, es_at), max(high, var_at, es_at)
    span = (high - low) or 1.0
    # The two markers can land within a few pixels of each other, so their
    # labels are given separate rows rather than allowed to overprint.
    width, height, top, base = 760, 330, 56, 270
    label_rows = {"VaR": 18, "ES": 36}
    tallest = max(b["count"] for b in bins) or 1

    def place(value):
        return 60 + (value - low) / span * (width - 120)

    parts = ['<svg class="chart" viewBox="0 0 {} {}" role="img" '
             'aria-label="Distribution of supplied P&amp;L observations with '
             'VaR and Expected Shortfall marked">'.format(width, height)]
    for bucket in bins:
        x1, x2 = place(bucket["low"]), place(bucket["high"])
        bar = (bucket["count"] / tallest) * (base - top)
        parts.append('<rect x="{:.2f}" y="{:.2f}" width="{:.2f}" '
                     'height="{:.2f}" class="bin"/>'.format(
                         x1, base - bar, max(x2 - x1 - 2, 1.0), bar))
    parts.append('<line x1="40" y1="{0}" x2="{1}" y2="{0}" '
                 'class="axis"/>'.format(base, width - 40))
    for value, name, css in ((var_at, "VaR", "mark var"),
                             (es_at, "ES", "mark es")):
        x = place(value)
        parts.append('<line x1="{0:.2f}" y1="{1}" x2="{0:.2f}" y2="{2}" '
                     'class="{3}"/>'.format(x, top - 8, base, css))
        parts.append('<text x="{:.2f}" y="{}" class="marklabel" '
                     'text-anchor="middle">{} {}</text>'.format(
                         min(max(x, 90.0), width - 90.0),
                         label_rows[name], name,
                         html.escape(money(value, currency))))
    parts.append('<text x="40" y="{}" class="tick">{}</text>'.format(
        base + 20, html.escape(money(low, currency))))
    parts.append('<text x="{}" y="{}" class="tick" text-anchor="end">{}</text>'
                 .format(width - 40, base + 20,
                         html.escape(money(high, currency))))
    parts.append('<text x="{}" y="{}" class="tick" text-anchor="middle">'
                 'supplied P&amp;L observations, profit positive</text>'
                 .format(width / 2, base + 38))
    parts.append("</svg>")
    return "".join(parts)


# The page reads the shared desk tokens. Every colour it paints comes from
# riskdesk.design, so dark and light both come from one place and neither
# is hard coded in a rule. Before this the block here carried 22 literal
# colours, 11 of them chart rules, which is why the dashboard could not be
# restyled without restyling this page too: the dashboard inlines this
# same string.
STYLE = design.STYLE + """
.flag-row { display: flex; flex-wrap: wrap; gap: var(--od-space-4);
            align-items: center; margin: var(--od-space-5) 0; }
"""


def render_html(payload):
    """Draw the page. Every number printed comes from `payload`."""
    esc = html.escape
    flag = "degraded" if payload["degraded"] else "ok"
    label = "degraded" if payload["degraded"] else "not degraded"
    out = ["<!DOCTYPE html>", '<html lang="en"><head><meta charset="utf-8">',
           '<meta name="viewport" content="width=device-width, '
           'initial-scale=1">',
           "<title>Risk Desk exposure, stress and tail report</title>",
           "<style>" + STYLE + "</style></head><body>"]
    out.append("<h1>Risk Desk exposure, stress and tail report</h1>")
    out.append('<p class="meta">As of {} &middot; base currency {} &middot; '
               'data mode {} &middot; riskdesk {}</p>'.format(
                   esc(payload["as_of"]), esc(payload["currency"]),
                   esc(payload["data_mode"]),
                   esc(payload["riskdesk_version"])))
    out.append('<p class="flag-row"><span class="flag {}">{}</span>'.format(
        flag, label))
    # data_mode is a state the page already carried in grey prose. It is a
    # different fact from degraded and gets its own token, never the amber
    # that means stale.
    if payload["data_mode"] == "synthetic":
        out.append('<span class="flag synthetic">synthetic inputs</span>')
    out.append("</p>")
    if payload["degraded_reason"]:
        out.append("<p class=\"meta\">Degraded reason: {}</p>".format(
            esc(payload["degraded_reason"])))
    out.append('<p class="meta">Input source: {}</p>'.format(
        esc(payload["source"])))
    out.append('<p class="meta">Stress input SHA-256: {}</p>'.format(
        esc(payload["input_sha256"])))
    out.append('<div class="convention"><strong>Sign convention.</strong> '
               "{}</div>".format(esc(payload["sign_convention"])))

    out.append("<h2>Linear portfolio exposure</h2>")
    exposure = payload["exposure"]
    if exposure is None:
        out.append("<p>No exposure result was supplied, so no gross, net or "
                   "concentration figure is shown. This section is empty "
                   "because the input was absent, not because the exposure "
                   "is zero.</p>")
    else:
        out.append("<p>Method: {}. Gross counts absolute position values "
                   "before offsetting; net does not. Leverage divides by "
                   "the supplied NAV.</p>".format(esc(exposure["method"])))
        out.append("<table><tr><th>Measure</th><th>Value</th>"
                   "<th>Against NAV</th></tr>")
        out.append("<tr><td>NAV</td><td>{}</td><td></td></tr>".format(
            esc(money(exposure["nav"], payload["currency"]))))
        out.append("<tr><td>Gross exposure</td><td>{}</td><td>{:.4g}x</td>"
                   "</tr>".format(
                       esc(money(exposure["gross_exposure"],
                                  payload["currency"])),
                       exposure["gross_leverage"]))
        out.append("<tr><td>Net exposure</td><td>{}</td><td>{:.4g}x</td>"
                   "</tr>".format(
                       esc(money(exposure["net_exposure"],
                                  payload["currency"])),
                       exposure["net_leverage"]))
        out.append("</table>")
        out.append("<h3>Net exposure by asset</h3>")
        out.append(framed(net_by_asset_svg(exposure, payload["currency"])))
        out.append("<h3>Share of gross exposure</h3>")
        out.append(framed(gross_share_svg(exposure, payload["currency"])))
        out.append('<p class="meta">Exposure input source: {}</p>'.format(
            esc(exposure["source"])))
        out.append('<p class="meta">Exposure input SHA-256: {}</p>'.format(
            esc(exposure["input_sha256"])))

    out.append("<h2>Explicit stress scenarios</h2>")
    out.append("<p>Method: {}. No probability is attached to any scenario. "
               "The stressed NAV column is the supplied NAV moved by the "
               "scenario P&amp;L.</p>".format(esc(payload["method"])))
    out.append("<table><tr><th>Scenario</th><th>P&amp;L</th><th>Loss</th>"
               "<th>Stressed NAV</th></tr>")
    for scenario in payload["scenarios"]:
        out.append("<tr><td>{}</td><td>{}</td><td>{}</td><td>{}</td></tr>"
                   .format(esc(scenario["name"]),
                           esc(money(scenario["pnl"], payload["currency"])),
                           esc(money(scenario["loss"], payload["currency"])),
                           esc(money(scenario["stressed_nav"],
                                      payload["currency"]))))
    out.append("</table>")
    for scenario in payload["scenarios"]:
        out.append("<h3>{}</h3>".format(esc(scenario["name"])))
        out.append(framed(contribution_svg(scenario, payload["currency"])))

    out.append("<h2>Historical tail risk</h2>")
    tail = payload["tail"]
    if tail is None:
        out.append("<p>No tail result was supplied, so no VaR or Expected "
                   "Shortfall is shown. This section is empty because the "
                   "input was absent, not because the risk is zero.</p>")
    else:
        out.append("<p>{} observations, {:.4g}% confidence, {} day horizon, "
                   "tail probability mass {:.6g} observations. Portfolio "
                   "value {}.</p>".format(
                       tail["observations"], tail["confidence"] * 100,
                       tail["horizon_days"], tail["tail_probability_mass"],
                       esc(money(tail["portfolio_value"],
                                  payload["currency"]))))
        out.append("<table><tr><th>Measure</th><th>Value (loss positive)"
                   "</th></tr>")
        out.append("<tr><td>VaR</td><td>{}</td></tr>".format(
            esc(money(tail["var"], payload["currency"]))))
        out.append("<tr><td>Expected Shortfall</td><td>{}</td></tr>".format(
            esc(money(tail["expected_shortfall"], payload["currency"]))))
        out.append("</table>")
        out.append(framed(tail_svg(tail, payload["currency"])))
        out.append('<p class="meta">Tail input source: {}</p>'.format(
            esc(tail["source"])))

    out.append("<h2>Assumptions carried from the inputs</h2><ul>")
    for line in payload["assumptions"]:
        out.append("<li>{}</li>".format(esc(line)))
    if exposure is not None:
        for line in exposure["assumptions"]:
            out.append("<li>{}</li>".format(esc(line)))
    if tail is not None:
        for line in tail["assumptions"]:
            out.append("<li>{}</li>".format(esc(line)))
    out.append("</ul>")
    out.append("<footer>Research software. Historical loss measures are not "
               "risk-neutral valuation, and an explicit scenario is not a "
               "forecast. No order is placed by this tool.</footer>")
    out.append("</body></html>")
    return "\n".join(out) + "\n"


def build_report(stress_payload, tail_payload=None, exposure_payload=None):
    """Run the analytics that were supplied and return (html, payload)."""
    from riskdesk.analytics import portfolio_exposure, stress_test, tail_risk

    stress_result = stress_test(stress_payload)
    tail_result = tail_risk(tail_payload) if tail_payload is not None else None
    observations = tail_payload["pnl"] if tail_payload is not None else None
    exposure_result = (portfolio_exposure(exposure_payload)
                       if exposure_payload is not None else None)
    payload = report_payload(stress_result, tail_result, observations,
                             exposure_result)
    return render_html(payload), payload
