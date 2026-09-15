"""The wiring, and every failure it turns into a sentence.

Split deliberately. The failures that do not need a socket are unit tests,
because a resolver or an error message should not need a port to be
checked. The two that genuinely bind are integration, and they are marked
so CI runs them rather than skipping them into invisibility.

Every case here exists because the container shipped the opposite: a
failure that arrived as a bare exit code with an empty stderr.
"""
import argparse
import io
from pathlib import Path
import socket
import threading
import urllib.request

import pytest

from riskdesk.dashboard import app

ROOT = Path(__file__).resolve().parent.parent
EXAMPLES = ROOT / "examples"


def parse(argv):
    return app.add_arguments(argparse.ArgumentParser()).parse_args(argv)


def run(argv, root=None, forever=True):
    out, err = io.StringIO(), io.StringIO()
    result = app.run(parse(argv), out=out, err=err, root=root,
                     forever=forever)
    return result, out.getvalue(), err.getvalue()


@pytest.mark.unit
def test_the_defaults_are_the_synthetic_energy_book():
    chosen = app.resolve_inputs(parse([]), root=ROOT)
    assert chosen["input"].name == "energy_stress.json"
    assert chosen["tail"].name == "energy_tail.json"
    assert chosen["exposure"].name == "energy_book.json"
    assert chosen["xva"] is None


@pytest.mark.unit
def test_a_default_that_is_not_there_is_not_an_error(tmp_path):
    """Being somewhere else is not a mistake; only the stress input is
    required, and its absence says what to pass."""
    with pytest.raises(app.Problem) as caught:
        app.resolve_inputs(parse([]), root=tmp_path)
    assert caught.value.code == app.EXIT_MISSING_INPUT
    assert "--input PATH" in caught.value.message


@pytest.mark.unit
def test_a_path_asked_for_by_name_and_missing_is_an_error(tmp_path):
    with pytest.raises(app.Problem) as caught:
        app.resolve_inputs(parse(["--tail", str(tmp_path / "nope.json")]),
                           root=ROOT)
    assert caught.value.code == app.EXIT_MISSING_INPUT
    assert "--tail" in caught.value.message


@pytest.mark.unit
def test_a_missing_input_is_one_sentence_on_stderr_not_a_traceback(tmp_path):
    code, out, err = run(["--input", str(tmp_path / "nope.json")], root=ROOT)
    assert code == app.EXIT_MISSING_INPUT
    assert out == ""
    assert err.startswith("riskdesk dashboard: no such file for --input")
    assert "Traceback" not in err
    assert err.count("\n") == 1


@pytest.mark.unit
def test_input_that_is_not_json_says_so_rather_than_raising(tmp_path):
    broken = tmp_path / "broken.json"
    broken.write_text("{not json", encoding="utf-8")
    code, out, err = run(["--input", str(broken)], root=ROOT)
    assert code == app.EXIT_BAD_INPUT
    assert "could not read an input" in err
    assert "Traceback" not in err


@pytest.mark.unit
def test_input_that_fails_its_contract_says_which_contract(tmp_path):
    empty = tmp_path / "empty.json"
    empty.write_text("{}", encoding="utf-8")
    code, out, err = run(["--input", str(empty)], root=ROOT)
    assert code == app.EXIT_BAD_INPUT
    assert "does not meet its contract" in err
    assert "ValidationError" in err
    assert "Traceback" not in err


@pytest.mark.unit
@pytest.mark.parametrize("host", ["0.0.0.0", "8.8.8.8"])
def test_a_non_loopback_host_is_refused_before_a_socket_exists(host):
    code, out, err = run(["--host", host], root=ROOT)
    assert code == app.EXIT_NOT_LOOPBACK
    assert "loopback" in err
    assert "Use 127.0.0.1 or ::1" in err
    assert out == ""


@pytest.mark.unit
def test_every_failure_has_its_own_exit_code():
    """A script should be able to tell these apart without reading prose."""
    codes = {app.EXIT_NOT_LOOPBACK, app.EXIT_MISSING_INPUT,
             app.EXIT_BAD_INPUT, app.EXIT_PORT_IN_USE}
    assert len(codes) == 4
    assert 0 not in codes


@pytest.mark.integration
def test_a_port_already_taken_is_a_sentence_not_a_stack():
    holder = socket.socket()
    holder.bind(("127.0.0.1", 0))
    holder.listen(1)
    try:
        port = holder.getsockname()[1]
        code, out, err = run(["--port", str(port)], root=ROOT)
        assert code == app.EXIT_PORT_IN_USE
        assert "already in use" in err
        assert "--port" in err
        assert "Traceback" not in err
    finally:
        holder.close()


@pytest.mark.integration
def test_it_serves_the_energy_book_and_says_what_it_read():
    httpd = None
    try:
        result, out, err = run(["--port", "0"], root=ROOT, forever=False)
        httpd = result
        assert err == ""
        assert "Risk Desk dashboard on http://127.0.0.1:" in out
        assert "energy_stress.json" in out
        assert "no outbound request" in out
        thread = threading.Thread(target=httpd.serve_forever, daemon=True)
        thread.start()
        host, port = httpd.server_address[0], httpd.server_address[1]
        with urllib.request.urlopen(
                "http://{}:{}/exposure".format(host, port), timeout=30) as r:
            body = r.read().decode("utf-8")
        assert "14,100,000.00 USD" in body
        assert ">not degraded<" in body
        httpd.shutdown()
        thread.join(timeout=10)
    finally:
        if httpd is not None:
            httpd.server_close()


@pytest.mark.integration
def test_an_absent_optional_input_is_reported_as_not_supplied(tmp_path):
    httpd = None
    try:
        result, out, err = run(
            ["--port", "0", "--input", str(EXAMPLES / "energy_stress.json")],
            root=tmp_path, forever=False)
        httpd = result
        assert "xva       not supplied" in out
        assert "tail      not supplied" in out
    finally:
        if httpd is not None:
            httpd.server_close()
