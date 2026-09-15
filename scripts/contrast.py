#!/usr/bin/env python3
"""Measure WCAG contrast for every token pair this project actually paints.

WHY THIS IS MEASURED HERE. The design system these tokens came from
records 50 pairs at 0 failures. That figure was measured on the other
service's markup, against pairs it puts on screen. This project paints a
different set: it has no stale state, it does paint a synthetic one, and
its charts use the accent as a bar fill rather than as a link. Inheriting
somebody else's pass would be claiming a measurement nobody made here.

Thresholds are WCAG 2.1: 4.5 to 1 for body text, 3.0 to 1 for a graphical
object or a large label. Every pair below names which it is, and the
reason it is on the list is the place it appears on screen.

    python3 scripts/contrast.py          measure, print, exit non-zero on a failure
    python3 scripts/contrast.py --all    also print the pairs that pass
"""
import argparse
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parent.parent

TEXT = 4.5
GRAPHIC = 3.0

# Measured and printed, but not required to meet a threshold, and the
# reason is given per pair. WCAG 2.1 SC 1.4.11 asks 3 to 1 of a user
# interface component's boundary and of a graphical object required to
# understand the content. It exempts decoration. A table's internal rules
# are neither: the table is not a control, and every figure in it stays
# readable with the rules removed, because the numerics are right aligned
# under labelled column heads. The chart axis is NOT in this category and
# is enforced, because the zero line is what tells a long from a short.
#
# This is recorded rather than deleted so the number stays visible. It is
# 1.39 to 1 in dark and 1.48 to 1 in light. Raising it would mean changing
# a token this repository copied from the shared system and is required to
# keep in step, and the only token that clears 3 to 1 against the ground
# is --od-text-faint, which would turn a dense table into a heavy grid.
DECORATIVE = None

# foreground token, background token, threshold, where it appears
PAIRS = [
    ("--od-text", "--od-ground", TEXT, "body text on the page"),
    ("--od-text-muted", "--od-ground", TEXT, "meta and provenance lines"),
    ("--od-text", "--od-surface", TEXT, "sign convention block"),
    ("--od-text-muted", "--od-surface", TEXT, "table column heads"),
    ("--od-gain", "--od-gain-ground", TEXT, "the not degraded flag"),
    ("--od-degraded", "--od-degraded-ground", TEXT, "the degraded flag"),
    ("--od-synthetic", "--od-synthetic-ground", TEXT, "the synthetic flag"),
    ("--od-accent-ink", "--od-accent", TEXT, "the current nav item"),
    ("--od-text", "--od-surface-raised", TEXT, "nav items at rest"),
    ("--od-text-faint", "--od-ground", GRAPHIC, "footer, and the flat bar"),
    ("--od-loss", "--od-ground", GRAPHIC, "loss and short bars, VaR mark"),
    ("--od-gain", "--od-ground", GRAPHIC, "gain and long bars"),
    ("--od-accent", "--od-ground", GRAPHIC, "share bars and histogram bins"),
    ("--od-synthetic", "--od-ground", GRAPHIC, "the Expected Shortfall mark"),
    ("--od-axis", "--od-ground", GRAPHIC, "chart axes"),
    ("--od-line", "--od-ground", DECORATIVE, "table rules, decoration"),
    ("--od-accent", "--od-surface", GRAPHIC, "convention block edge"),
]


def read_tokens(text, mode):
    """Every token value for one mode.

    Light starts from the dark set and overrides it, exactly as the cascade
    does, so a token the light block does not restate keeps its dark value
    rather than going missing.
    """
    blocks = text.split("@media (prefers-color-scheme: light)")
    dark = dict(re.findall(r"(--od-[a-z0-9-]+)\s*:\s*(#[0-9a-fA-F]{3,8})\s*;",
                           blocks[0]))
    if mode == "dark":
        return dark
    light = dict(dark)
    light.update(re.findall(r"(--od-[a-z0-9-]+)\s*:\s*(#[0-9a-fA-F]{3,8})\s*;",
                            "".join(blocks[1:])))
    return light


def channel(value):
    value = value / 255.0
    return value / 12.92 if value <= 0.04045 else ((value + 0.055) / 1.055) ** 2.4


def luminance(hex_colour):
    raw = hex_colour.lstrip("#")
    if len(raw) == 3:
        raw = "".join(c * 2 for c in raw)
    red, green, blue = (int(raw[i:i + 2], 16) for i in (0, 2, 4))
    return (0.2126 * channel(red) + 0.7152 * channel(green)
            + 0.0722 * channel(blue))


def ratio(foreground, background):
    first, second = luminance(foreground), luminance(background)
    lighter, darker = max(first, second), min(first, second)
    return (lighter + 0.05) / (darker + 0.05)


def measure(text):
    rows = []
    for mode in ("dark", "light"):
        tokens = read_tokens(text, mode)
        for front, back, threshold, where in PAIRS:
            missing = [n for n in (front, back) if n not in tokens]
            if missing:
                raise ValueError("no such token in {} mode: {}".format(
                    mode, ", ".join(missing)))
            value = ratio(tokens[front], tokens[back])
            rows.append({"mode": mode, "foreground": front,
                         "background": back, "threshold": threshold,
                         "ratio": value,
                         "passed": threshold is None or value >= threshold,
                         "enforced": threshold is not None,
                         "where": where})
    return rows


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--all", action="store_true",
                        help="print passing pairs too")
    args = parser.parse_args(argv)
    source = (ROOT / "src" / "riskdesk" / "design.py").read_text(
        encoding="utf-8")
    rows = measure(source)
    failures = [row for row in rows if not row["passed"]]
    for row in rows:
        if args.all or not row["passed"]:
            print("{:5} {:22} on {:22} {:6.2f}:1 {:>8}  {}  {}".format(
                row["mode"], row["foreground"], row["background"],
                row["ratio"],
                "need {:.1f}".format(row["threshold"]) if row["enforced"]
                else "no min",
                ("PASS" if row["passed"] else "FAIL") if row["enforced"]
                else "NOTE", row["where"]))
    enforced = [row for row in rows if row["enforced"]]
    recorded = [row for row in rows if not row["enforced"]]
    print("{} pairs enforced, {} failures; {} recorded as decoration".format(
        len(enforced), len(failures), len(recorded)))
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
