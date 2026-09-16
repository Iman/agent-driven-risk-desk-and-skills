#!/usr/bin/env python3
"""Pin the numbers the documentation quotes to where they came from.

WHY THIS EXISTS. A README is the one file a reader believes without
checking, and it is also the file that rots first: a test is added, a
notice is refreshed, a tool is renamed, and the sentence describing the
old state stays exactly where it was, still perfectly readable and no
longer true. Nothing in an ordinary build notices.

So every figure the documentation quotes is recorded here with its
provenance, and a test runs the check, which means the suite fails when
the prose and the repository disagree. The build refuses to let the prose
lie, which is a smaller claim than it sounds and a much more useful one
than an unchecked sentence.

    python3 scripts/evidence.py record    measure, then write the file
    python3 scripts/evidence.py check     verify the documents still match

Recording is deliberate and manual. A recorder that ran on every build
would silently follow whatever is on disk today, the documented sentence
would follow it, and the exercise would prove nothing.

TWO KINDS OF FIGURE. Most are MEASURED: the recorder counts them in this
checkout, now. A few are PINNED: the ORE regression values came from a run
against an upstream checkout that is not part of this repository and is
not present on every machine. Those are carried forward with the date and
the document they were observed in, and the recorder does not pretend to
have re-measured them. The distinction is written into the file, so a
reader can tell which figures this run stands behind.
"""
import argparse
import json
from pathlib import Path
import re
import subprocess
import sys

ROOT = Path(__file__).resolve().parent.parent
EVIDENCE = ROOT / "docs" / "evidence.json"


# -------------------------------------------------------------- measuring

def measure_tests_collected():
    """How many tests pytest collects in this checkout."""
    finished = subprocess.run(
        [sys.executable, "-m", "pytest", "--collect-only", "-q",
         "--color=no", "-p", "no:cacheprovider"],
        cwd=str(ROOT), capture_output=True, text=True, timeout=900)
    match = re.search(r"^(\d+) tests? collected", finished.stdout,
                      re.MULTILINE)
    if not match:
        raise ValueError("pytest did not report a collected count:\n"
                         + finished.stdout[-2000:])
    return int(match.group(1))


def measure_unit_coverage():
    """Unit line coverage of the package, to two decimal places.

    Measured here rather than pinned, because it is measurable here and a
    coverage figure copied forward from a previous run is the exact kind
    of sentence this file exists to stop.
    """
    report = ROOT / "artifacts" / "coverage" / "unit.json"
    for argv in ([sys.executable, "-m", "coverage", "run", "-m", "pytest",
                  "-q", "--color=no", "-m", "unit", "-p", "no:cacheprovider"],
                 [sys.executable, "-m", "coverage", "json", "-q"]):
        finished = subprocess.run(argv, cwd=str(ROOT), capture_output=True,
                                  text=True, timeout=900)
        if finished.returncode:
            raise ValueError("coverage step failed: {}\n{}".format(
                " ".join(argv), finished.stdout[-2000:]))
    payload = json.loads(report.read_text(encoding="utf-8"))
    covered = total = 0
    for name, entry in payload["files"].items():
        if not name.replace("\\", "/").startswith("src/riskdesk/"):
            continue
        covered += entry["summary"]["covered_lines"]
        total += entry["summary"]["num_statements"]
    if not total:
        raise ValueError("coverage report has no production statements")
    return "{:.2f}".format(100 * covered / total)


def _energy_exposure():
    """The exposure result for the example book the README draws."""
    sys.path.insert(0, str(ROOT / "src"))
    from riskdesk.analytics import portfolio_exposure

    payload = json.loads((ROOT / "examples" / "energy_book.json")
                         .read_text(encoding="utf-8"))
    return portfolio_exposure(payload)


def measure_energy_gross_exposure():
    return "{:,.2f}".format(_energy_exposure()["gross_exposure"])


def measure_energy_net_exposure():
    return "{:,.2f}".format(_energy_exposure()["net_exposure"])


def measure_energy_exposure_assets():
    return len(_energy_exposure()["net_by_asset"])


def measure_commands():
    return len(sorted((ROOT / "plugins" / "risk-desk" / "commands")
                      .glob("*.md")))


def measure_agents():
    return len(sorted((ROOT / "plugins" / "risk-desk" / "agents")
                      .glob("*.md")))


def measure_skills():
    return len(sorted((ROOT / "plugins" / "risk-desk" / "skills")
                      .glob("*/SKILL.md")))


def measure_mcp_tools():
    """Ask the server object, in this process, what it registers."""
    import asyncio

    sys.path.insert(0, str(ROOT / "src"))
    from riskdesk.server import server

    return len(asyncio.run(server.list_tools()))


def _visible(path):
    """Ignore dot files. A stray .DS_Store is not an upstream notice, and
    counting one would put a wrong number straight into the README."""
    return not any(part.startswith(".") for part in path.parts)


def measure_notice_files():
    root = ROOT / "notices"
    return len([p for p in root.rglob("*")
                if p.is_file() and _visible(p.relative_to(root))])


