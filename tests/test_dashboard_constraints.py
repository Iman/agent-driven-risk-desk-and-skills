"""Repository rules the dashboard has to keep, checked rather than trusted.

Two of them were conditions on the work being done at all: no new
dependency, and no second charting path. Both are the kind of thing that
holds on the day and erodes later, so they are enforced here.
"""
import ast
from pathlib import Path
import sys

import pytest

ROOT = Path(__file__).resolve().parent.parent
DASHBOARD = ROOT / "src" / "riskdesk" / "dashboard"

pytestmark = pytest.mark.validation


def imported_roots(path):
    tree = ast.parse(path.read_text(encoding="utf-8"))
    roots = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            roots.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
            roots.add(node.module.split(".")[0])
    return roots


def test_the_dashboard_adds_no_dependency():
    """The whole thing is standard library plus this package. A plotting
    library would have meant a notices change, a lock change and a bigger
    wheel, and it was ruled out before any of this was written."""
    allowed = set(sys.stdlib_module_names) | {"riskdesk"}
    for path in sorted(DASHBOARD.glob("*.py")):
        outside = imported_roots(path) - allowed
        assert not outside, "{} imports {}".format(path.name,
                                                   sorted(outside))


def test_the_dashboard_draws_no_chart_of_its_own():
    """One charting path. A fix to a sign or an axis has to reach the saved
    report page and the served page together, which it cannot do if the
    dashboard grows its own SVG."""
    charts = {"net_by_asset_svg", "gross_share_svg", "contribution_svg",
              "tail_svg"}
    page = (DASHBOARD / "page.py").read_text(encoding="utf-8")
    for name in charts:
        assert "def " + name not in page, name + " is redefined in the page"
    assert "from riskdesk.report import" in page
    for path in sorted(DASHBOARD.glob("*.py")):
        body = path.read_text(encoding="utf-8")
        assert "<svg" not in body, "{} builds an svg".format(path.name)


def test_the_dashboard_never_reaches_the_network():
    for path in sorted(DASHBOARD.glob("*.py")):
        body = path.read_text(encoding="utf-8")
        for forbidden in ("urllib.request", "httpx", "requests.get",
                          "socket.create_connection", "http.client"):
            assert forbidden not in body, "{}: {}".format(path.name,
                                                          forbidden)


def test_the_module_split_matches_the_one_it_was_asked_to_follow():
    names = sorted(p.name for p in DASHBOARD.glob("*.py"))
    assert names == ["__init__.py", "app.py", "data.py", "maths.py",
                     "page.py", "server.py"]


def test_every_dashboard_test_file_declares_which_kind_it_is():
    """A test that binds a socket and is collected as unit would hide the
    split rather than keep it."""
    for path in sorted(ROOT.glob("tests/test_dashboard_*.py")):
        body = path.read_text(encoding="utf-8")
        assert ("pytestmark = pytest.mark." in body
                or "@pytest.mark.unit" in body), path.name
    assert (ROOT / "tests" / "test_dashboard_server.py").exists()


SOCKET_ROOTS = {"socket", "socketserver", "urllib", "http", "asyncio"}


def _module_marker(tree):
    for node in tree.body:
        if isinstance(node, ast.Assign) and any(
                getattr(target, "id", None) == "pytestmark"
                for target in node.targets):
            return ast.unparse(node.value)
    return ""


def _marked_unit(function):
    return any("mark.unit" in ast.unparse(d) for d in function.decorator_list)


def _names_used(node):
    used = set()
    for child in ast.walk(node):
        if isinstance(child, ast.Name):
            used.add(child.id)
        elif isinstance(child, ast.Attribute):
            used.add(child.attr)
    return used


def test_no_unit_test_can_reach_a_socket():
    """Checked from the syntax tree, not from the text.

    An earlier version of this test matched the word "socket" anywhere in
    the file and failed on a docstring that said "no socket", which is a
    test of prose rather than of behaviour. Imports and names are what a
    test actually uses.
    """
    offenders = []
    for path in sorted(ROOT.glob("tests/test_*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        roots = imported_roots(path)
        module_unit = "mark.unit" in _module_marker(tree)
        if module_unit and roots & SOCKET_ROOTS:
            offenders.append("{}: module is unit and imports {}".format(
                path.name, sorted(roots & SOCKET_ROOTS)))
        for node in ast.walk(tree):
            if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            if not (_marked_unit(node) or (module_unit
                                           and node.name.startswith("test_"))):
                continue
            reached = _names_used(node) & SOCKET_ROOTS
            if reached:
                offenders.append("{}::{} uses {}".format(
                    path.name, node.name, sorted(reached)))
    assert not offenders, "unit tests must not bind a socket: " + \
        "; ".join(offenders)


def test_the_socket_tests_are_marked_so_ci_runs_them():
    """Marked integration, and integration is not deselected anywhere in
    the workflow, so they run rather than skipping into invisibility."""
    server_tests = ROOT / "tests" / "test_dashboard_server.py"
    tree = ast.parse(server_tests.read_text(encoding="utf-8"))
    assert "mark.integration" in _module_marker(tree)
    workflow = (ROOT / ".github" / "workflows"
                / "tests.yml").read_text(encoding="utf-8")
    assert "not docker" in workflow
    assert "not integration" not in workflow
