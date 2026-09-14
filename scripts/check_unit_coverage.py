"""Check unit line coverage for the production package.

The gate is on the unit suite alone, not the whole run. Integration tests
drive real processes and a real stdio transport, so they light up lines
they never assert anything about, and a gate that counted them would
report a number that means very little.

Every production file must appear in the report. A file that is simply
absent from a coverage run looks like nothing rather than like zero, and
the aggregate would then pass by ignoring it.

    python -m coverage run --source=src/riskdesk -m pytest -m unit -q
    python -m coverage json -o artifacts/coverage/unit.json
    python scripts/check_unit_coverage.py artifacts/coverage/unit.json
"""
import argparse
import json
from pathlib import Path

PACKAGE = "src/riskdesk"
ROOT = Path(__file__).resolve().parents[1]
MINIMUM = 80


def _rows(report):
    files = report.get("files")
    if not isinstance(files, dict) or not files:
        raise ValueError("coverage report has no files")
    rows = []
    for name, entry in sorted(files.items()):
        summary = entry["summary"]
        covered, total = summary["covered_lines"], summary["num_statements"]
        if not (isinstance(covered, int) and isinstance(total, int)
                and 0 <= covered <= total):
            raise ValueError("invalid line counts for " + name)
        rows.append(dict(name=name.replace("\\", "/"), covered=covered,
                         total=total))
    return rows


def assess(report, minimum=MINIMUM):
    rows = [row for row in _rows(report)
            if row["name"].startswith(PACKAGE + "/")]
    if not rows:
        raise ValueError("coverage report has no production files for "
                         + PACKAGE)
    covered = sum(row["covered"] for row in rows)
    total = sum(row["total"] for row in rows)
    if not total:
        raise ValueError("coverage report has no statements for " + PACKAGE)
    return rows, dict(package=PACKAGE, covered=covered, total=total,
                      percent=100 * covered / total,
                      passed=100 * covered >= minimum * total)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("report", type=Path)
    parser.add_argument("--minimum", type=int, default=MINIMUM)
    args = parser.parse_args(argv)
    try:
        payload = json.loads(args.report.read_text(encoding="utf-8"))
        expected = {path.relative_to(ROOT).as_posix()
                    for path in (ROOT / PACKAGE).rglob("*.py")}
        missing = expected - set(payload.get("files", {}))
        if missing:
            raise ValueError("production files missing from coverage: "
                             + ", ".join(sorted(missing)))
        rows, total = assess(payload, args.minimum)
    except (OSError, ValueError, KeyError, TypeError) as exc:
        print("Coverage gate failed: " + str(exc))
        return 1
    for row in rows:
        print("  {name}: {covered}/{total} lines, {percent:.2f}%".format(
            percent=100 * row["covered"] / row["total"] if row["total"]
            else 100.0, **row))
    print("{package}: {covered}/{total} lines, {percent:.2f}% ({verdict}, "
          "minimum {minimum}%)".format(
              verdict="PASS" if total["passed"] else "FAIL",
              minimum=args.minimum, **total))
    return 0 if total["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