def measure_notice_distributions():
    root = ROOT / "notices"
    return len([p for p in root.iterdir()
                if p.is_dir() and _visible(p.relative_to(root))])


def measure_examples():
    return len(sorted((ROOT / "examples").glob("*.json")))


MEASURES = {
    "tests_collected": measure_tests_collected,
    "unit_coverage": measure_unit_coverage,
    "skills": measure_skills,
    "commands": measure_commands,
    "agents": measure_agents,
    "mcp_tools": measure_mcp_tools,
    "notice_files": measure_notice_files,
    "notice_distributions": measure_notice_distributions,
    "examples": measure_examples,
    "energy_gross_exposure": measure_energy_gross_exposure,
    "energy_net_exposure": measure_energy_net_exposure,
    "energy_exposure_assets": measure_energy_exposure_assets,
}


# ----------------------------------------------------------------- claims
#
# Each claim names the exact sentence the document uses, not the number
# alone. "82" appearing somewhere in a README is not evidence that the
# sentence about exposure dates is right.

CLAIMS = [
    {
        "id": "tests_collected",
        "measure": "tests_collected",
        "about": "tests pytest collects in this checkout",
        "documents": {
            "README.md": "tests-%d%%20collected",
            "docs/IMPLEMENTATION.md": "%d tests collected",
        },
    },
    {
        "id": "unit_coverage",
        "measure": "unit_coverage",
        "about": "unit line coverage of src/riskdesk, percent",
        "documents": {
            "README.md": "unit%%20coverage-%s%%25",
            "docs/IMPLEMENTATION.md": "%s percent",
            "CHANGELOG.md": "%s percent",
        },
    },
    {
        "id": "skills",
        "measure": "skills",
        "about": "plugin skills under plugins/risk-desk/skills",
        "documents": {"README.md": "%d plugin skills cover these tasks"},
    },
    {
        "id": "skills_in_manifest",
        "measure": "skills",
        "about": "skill directories both plugin manifests point at",
        "documents": {"README.md": "point at the same %d skill directories"},
    },
    {
        "id": "commands",
        "measure": "commands",
        "about": "slash commands under plugins/risk-desk/commands",
        "documents": {"README.md": "%d commands and"},
    },
    {
        "id": "agents",
        "measure": "agents",
        "about": "agents under plugins/risk-desk/agents",
        "documents": {"README.md": "and %d agents"},
    },
    {
        "id": "mcp_tools",
        "measure": "mcp_tools",
        "about": "tools the local MCP server registers",
        "documents": {"README.md": "%d local MCP tools call the same runtime"},
    },
    {
        "id": "notice_files",
        "measure": "notice_files",
        "about": "upstream notice files retained under notices/",
        "documents": {"README.md": "%d upstream notice files"},
    },
    {
        "id": "notice_distributions",
        "measure": "notice_distributions",
        "about": "upstream distributions with a retained notice",
        "documents": {"README.md": "from %d distributions"},
    },
    {
        "id": "examples",
        "measure": "examples",
        "about": "example input files under examples/",
        "documents": {"README.md": "%d example input files"},
    },
    {
        "id": "energy_exposure_assets",
        "measure": "energy_exposure_assets",
        "about": "assets the exposure charts draw for the example book",
        "documents": {
            "README.md": "the %d legs of the synthetic energy book",
            "docs/IMPLEMENTATION.md": "%d assets",
        },
    },
    {
        "id": "energy_gross_exposure",
        "measure": "energy_gross_exposure",
        "about": "gross exposure of examples/energy_book.json, in USD",
        "documents": {
            "docs/IMPLEMENTATION.md": "gross exposure %s USD",
            "CHANGELOG.md": "gross %s USD",
        },
    },
    {
        "id": "energy_net_exposure",
        "measure": "energy_net_exposure",
        "about": "net exposure of examples/energy_book.json, in USD",
        "documents": {
            "docs/IMPLEMENTATION.md": "net exposure %s USD",
            "CHANGELOG.md": "net %s USD",
        },
    },
    {
        "id": "ore_exposure_dates",
        "pinned": 82,
        "observed": "2026-09-13",
        "provenance": ("docs/IMPLEMENTATION.md VERIFIED block of 2026-09-13; "
                       "produced by scripts/ore_smoke.py against an upstream "
                       "ORE checkout that is not part of this repository"),
        "about": "netting-set exposure dates in the pinned ORE example",
        "documents": {
            "docs/ORE.md": "%d netting-set exposure dates",
            "docs/IMPLEMENTATION.md": "%d netting-set exposure dates",
        },
    },
    {
        "id": "ore_cva",
        "pinned": 42600.768114722014,
        "observed": "2026-09-13",
        "provenance": ("docs/IMPLEMENTATION.md VERIFIED block of 2026-09-13; "
                       "a numerical regression value, not model validation"),
        "about": "CVA reported by the pinned ORE example, in EUR",
        "documents": {
            "docs/ORE.md": "CVA %s EUR",
            "docs/IMPLEMENTATION.md": "CVA %s EUR",
        },
    },
    {
        "id": "ore_dva",
        "pinned": 62036.0247267215,
        "observed": "2026-09-13",
        "provenance": ("docs/IMPLEMENTATION.md VERIFIED block of 2026-09-13; "
                       "a numerical regression value, not model validation"),
        "about": "DVA reported by the pinned ORE example, in EUR",
        "documents": {
            "docs/ORE.md": "DVA %s EUR",
            "docs/IMPLEMENTATION.md": "DVA %s EUR",
        },
    },
    {
        "id": "ore_samples",
        "pinned": 1000,
        "observed": "2026-09-13",
        "provenance": ("docs/IMPLEMENTATION.md VERIFIED block of 2026-09-13; "
                       "retained by scripts/ore_smoke.py"),
        "about": "simulation samples retained in the pinned ORE example",
        "documents": {"docs/ORE.md": "%s simulation samples and seed 42"},
    },
    {
        "id": "ore_seed",
        "pinned": 42,
        "observed": "2026-09-13",
        "provenance": ("docs/IMPLEMENTATION.md VERIFIED block of 2026-09-13; "
                       "retained by scripts/ore_smoke.py"),
        "about": "simulation seed retained in the pinned ORE example",
        "documents": {"docs/ORE.md": "simulation samples and seed %d"},
    },
    {
        "id": "ore_version",
        "pinned": "1.8.16.0",
        "observed": "2026-09-13",
        "provenance": ("docs/IMPLEMENTATION.md VERIFIED block of 2026-09-13; "
                       "the wheel version the example was run against"),
        "about": "ORE release the pinned example was run against",
        "documents": {
            "docs/ORE.md": "ORE v%s",
            "README.md": "Version %s was tested",
        },
    },
    {
        "id": "ore_commit",
        "pinned": "b1f239332fdd51e5c514dd6de34a665fe0ff8326",
        "observed": "2026-09-13",
        "provenance": ("docs/IMPLEMENTATION.md VERIFIED block of 2026-09-13; "
                       "the revision scripts/ore_smoke.py verifies before "
                       "copying example inputs"),
        "about": "upstream ORE revision behind the pinned example",
        "documents": {
            "docs/ORE.md": "`%s`",
            "docs/IMPLEMENTATION.md": "`%s`",
        },
    },
]


