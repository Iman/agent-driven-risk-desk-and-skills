"""Rendering. In process, no socket, no subprocess.

Two properties matter more than any individual string. Every view prints
the sign convention and the degraded flag, whether or not the flag is set,
because a page that mentions degradation only when degraded trains a reader
to stop looking for it. And no view loads anything from anywhere, so what a
reader sees is what the page was given.
"""
from pathlib import Path
import re

import pytest

from riskdesk.dashboard import data, page
from riskdesk.report import SIGN_CONVENTION

EXAMPLES = Path(__file__).resolve().parent.parent / "examples"
SLUGS = ("overview", "exposure", "stress", "tail", "xva")

pytestmark = pytest.mark.unit


@pytest.fixture(scope="module")
def full():
    return data.build(data.load_desk(EXAMPLES / "energy_stress.json",
                                     EXAMPLES / "energy_tail.json",
                                     EXAMPLES / "energy_book.json"))


@pytest.fixture(scope="module")
def bare():
    return data.build(data.load_desk(EXAMPLES / "energy_stress.json"))


@pytest.mark.parametrize("slug", SLUGS)
def test_every_view_is_a_whole_document(full, slug):
    document = page.render(full, slug)
    assert document.startswith("<!DOCTYPE html>")
    assert document.rstrip().endswith("</html>")
    assert "<title>Risk Desk dashboard" in document


@pytest.mark.parametrize("slug", SLUGS)
def test_every_view_states_the_sign_convention(full, slug):
    document = page.render(full, slug)
    assert SIGN_CONVENTION.split(";")[0] in document
    assert "a negative net value is a short position" in document


@pytest.mark.parametrize("slug", SLUGS)
def test_every_view_prints_the_flag_even_when_it_is_not_set(full, slug):
    """A page that mentions degradation only when degraded teaches a reader
    that silence means nothing was checked."""
    assert full["degraded"] is False
    assert ">not degraded<" in page.render(full, slug)


@pytest.mark.parametrize("slug", SLUGS)
def test_a_degraded_desk_says_so_on_every_view(slug):
    payload = data.build(data.load_desk(EXAMPLES / "energy_stress.json",
                                        EXAMPLES / "tail.json"))
    document = page.render(payload, slug)
    assert ">degraded<" in document
    assert "Fewer than 20 observations" in document


@pytest.mark.parametrize("slug", SLUGS)
def test_no_view_loads_anything_from_anywhere(full, slug):
    document = page.render(full, slug)
    assert "http://" not in document
    assert "https://" not in document
    assert "<script" not in document.lower()
    assert "<img" not in document.lower()


@pytest.mark.parametrize("slug", SLUGS)
def test_every_view_links_every_other_view(full, slug):
    """Exactly one nav entry is marked current. It may carry a second
    class as well: a view that is both current and empty is both, and the
    nav says so."""
    document = page.render(full, slug)
    for other in SLUGS:
        assert 'href="/{}"'.format(other) in document
    current = re.findall(r'<a class="([^"]*)" href="/([^"]+)"', document)
    marked = [name for classes, name in current if "here" in classes.split()]
    assert marked == [slug]


def test_the_exposure_view_draws_the_report_charts(full):
    document = page.render(full, "exposure")
    assert "Signed net exposure by asset" in document
    assert "Share of gross exposure by asset" in document
    assert 'class="bar long"' in document
    assert 'class="bar short"' in document
    assert 'class="bar share"' in document
    assert "14,100,000.00 USD" in document
    assert "1.175x" in document
    assert "4</strong> are long" in document
    assert "2</strong> are short" in document


def test_the_stress_view_draws_one_chart_for_each_scenario(full):
    document = page.render(full, "stress")
    assert document.count("<svg") == len(full["scenarios"])
    for scenario in full["scenarios"]:
        assert scenario["name"] in document


def test_the_tail_view_marks_var_and_es(full):
    document = page.render(full, "tail")
    assert "511,773.00 USD" in document
    assert "617,885.16 USD" in document
    assert 'class="mark var"' in document
    assert 'class="mark es"' in document


@pytest.mark.parametrize("slug,phrase", [
    ("exposure", "not because the exposure is zero"),
    ("tail", "not because the risk is zero"),
    ("xva", "Nothing here is zero"),
])
def test_an_absent_view_denies_being_a_zero(bare, slug, phrase):
    document = page.render(bare, slug)
    assert phrase in document
    assert 'class="absent"' in document


def test_the_absent_xva_view_prints_the_command_that_would_fill_it(bare):
    document = page.render(bare, "xva")
    assert "riskdesk xva --project" in document
    assert "did not run ORE" not in document  # it never ran, so no past tense


def test_a_loaded_xva_view_reprints_it_without_adding_rows(tmp_path):
    import json
    written = {"backend": "Open Source Risk Engine",
               "backend_version": "1.8.16.0", "backend_git_hash": "b1f2393",
               "currency": "EUR", "as_of": "2016-02-05",
               "data_mode": "upstream-example",
               "requested_xva_flags": {"cva": "Y", "mva": "N"}, "errors": [],
               "reports": {"xva": {"rows": [{"a": 1}, {"b": 2}]}},
               "assumptions": []}
    path = tmp_path / "riskdesk-xva.json"
    path.write_text(json.dumps(written), encoding="utf-8")
    payload = data.build(data.load_desk(EXAMPLES / "energy_stress.json",
                                        xva_path=path))
    document = page.render(payload, "xva")
    assert "never added together" in document
    assert "did not run ORE" in document
    assert "1.8.16.0" in document


def test_an_unknown_view_is_refused_rather_than_guessed(full):
    with pytest.raises(KeyError):
        page.render(full, "../../etc/passwd")
    document = page.not_found(full, "nonsense")
    assert "no view called" in document
    assert "reads nothing else from disk" in document


def test_a_hostile_scenario_name_cannot_inject_markup():
    import json
    payload = json.loads((EXAMPLES / "energy_stress.json").read_text(
        encoding="utf-8"))
    payload["scenarios"][0]["name"] = "<script>alert(1)</script>"
    desk = {"stress": payload, "tail": None, "exposure": None, "xva": None,
            "paths": {"stress": "x", "tail": None, "exposure": None,
                      "xva": None}}
    document = page.render(data.build(desk), "stress")
    assert "<script>alert(1)</script>" not in document
    assert "&lt;script&gt;" in document
