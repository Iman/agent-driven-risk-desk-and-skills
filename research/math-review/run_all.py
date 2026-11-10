"""Run every area of the independent numerical review and write manifest.json.

    python research/math-review/run_all.py

Exit status 1 if any check failed. The manifest records the sha256 of every reviewed module
so tests/test_governance.py can tell when the evidence no longer describes the code.
"""
from datetime import datetime, timezone
import hashlib
from importlib import import_module
from importlib.metadata import version
import json
from pathlib import Path
import platform
import subprocess
import sys

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from _review import ROOT  # noqa: E402

AREAS = ("backtest", "tail", "counterparty", "credit", "decomposition", "scenarios", "frtb", "derivatives",
         "liquidity")
# The modules under review. Plumbing (server, cli, models, design, report, summaries, ore_worker,
# dashboard) is outside model governance; tests/test_governance.py holds the same exclusion list.
REVIEWED = ("analytics", "tail_models", "backtest", "derivatives", "decomposition", "limits", "liquidity",
            "scenarios", "counterparty", "credit", "frtb", "ore")
PENDING_REHASH = {
    "analytics": "the integrator's overflow fix on feat/v0.2 changes this file; re-run this script after it lands",
    "derivatives": "the integrator is removing the Black-76 rho workaround now that Option Desk 4a282d9 fixes "
                   "black76_greeks; re-run this script after it lands"}


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def git(*args, cwd=ROOT):
    return subprocess.run(["git", *args], cwd=cwd, capture_output=True, text=True, check=True).stdout.strip()


def main():
    results = {}
    for area in AREAS:
        results[area] = import_module(f"{area}.checks").main()
        print(f"{area}: {results[area]['passed']} passed, {len(results[area]['failed'])} failed")
    option_desk = Path(import_module("optiondesk_engine").__file__).resolve().parents[3]
    manifest = dict(
        generated_utc=datetime.now(timezone.utc).isoformat(),
        command="python research/math-review/run_all.py",
        reviewed_head=git("rev-parse", "HEAD"),
        reviewed_branch=git("rev-parse", "--abbrev-ref", "HEAD"),
        uncommitted_module_changes=git("status", "--porcelain", "--", "src/riskdesk").splitlines(),
        python=platform.python_version(),
        packages={p: version(p) for p in ("numpy", "scipy", "skfolio", "scikit-learn", "pydantic")},
        option_desk=dict(path=option_desk.name, head=git("rev-parse", "HEAD", cwd=option_desk),
                         uncommitted_engine_changes=git("status", "--porcelain", "--", "engine", cwd=option_desk).splitlines()),
        module_sha256={f"src/riskdesk/{m}.py": sha256(ROOT / "src" / "riskdesk" / f"{m}.py") for m in REVIEWED},
        pending_rehash={f"src/riskdesk/{m}.py": why for m, why in PENDING_REHASH.items()},
        results_sha256={f"{a}/numerical-results.json": sha256(HERE / a / "numerical-results.json") for a in AREAS},
        totals=dict(checks=sum(len(r["checks"]) for r in results.values()),
                    failed=[f"{a}/{c}" for a, r in results.items() for c in r["failed"]]),
        checks=[dict(area=a, id=c["id"], what=c["what"], source=c["source"], compared=c["compared"],
                     abs_tol=c["abs_tol"], rel_tol=c["rel_tol"], passed=c["passed"])
                for a, r in results.items() for c in r["checks"]])
    (HERE / "manifest.json").write_text(json.dumps(manifest, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    print(f"total: {manifest['totals']['checks']} checks, {len(manifest['totals']['failed'])} failed")
    return 1 if manifest["totals"]["failed"] else 0


if __name__ == "__main__":
    sys.exit(main())
