"""Turn one Risk Desk result envelope into a few readable lines.

This exists so demo.sh can show what a result means without a reader
parsing JSON in their head, and so the wording that states the sign
convention lives in one testable, importable place rather than in
shell quoting.

It prints only values that are present in the envelope it was given. It
computes nothing, it rounds for display only, and it always prints the
degraded flag, because a number without its degraded status is the one
thing this project refuses to show.

    riskdesk tail --input examples/tail.json | python -m riskdesk.summaries tail
"""
import argparse
import json
import sys

SIGNS = {
    "tail": ("loss is positive: a positive VaR or ES is a loss, a negative "
             "one is a gain, and neither is floored at zero"),
    "exposure": ("market values are signed: gross counts absolute values "
                 "before offsetting, net does not"),
    "stress": ("P&L is signed and loss is its negation, so a negative loss "
               "is a scenario the book gains in"),
}


def _money(value, currency):
    return "{:,.2f} {}".format(value, currency)


def _header(result, kind):
    lines = ["  method:    {}".format(result["method"]),
             "  as of:     {} in {}, data mode {}".format(
                 result["as_of"], result["currency"], result["data_mode"]),
             "  signs:     {}".format(SIGNS[kind])]
    if result["degraded"]:
        lines.append("  DEGRADED:  {}".format(result["degraded_reason"]))
    else:
        lines.append("  degraded:  no")
    return lines


def summarise_tail(result):
    currency = result["currency"]
    return _header(result, "tail") + [
        "  VaR:       {} at {:.6g}% over {} day(s)".format(
            _money(result["var"], currency), result["confidence"] * 100,
            result["horizon_days"]),
        "  ES:        {}".format(
            _money(result["expected_shortfall"], currency)),
        "  sample:    {} observations, {:.6g} of them in the tail".format(
            result["observations"], result["tail_probability_mass"]),
    ]


def summarise_exposure(result):
    currency = result["currency"]
    top = sorted(result["gross_shares"].items(), key=lambda kv: -kv[1])[:3]
    return _header(result, "exposure") + [
        "  NAV:       {}".format(_money(result["nav"], currency)),
        "  gross:     {} ({:.3g}x NAV)".format(
            _money(result["gross_exposure"], currency),
            result["gross_leverage"]),
        "  net:       {} ({:.3g}x NAV)".format(
            _money(result["net_exposure"], currency),
            result["net_leverage"]),
        "  largest:   " + ", ".join(
            "{} {:.1f}% of gross".format(asset, share * 100)
            for asset, share in top),
    ]


def summarise_stress(result):
    currency = result["currency"]
    lines = _header(result, "stress")
    for scenario in result["scenarios"]:
        worst = sorted(scenario["contributions"].items(),
                       key=lambda kv: kv[1])[:3]
        lines.append("  scenario:  {}".format(scenario["name"]))
        lines.append("    loss:            {}".format(
            _money(scenario["loss"], currency)))
        lines.append("    stressed NAV:    {}".format(
            _money(scenario["stressed_nav"], currency)))
        lines.append("    worst three positions by P&L:")
        for position, value in worst:
            lines.append("      {:<28} {}".format(
                position, _money(value, currency)))
    return lines


SUMMARIES = {"tail": summarise_tail, "exposure": summarise_exposure,
             "stress": summarise_stress}


def summarise(kind, result):
    if kind not in SUMMARIES:
        raise ValueError("unknown result kind: " + kind)
    if "error" in result and "method" not in result:
        raise ValueError("{}: {}".format(result["error"],
                                         result.get("message", "")))
    return SUMMARIES[kind](result)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("kind", choices=sorted(SUMMARIES))
    args = parser.parse_args(argv)
    try:
        result = json.loads(sys.stdin.read())
        lines = summarise(args.kind, result)
    except (ValueError, KeyError, TypeError) as exc:
        print("could not summarise the {} result: {}".format(args.kind, exc))
        return 1
    for line in lines:
        print(line)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
