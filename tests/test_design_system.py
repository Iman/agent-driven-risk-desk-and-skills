"""The design system's own rules, enforced against the real files.

Two of these guards exist because of a specific failure in the repository
this system was copied from. Its first token guard was anchored to the
start of a line, so a token written as `:root { --x: 1px; }` on one line
was invisible to it, and a reformatted token file would have silently
disabled every check while still reporting a pass. The token layer copied
here contains exactly that shape, twice, in its `color-scheme` blocks. So
each guard below is mutation checked in the same file: a deliberately
broken input is fed to it and it is required to object.
"""
import importlib.util
from pathlib import Path
import re

import pytest

from riskdesk import design

ROOT = Path(__file__).resolve().parent.parent
# No re.VERBOSE here. An earlier version of this line used it, which
# stripped the spaces out of the alternation and left a branch that matched
# the empty string, so the guard reported a literal on every file including
# ones that had none. The mutation check below is what caught it.
COLOUR = re.compile(r"#[0-9a-fA-F]{3,8}\b|\b(?:rgba?|hsla?)\(")
STYLED = ["src/riskdesk/report.py", "src/riskdesk/dashboard/page.py"]

pytestmark = pytest.mark.validation


@pytest.fixture(scope="module")
def contrast():
    spec = importlib.util.spec_from_file_location(
        "riskdesk_contrast", ROOT / "scripts" / "contrast.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_the_token_layer_is_the_only_place_a_colour_is_written():
    """Every other rule reads a token. A literal anywhere else is a colour
    that cannot follow the light mode, which is how a page ends up with
    one hard-coded value that stays dark on a white ground."""
    for name in STYLED:
        body = (ROOT / name).read_text(encoding="utf-8")
        found = COLOUR.findall(body)
        assert not found, "{} writes a colour literal: {}".format(name,
                                                                  found)
    components = design.COMPONENTS
    assert not COLOUR.findall(components), \
        "the component layer writes a colour literal"


def test_the_colour_guard_would_catch_a_literal():
    """Mutation check. A guard never seen to object cannot be told from one
    that cannot object."""
    assert COLOUR.findall("a { color: #fff; }")
    assert COLOUR.findall("a { color: #1d1d1f; }")
    assert COLOUR.findall("a { fill: rgba(0, 0, 0, 0.5); }")
    assert COLOUR.findall("a { fill: hsl(10 20% 30%); }")
    assert not COLOUR.findall("a { color: var(--od-text); }")


def tokens_declared(text):
    """Every token name declared, wherever it sits on a line.

    Deliberately not anchored to the start of a line. The copied token
    layer writes `:root { color-scheme: dark; }` on one line, and a guard
    that only matched a token at the head of a line would go quiet the
    moment somebody reformatted the file.
    """
    return set(re.findall(r"(--od-[a-z0-9-]+)\s*:", text))


def test_the_token_scan_is_not_anchored_to_the_start_of_a_line():
    """Mutation check for the exact defect this guard is written against."""
    one_line = ":root { --od-ground: #000000; --od-text: #fff; }"
    assert tokens_declared(one_line) == {"--od-ground", "--od-text"}
    anchored = set(re.findall(r"^\s*(--od-[a-z0-9-]+)\s*:", one_line,
                              re.MULTILINE))
    assert anchored != tokens_declared(one_line), \
        "the anchored pattern would have found these, so this test proves nothing"


def test_both_modes_define_every_state_token(contrast):
    """A token defined in one mode only is a colour that survives the theme
    switch unchanged, which is the inconsistency this system exists to
    close."""
    dark = contrast.read_tokens(design.TOKENS, "dark")
    blocks = design.TOKENS.split("@media (prefers-color-scheme: light)")
    light_only = dict(re.findall(
        r"(--od-[a-z0-9-]+)\s*:\s*(#[0-9a-fA-F]{3,8})\s*;",
        "".join(blocks[1:])))
    for name in ("--od-ground", "--od-surface", "--od-text",
                 "--od-text-muted", "--od-text-faint", "--od-accent",
                 "--od-accent-ink", "--od-gain", "--od-gain-ground",
                 "--od-loss", "--od-loss-ground", "--od-degraded",
                 "--od-degraded-ground", "--od-synthetic",
                 "--od-synthetic-ground", "--od-stale", "--od-stale-ground",
                 "--od-axis", "--od-line"):
        assert name in dark, "{} is not defined in dark".format(name)
        assert name in light_only, "{} is not redefined in light".format(name)


def test_every_token_a_rule_reads_is_declared():
    """A var() pointing at nothing renders as nothing, silently."""
    declared = tokens_declared(design.TOKENS)
    used = set(re.findall(r"var\((--od-[a-z0-9-]+)\)",
                          design.COMPONENTS + "".join(
                              (ROOT / name).read_text(encoding="utf-8")
                              for name in STYLED)))
    missing = used - declared
    assert not missing, "rules read undeclared tokens: {}".format(
        sorted(missing))


def test_the_stale_token_is_declared_and_deliberately_unpainted():
    """This project has no freshness state. The token stays so the set can
    be compared with the file it was copied from, and nothing binds it,
    because binding the small-sample warning to it would paint a degraded
    page in the amber that means stale."""
    assert "--od-stale" in tokens_declared(design.TOKENS)
    surfaces = design.COMPONENTS + "".join(
        (ROOT / name).read_text(encoding="utf-8") for name in STYLED)
    assert "var(--od-stale)" not in surfaces
    assert "var(--od-stale-ground)" not in surfaces
    assert "deliberately unused" in design.__doc__.lower() \
        or "DELIBERATELY UNUSED" in design.__doc__


def test_the_measured_contrast_has_no_enforced_failure(contrast):
    rows = contrast.measure(design.TOKENS)
    failures = [row for row in rows if not row["passed"]]
    assert not failures, "; ".join(
        "{} {} on {} {:.2f}:1".format(row["mode"], row["foreground"],
                                      row["background"], row["ratio"])
        for row in failures)
    enforced = [row for row in rows if row["enforced"]]
    assert len(enforced) >= 30, "too few pairs enforced to mean anything"
    assert {row["mode"] for row in rows} == {"dark", "light"}


def test_the_contrast_measurement_would_fail_a_bad_pair(contrast):
    """Mutation check. A grey on black that no reader could use must be
    rejected, or the measurement above proves nothing."""
    broken = design.TOKENS.replace("--od-text: #e8eaed;",
                                   "--od-text: #0a0a0a;")
    assert broken != design.TOKENS
    rows = contrast.measure(broken)
    assert any(not row["passed"] for row in rows)


def test_the_provenance_is_recorded_where_someone_will_read_it():
    """Copied, not imported, so the two can drift. The module has to say
    where it came from and that they must be kept in step."""
    doc = design.__doc__
    assert "optiondesk.avidquant.com" in doc
    assert "KEPT IN STEP" in doc.upper()
    assert "COPIED, NOT IMPORTED" in doc.upper()


def test_the_page_still_adds_no_dependency_and_fetches_nothing():
    for name in STYLED + ["src/riskdesk/design.py"]:
        body = (ROOT / name).read_text(encoding="utf-8")
        for forbidden in ("@import", "@font-face", "url(http", "//fonts.",
                          "cdn."):
            assert forbidden not in body, "{}: {}".format(name, forbidden)
