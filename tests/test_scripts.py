"""install.sh and demo.sh, the two commands the README tells people to run.

demo.sh is run for real here, because it only reads files in examples/ and
takes a second. install.sh is not run to completion, because a complete run
downloads a dependency tree from the network, and a test that needs the
network is a test that reports the network. What is checked instead is
everything that can go wrong without it: the shell parses it, its option
handling is right, it refuses an unusable interpreter, and it prints no
colour. The complete clean-clone run is a release step, recorded in
docs/IMPLEMENTATION.md with the date it was observed.
"""
import os
from pathlib import Path
import shutil
import subprocess

import pytest

ROOT = Path(__file__).resolve().parent.parent
INSTALL = ROOT / "install.sh"
DEMO = ROOT / "demo.sh"
ESCAPE = "\x1b"

pytestmark = pytest.mark.integration


def sh(*argv, **kwargs):
    return subprocess.run(list(argv), capture_output=True, text=True,
                          cwd=str(ROOT), timeout=600, **kwargs)


@pytest.mark.parametrize("script", [INSTALL, DEMO])
def test_the_scripts_are_executable_posix_sh(script):
    assert os.access(script, os.X_OK), "{} is not executable".format(
        script.name)
    assert script.read_text(encoding="utf-8").startswith("#!/bin/sh\n")
    assert sh("/bin/sh", "-n", str(script)).returncode == 0


@pytest.mark.parametrize("script", [INSTALL, DEMO])
def test_the_scripts_emit_no_escape_codes(script):
    assert ESCAPE not in script.read_text(encoding="utf-8")


def test_install_help_exits_zero_and_describes_the_optional_extra():
    finished = sh("/bin/sh", str(INSTALL), "--help")
    assert finished.returncode == 0
    assert "--no-xva" in finished.stdout
    assert ESCAPE not in finished.stdout


def test_install_refuses_an_unknown_option():
    finished = sh("/bin/sh", str(INSTALL), "--make-it-fast")
    assert finished.returncode == 2
    assert "unknown option" in finished.stderr


def test_install_refuses_an_interpreter_it_cannot_use(tmp_path):
    """An installer that accepts any --python builds an environment that
    fails later, somewhere less obvious."""
    fake = tmp_path / "python"
    fake.write_text("#!/bin/sh\nexit 1\n")
    fake.chmod(0o755)
    finished = sh("/bin/sh", str(INSTALL), "--python", str(fake))
    assert finished.returncode != 0
    assert "3.11 or later" in finished.stderr


def test_install_stops_rather_than_reporting_success_without_an_environment(
        tmp_path):
    finished = sh("/bin/sh", str(INSTALL), "--venv", str(tmp_path / "nope"),
                  "--python", "/bin/false")
    assert finished.returncode != 0
    assert "Done" not in finished.stdout


def test_demo_refuses_to_run_with_no_riskdesk_anywhere(tmp_path):
    empty = tmp_path / "bin"
    empty.mkdir()
    finished = sh("/bin/sh", str(DEMO),
                  env={"PATH": str(empty), "HOME": str(tmp_path),
                       "RISKDESK_VENV": str(tmp_path / "absent")})
    assert finished.returncode == 1
    assert "Run ./install.sh first" in finished.stderr


@pytest.mark.skipif(not (ROOT / ".venv" / "bin" / "riskdesk").exists()
                    and shutil.which("riskdesk") is None,
                    reason="riskdesk is not installed in this environment")
def test_demo_runs_every_command_and_states_the_conventions(tmp_path):
    finished = sh("/bin/sh", str(DEMO),
                  env=dict(os.environ, RISKDESK_ARTIFACTS=str(tmp_path)))
    assert finished.returncode == 0, finished.stdout + finished.stderr
    out = finished.stdout
    assert ESCAPE not in out
    for expected in ("historical VaR and Expected Shortfall via skfolio",
                     "signed base-currency linear position exposure",
                     "linear full-position scenario revaluation",
                     "loss is positive",
                     "worst three positions by P&L",
                     "4 MCP tools",
                     "risk_tail", "risk_exposure", "risk_stress", "risk_xva",
                     "WTI_CRUDE_FUTURE",
                     "european_gas_supply_dislocation_shape",
                     "carries no probability and is not a forecast"):
        assert expected in out, expected
    page = tmp_path / "report.html"
    assert page.exists() and page.stat().st_size > 2000


@pytest.mark.skipif(not (ROOT / ".venv" / "bin" / "riskdesk").exists()
                    and shutil.which("riskdesk") is None,
                    reason="riskdesk is not installed in this environment")
def test_demo_fails_loudly_when_an_example_is_unreadable(tmp_path):
    """set -eu with no pipefail would let a broken command pass unnoticed
    through the summariser, so the failure has to reach the exit code."""
    broken = tmp_path / "examples"
    shutil.copytree(ROOT / "examples", broken)
    (broken / "tail.json").write_text("{}")
    copy = tmp_path / "demo.sh"
    shutil.copy2(DEMO, copy)
    shutil.copytree(ROOT / "scripts", tmp_path / "scripts")
    venv = ROOT / ".venv"
    if venv.exists():
        os.symlink(venv, tmp_path / ".venv")
    finished = subprocess.run(["/bin/sh", str(copy)], capture_output=True,
                              text=True, cwd=str(tmp_path), timeout=600,
                              env=dict(os.environ,
                                       RISKDESK_ARTIFACTS=str(tmp_path / "a")))
    assert finished.returncode != 0
