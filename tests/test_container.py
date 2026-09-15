"""The container image, built and run for real.

These are slow and they need a Docker daemon, so they carry their own
marker and are skipped, not failed, where there is no daemon: a test that
reports the absence of Docker as a defect in this repository is reporting
the wrong thing.

What they pin is the pair of failures the entrypoint exists to prevent,
both of which otherwise look like success: a report written into a
container with no volume and discarded on exit, and an xva run against an
ORE backend the image does not have.
"""
import json
import os
from pathlib import Path
import shutil
import subprocess

import pytest

ROOT = Path(__file__).resolve().parent.parent
TAG = os.environ.get("RISKDESK_IMAGE_TAG", "risk-desk:pytest")

pytestmark = [pytest.mark.integration, pytest.mark.docker,
              pytest.mark.skipif(shutil.which("docker") is None,
                                 reason="no docker on PATH")]


def docker(*argv, **kwargs):
    return subprocess.run(["docker", *argv], capture_output=True, text=True,
                          timeout=1800, **kwargs)


def as_me():
    """Run as the uid that owns the mount.

    The image runs as a fixed non-root uid on purpose, and a bind mount on
    Linux keeps the host's ownership, so writing into a directory owned by
    somebody else fails with EACCES. Docker Desktop on macOS virtualises
    that away, which is exactly why this was green on a laptop and red on a
    Linux runner. Every writing test here passes --user so it exercises the
    documented route rather than a permissive daemon.
    """
    return ["--user", "{}:{}".format(os.getuid(), os.getgid())]


@pytest.fixture
def unwritable_volume():
    """A mount the image's uid cannot write, on any daemon.

    A bind mount cannot be made unwritable portably, because Docker Desktop
    remaps ownership. A named volume can: Docker chowns a volume to the
    container user only while it is empty, so populating it first and then
    chowning it to another uid produces a mount root the container cannot
    write, on Linux and on macOS alike. That is what the CI runner had.
    """
    name = "riskdesk-pytest-unwritable"
    docker("volume", "rm", "-f", name)
    created = docker("volume", "create", name)
    assert created.returncode == 0, created.stderr
    prepared = docker("run", "--rm", "-u", "0", "-v", name + ":/artifacts",
                      "alpine", "sh", "-c",
                      "touch /artifacts/.keep && chown -R 1001:1001 "
                      "/artifacts && chmod 755 /artifacts")
    if prepared.returncode:
        docker("volume", "rm", "-f", name)
        pytest.skip("could not prepare the volume: " + prepared.stderr[-300:])
    yield name
    docker("volume", "rm", "-f", name)


@pytest.fixture(scope="module")
def image():
    if docker("version", "--format", "{{.Server.Version}}").returncode:
        pytest.skip("no docker daemon is answering")
    built = docker("build", "-t", TAG, ".", cwd=str(ROOT))
    assert built.returncode == 0, built.stdout[-4000:] + built.stderr[-4000:]
    return TAG


def test_the_image_builds_and_reports_its_own_scope(image):
    """doctor has to say whether the ORE extra is in this image. It is not
    available for every platform, and finding that out from an import
    error inside a worker is a bad way to find out."""
    finished = docker("run", "--rm", image)
    assert finished.returncode == 0, finished.stderr
    out = finished.stdout
    assert "Risk Desk in a container" in out
    assert "/usr/local/bin/riskdesk" in out
    assert "ORE extra:" in out
    assert "\x1b" not in out
    status = [line for line in out.splitlines() if "ORE extra:" in line][0]
    assert ("installed:" in status
            or "not available for this image platform" in status
            or "not attempted" in status), status


def test_the_cli_runs_over_the_examples_that_travel_with_the_image(image):
    finished = docker("run", "--rm", image, "exposure",
                      "--input", "/opt/risk-desk/examples/energy_book.json")
    assert finished.returncode == 0, finished.stderr
    result = json.loads(finished.stdout)
    assert result["gross_exposure"] == 14100000.0
    assert result["net_exposure"] == 6000000.0
    assert result["degraded"] is False


def test_the_entrypoint_runs_the_demo_and_keeps_what_it_wrote(image, tmp_path):
    artifacts = tmp_path / "artifacts"
    artifacts.mkdir()
    finished = docker("run", "--rm", *as_me(), "-v",
                      "{}:/artifacts".format(artifacts), image, "demo")
    assert finished.returncode == 0, finished.stdout[-3000:] + finished.stderr
    out = finished.stdout
    assert "\x1b" not in out
    for expected in ("historical VaR and Expected Shortfall via skfolio",
                     "loss is positive",
                     "WTI_CRUDE_FUTURE",
                     "worst three positions by P&L",
                     "4 MCP tools",
                     "carries no probability and is not a forecast"):
        assert expected in out, expected
    page = artifacts / "report.html"
    assert page.exists(), "the demo wrote nothing to the mounted volume"
    document = page.read_text(encoding="utf-8")
    assert document.startswith("<!DOCTYPE html>")
    assert 'class="bar short"' in document


