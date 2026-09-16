"""The root documents, checked against the repository they describe.

A document is the part of a project nobody runs, so it is the part that
rots first. These are the three failures worth catching mechanically: a
link to a file that does not exist, a document promising a capability the
code does not have, and four files disagreeing about the licence.

The options vocabulary check exists because these documents were adapted
from a sibling project whose scope is listed options. A sentence about
Greeks or an expiry surviving the adaptation would describe a capability
this repository refuses to have, which is worse than a typo.
"""
import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
LICENCE_ID = "PolyForm-Noncommercial-1.0.0"
LICENCE_NAME = "PolyForm Noncommercial License 1.0.0"

# Words from the sibling project's scope. None of these is in this
# project's contract, and the models refuse the instruments they name.
OPTIONS_VOCABULARY = ("greek", "iron condor", "straddle", "strangle",
                      "open interest", "volatility surface", "moneyness",
                      "option chain", "expiry", "max pain")

# A line containing one of these is denying a capability, not claiming it.
DENIALS = ("no ", "not ", "cannot", "refus", "outside this", "do not",
           "does not", "separate calculation")

pytestmark = pytest.mark.validation


def documents():
    return sorted(p for p in ROOT.glob("*.md"))


def text(path):
    return path.read_text(encoding="utf-8")


def test_every_local_link_in_every_document_resolves():
    """A link to a file that is not there is the cheapest possible defect
    and the one a reader hits first."""
    broken = []
    for path in documents() + [ROOT / "docs" / "IMPLEMENTATION.md"]:
        for target in re.findall(r"\]\(([^)#][^)]*)\)", text(path)):
            if target.startswith(("http://", "https://", "mailto:")):
                continue
            resolved = (path.parent / target.split("#")[0]).resolve()
            if not resolved.exists():
                broken.append("{} -> {}".format(path.name, target))
    assert not broken, "broken links: " + ", ".join(broken)


def test_the_readme_links_the_documents_a_reader_needs():
    readme = text(ROOT / "README.md")
    for name in ("LICENSE", "LICENSES.md", "DISCLAIMER.md", "PRIVACY.md",
                 "SECURITY.md", "CONTRIBUTING.md", "INSTALL.md", "FAQ.md",
                 "THIRD-PARTY.md", "CHANGELOG.md"):
        assert name in readme, "README does not point at " + name


def test_no_document_carries_the_sibling_projects_scope():
    """These were adapted from a listed-options project. A surviving
    sentence about Greeks would promise something the models refuse."""
    offenders = []
    for path in documents():
        if path.name == Path(__file__).name:
            continue
        for line in text(path).lower().splitlines():
            if any(deny in line for deny in DENIALS):
                # "No Greeks" is the opposite of the failure this looks
                # for. The test is for a sentence PROMISING an options
                # capability, and a denial is the project stating its
                # scope, which these documents are supposed to do.
                continue
            for word in OPTIONS_VOCABULARY:
                if word in line:
                    offenders.append("{}: {}".format(path.name, word))
    assert not offenders, "options vocabulary survived: " + \
        ", ".join(offenders)


def test_no_document_claims_this_software_fetches_market_data():
    """It fetches none. There is no provider, no key and no account, and
    that is the strongest privacy claim the project makes."""
    for path in documents():
        body = text(path).lower()
        for claim in ("fetches market data", "market data provider",
                      "provider api key", "downloads prices"):
            assert claim not in body, "{}: {}".format(path.name, claim)


def cli_commands():
    source = (ROOT / "src" / "riskdesk" / "cli.py").read_text(
        encoding="utf-8")
    named = set(re.findall(r'commands\.add_parser\("([a-z]+)"', source))
    handlers = set(re.findall(r'"([a-z]+)": \w+', source.split(
        "HANDLERS = {")[1].split("}")[0]))
    return named | handlers


