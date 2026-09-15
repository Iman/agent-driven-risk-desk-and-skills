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
    finished = docker("run", "--rm", "-v",
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


def test_xva_without_a_backend_is_refused_before_anything_runs(image):
    status = docker("run", "--rm", image).stdout
    if "installed:" in status:
        pytest.skip("this image has the ORE extra, so there is nothing to "
                    "refuse")
    finished = docker("run", "--rm", image, "xva", "--project", "p",
                      "--config", "c", "--output", "o",
                      "--data-mode", "synthetic")
    assert finished.returncode == 69
    assert "no ORE backend" in finished.stderr
    assert "Nothing was run" in finished.stderr


def test_the_image_does_not_run_as_root(image):
    finished = docker("run", "--rm", "--entrypoint", "id", image, "-un")
    assert finished.returncode == 0, finished.stderr
    assert finished.stdout.strip() == "desk"