def test_a_run_that_would_discard_its_output_is_refused(image):
    """Without a mount the report is written into the container and lost,
    and the summary on stdout is identical to a real run."""
    finished = docker("run", "--rm", image, "demo")
    assert finished.returncode == 64
    assert "No volume is mounted" in finished.stderr
    assert "RISKDESK_ALLOW_EPHEMERAL" in finished.stderr


def test_an_explicitly_throwaway_run_is_allowed(image):
    finished = docker("run", "--rm", "-e", "RISKDESK_ALLOW_EPHEMERAL=1",
                      image, "report",
                      "--input", "/opt/risk-desk/examples/energy_stress.json",
                      "--exposure", "/opt/risk-desk/examples/energy_book.json",
                      "--output", "/artifacts/report.html")
    assert finished.returncode == 0, finished.stderr
    assert json.loads(finished.stdout)["exposure_included"] is True
    assert "will be discarded" in finished.stderr


def test_xva_behaves_correctly_for_whichever_scope_this_image_has(image):
    """Both platforms are covered, not one with a bare skip.

    The ORE wheel resolves on linux/amd64 and not on linux/arm64, so the
    same image recipe legitimately produces two scopes. A test that simply
    skipped on the amd64 side would leave the path CI actually runs
    untested, which is how a skip hides a second problem.
    """
    status = docker("run", "--rm", image).stdout
    finished = docker("run", "--rm", image, "xva", "--project", "p",
                      "--config", "c", "--output", "o",
                      "--data-mode", "synthetic")
    if "installed:" in status:
        # The backend is present, so the adapter runs and refuses the bad
        # project itself, as a JSON envelope with a line on stderr.
        assert finished.returncode == 1, finished.stdout + finished.stderr
        assert json.loads(finished.stdout)["error"] == "ValueError"
        assert "ValueError" in finished.stderr
    else:
        assert finished.returncode == 69
        assert "no ORE backend" in finished.stderr
        assert "Nothing was run" in finished.stderr


def test_a_mount_it_cannot_write_is_refused_before_anything_runs(
        image, unwritable_volume):
    """The regression. This failed in CI as exit 1 with an empty stderr and
    a demo that stopped mid run; it must now refuse, say why, and name the
    fix, before writing anything."""
    finished = docker("run", "--rm", "-v", unwritable_volume + ":/artifacts",
                      image, "demo")
    assert finished.returncode == 65, finished.stdout[-2000:]
    assert "Cannot write to /artifacts as uid 10001" in finished.stderr
    assert "--user" in finished.stderr
    assert "Nothing was run" in finished.stderr
    assert "historical VaR" not in finished.stdout


def test_the_documented_fix_for_that_mount_actually_works(
        image, unwritable_volume):
    """A refusal that names a fix which does not work is worse than no
    message, so the message is checked against the thing it recommends."""
    finished = docker("run", "--rm", "--user", "1001:1001", "-v",
                      unwritable_volume + ":/artifacts", image, "demo")
    assert finished.returncode == 0, finished.stdout[-2000:] + finished.stderr
    assert "4 MCP tools" in finished.stdout


def test_a_failing_command_says_why_on_stderr(image):
    """The defect that made the CI failure unreadable. demo.sh sends this
    command's stdout to /dev/null, so an error envelope printed only to
    stdout arrived as a bare exit code and an empty stderr."""
    finished = docker("run", "--rm", "-e", "RISKDESK_ALLOW_EPHEMERAL=1",
                      image, "report", "--input", "/opt/risk-desk/nope.json",
                      "--output", "/artifacts/report.html")
    assert finished.returncode == 1
    assert finished.stderr.strip(), "a failure with an empty stderr"
    assert "FileNotFoundError" in finished.stderr
    assert json.loads(finished.stdout)["error"] == "FileNotFoundError"


def test_a_missing_artifacts_directory_reports_that_and_not_permissions(
        image):
    """Two different problems deserve two different messages. Reporting a
    missing directory as a permission problem sends the reader to --user,
    which would not help."""
    finished = docker("run", "--rm", "-e", "RISKDESK_ARTIFACTS=/nowhere",
                      image, "demo")
    assert finished.returncode == 66
    assert "There is no directory at /nowhere" in finished.stderr
    assert "--user" not in finished.stderr
    assert "Nothing was run" in finished.stderr


def test_the_image_does_not_run_as_root(image):
    finished = docker("run", "--rm", "--entrypoint", "id", image, "-un")
    assert finished.returncode == 0, finished.stderr
    assert finished.stdout.strip() == "desk"