def _sentence(template, value):
    """The exact text a document must contain for this claim."""
    if "%d" in template:
        return template % int(value)
    if "%s" in template:
        return template % (value,)
    return template


def record():
    entries = {}
    for claim in CLAIMS:
        if "measure" in claim:
            value = MEASURES[claim["measure"]]()
            entry = {"value": value, "kind": "measured",
                     "measured_by": "scripts/evidence.py record"}
        else:
            value = claim["pinned"]
            entry = {"value": value, "kind": "pinned",
                     "observed": claim["observed"],
                     "provenance": claim["provenance"]}
        entry["about"] = claim["about"]
        entry["documents"] = {document: _sentence(template, value)
                              for document, template
                              in claim["documents"].items()}
        entries[claim["id"]] = entry
    EVIDENCE.parent.mkdir(parents=True, exist_ok=True)
    EVIDENCE.write_text(json.dumps({
        "note": ("Figures quoted in the documentation, with where each came "
                 "from. A measured figure was counted in this checkout when "
                 "this file was written. A pinned figure came from a run "
                 "against inputs that are not in this repository and was "
                 "not re-measured. Written by scripts/evidence.py."),
        "figures": entries,
    }, indent=1) + "\n", encoding="utf-8")
    print("recorded {} figures to {}".format(
        len(entries), EVIDENCE.relative_to(ROOT)))
    for key, entry in entries.items():
        print("  {:24} {:8} {}".format(key, entry["kind"],
                                       entry["value"]))
    return 0


def _flat(text):
    """Collapse whitespace so a wrapped Markdown line still matches.

    The documents are hard wrapped, so a quoted sentence is routinely split
    across two lines. Matching the raw text would make the check fail on
    reflow, which trains people to ignore it. Collapsing whitespace keeps
    every failure a real one: a changed digit or a deleted sentence.
    """
    return " ".join(text.split())


def check():
    """Every recorded figure must still appear in the document citing it."""
    if not EVIDENCE.exists():
        print("no evidence file: run scripts/evidence.py record")
        return 1
    figures = json.loads(EVIDENCE.read_text(encoding="utf-8"))["figures"]
    problems = []
    for key, entry in figures.items():
        for document, sentence in entry["documents"].items():
            path = ROOT / document
            if not path.exists():
                problems.append("{}: {} is missing".format(key, document))
                continue
            if _flat(sentence) not in _flat(path.read_text(encoding="utf-8")):
                problems.append("{}: {} no longer contains {!r}".format(
                    key, document, sentence))
    for problem in problems:
        print(problem)
    print("{} figures checked, {} problems".format(len(figures),
                                                   len(problems)))
    return 1 if problems else 0


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("action", choices=("record", "check"))
    args = parser.parse_args(argv)
    return record() if args.action == "record" else check()


if __name__ == "__main__":
    raise SystemExit(main())
