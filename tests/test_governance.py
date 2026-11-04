"""Model governance gate, and proof that it can fail.

Every model module under src/riskdesk has a row in docs/models/INVENTORY.md, and the independent
review in research/math-review describes the exact bytes of the modules it reviewed. When a
reviewed module changes, re-run `python research/math-review/run_all.py` and commit its outputs.
"""
import hashlib
import json
from pathlib import Path
import re
import shutil

import pytest

ROOT = Path(__file__).resolve().parent.parent
INVENTORY = "docs/models/INVENTORY.md"
MANIFEST = "research/math-review/manifest.json"
# Plumbing, not models; research/math-review/run_all.py holds the same exclusion.
PLUMBING = {"__init__", "server", "cli", "models", "design", "report", "summaries", "ore_worker", "dashboard"}

pytestmark = pytest.mark.validation


def inventory_gaps(root):
    """Model modules with no row in the inventory's summary table."""
    rows = [line for line in (root / INVENTORY).read_text(encoding="utf-8").splitlines()
            if re.match(r"\| M\d+ \|", line)]
    listed = {name for line in rows for name in re.findall(r"src/riskdesk/(\w+)\.py", line)}
    modules = {path.stem for path in (root / "src" / "riskdesk").glob("*.py")} - PLUMBING
    return sorted(modules - listed)


def stale_hashes(root):
    """Reviewed files whose bytes no longer match the review manifest."""
    recorded = json.loads((root / MANIFEST).read_text(encoding="utf-8"))["module_sha256"]
    return sorted(path for path, digest in recorded.items()
                  if not (root / path).is_file() or hashlib.sha256((root / path).read_bytes()).hexdigest() != digest)


def test_every_model_module_has_an_inventory_row():
    assert inventory_gaps(ROOT) == [], "add a row for each module to the summary table in " + INVENTORY


def test_the_review_evidence_is_for_the_current_code():
    assert stale_hashes(ROOT) == [], "re-run python research/math-review/run_all.py and commit its outputs"


def test_both_gates_fail_on_drift(tmp_path):
    shutil.copytree(ROOT / "src" / "riskdesk", tmp_path / "src" / "riskdesk",
                    ignore=shutil.ignore_patterns("__pycache__", "dashboard"))
    for name in (INVENTORY, MANIFEST):
        (tmp_path / name).parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(ROOT / name, tmp_path / name)
    assert inventory_gaps(tmp_path) == [] and stale_hashes(tmp_path) == []
    (tmp_path / "src" / "riskdesk" / "new_model.py").write_text("", encoding="utf-8")
    with (tmp_path / "src" / "riskdesk" / "limits.py").open("a", encoding="utf-8") as handle:
        handle.write("\n")
    assert inventory_gaps(tmp_path) == ["new_model"]
    assert stale_hashes(tmp_path) == ["src/riskdesk/limits.py"]