def test_every_riskdesk_command_a_document_names_exists():
    """A documented command that the CLI does not have is a promise the
    first reader to try it discovers is false."""
    real = cli_commands()
    assert {"tail", "exposure", "stress", "report", "xva",
            "dashboard"} <= real, real
    invented = []
    for path in documents() + [ROOT / "docs" / "OPENAI.md"]:
        # Only where the document is showing a command: inside a fenced
        # block or an inline code span. Prose about "every riskdesk
        # command" is English, not an invocation, and an earlier version
        # of this test flagged exactly that sentence in CHANGELOG.md.
        body = text(path)
        code = "\n".join(re.findall(r"```[a-z]*\n(.*?)```", body, re.S))
        code += "\n" + "\n".join(re.findall(r"`([^`\n]+)`", body))
        for name in re.findall(r"\briskdesk ([a-z]+)", code):
            if name in real:
                continue
            invented.append("{}: riskdesk {}".format(path.name, name))
    assert not invented, "documented commands that do not exist: " + \
        ", ".join(invented)


def test_the_licence_is_the_same_one_in_every_place_it_is_stated():
    """Four files and a directory have to agree, or a reader picks the
    statement that suits them."""
    assert LICENCE_NAME in text(ROOT / "LICENSE")
    licences = text(ROOT / "LICENSES.md")
    assert LICENCE_NAME in licences
    assert LICENCE_ID in (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    for name in ("THIRD-PARTY.md", "DISCLAIMER.md", "CLA.md", "README.md"):
        assert "PolyForm Noncommercial" in text(ROOT / name), name
    for runtime in (".claude-plugin", ".codex-plugin"):
        manifest = (ROOT / "plugins" / "risk-desk" / runtime /
                    "plugin.json").read_text(encoding="utf-8")
        assert LICENCE_ID in manifest, runtime


def test_the_licence_documents_agree_about_the_upstream_counts():
    """LICENSES.md and THIRD-PARTY.md both quote the notice counts. They
    must agree with each other and with the directory on disk."""
    notices = ROOT / "notices"
    distributions = len([p for p in notices.iterdir()
                         if p.is_dir() and not p.name.startswith(".")])
    files = len([p for p in notices.rglob("*")
                 if p.is_file()
                 and not any(part.startswith(".")
                             for part in p.relative_to(notices).parts)])
    for name in ("LICENSES.md", "THIRD-PARTY.md"):
        body = text(ROOT / name)
        assert str(distributions) in body, "{} does not quote {}".format(
            name, distributions)
        assert str(files) in body, "{} does not quote {}".format(name, files)


def test_every_dependency_licence_named_was_checked_against_its_notice():
    """LICENSES.md names four. Each one has to match the notice file that
    actually ships, not a package index."""
    expected = {"skfolio": "BSD 3-Clause", "mcp": "MIT License",
                "pydantic": "The MIT License"}
    for package, opening in expected.items():
        directory = ROOT / "notices" / package
        assert directory.is_dir(), package
        notice = sorted(directory.glob("*"))[0].read_text(
            encoding="utf-8", errors="replace")
        assert opening in notice[:200], "{}: notice does not open {!r}".format(
            package, opening)
    ore = sorted((ROOT / "notices" / "open-source-risk-engine").glob("*"))[0]
    body = ore.read_text(encoding="utf-8", errors="replace")
    assert "Quaternion Risk Management" in body
    assert "Acadia" in body
    assert "Quaternion" in text(ROOT / "LICENSES.md")


def test_the_disclaimer_and_privacy_say_no_order_is_placed():
    """The two sentences a regulated reader looks for first."""
    assert "places no orders" in text(ROOT / "README.md") \
        or "no order is placed" in text(ROOT / "README.md").lower()
    # Checked against what the document says, not against a phrase this
    # test guessed at. An earlier version of this line asserted "no
    # order" and failed on a document that says it more precisely.
    disclaimer = text(ROOT / "DISCLAIMER.md").lower()
    assert "places, routes or executes an order" in disclaimer
    assert "no order is placed by this tool" in text(
        ROOT / "src" / "riskdesk" / "report.py").lower()
    privacy = text(ROOT / "PRIVACY.md")
    assert "makes no outbound request" in privacy
    assert "riskdesk.avidquant.com" in privacy


def test_no_document_names_an_assistant_as_an_author():
    """Commits carry one identity and so do the documents."""
    for path in documents():
        if path.name == Path(__file__).name:
            continue
        body = text(path).lower()
        for name in ("co-authored-by", "generated with", "@anthropic.com"):
            assert name not in body, "{}: {}".format(path.name, name)
    contributors = text(ROOT / "CONTRIBUTORS.md")
    assert contributors.count("-") >= 1
    assert "Iman Samizadeh" in contributors
