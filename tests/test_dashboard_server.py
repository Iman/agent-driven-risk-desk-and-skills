"""The socket. Integration, because it binds one.

Nothing here is marked unit. The unit files above render the same HTML in
process and assert on the strings; this file exists to prove a real client
over a real socket gets that HTML, and to pin what the server refuses.

Port 0 throughout, so the operating system picks a free port and no run can
collide with a developer's own server or with a parallel job.
"""
from pathlib import Path
import socket
import threading
import urllib.error
import urllib.request

import pytest

from riskdesk.dashboard import data, server

EXAMPLES = Path(__file__).resolve().parent.parent / "examples"

pytestmark = pytest.mark.integration


@pytest.fixture(scope="module")
def payload():
    return data.build(data.load_desk(EXAMPLES / "energy_stress.json",
                                     EXAMPLES / "energy_tail.json",
                                     EXAMPLES / "energy_book.json"))


@pytest.fixture
def running(payload):
    httpd = server.make_server(payload, "127.0.0.1", 0)
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    host, port = httpd.server_address[0], httpd.server_address[1]
    yield "http://{}:{}".format(host, port)
    httpd.shutdown()
    httpd.server_close()
    thread.join(timeout=10)


def fetch(base, path=""):
    with urllib.request.urlopen("{}/{}".format(base, path), timeout=30) as r:
        return r.status, dict(r.headers), r.read().decode("utf-8")


@pytest.mark.parametrize("slug", ["", "overview", "exposure", "stress",
                                  "tail", "xva"])
def test_every_view_is_served_over_a_real_socket(running, slug):
    status, headers, body = fetch(running, slug)
    assert status == 200
    assert headers["Content-Type"] == "text/html; charset=utf-8"
    assert int(headers["Content-Length"]) == len(body.encode("utf-8"))
    assert body.startswith("<!DOCTYPE html>")
    assert "Risk Desk dashboard" in body


def test_the_root_path_serves_the_overview(running):
    assert fetch(running, "")[2] == fetch(running, "overview")[2]


def test_a_query_string_does_not_change_the_view(running):
    assert fetch(running, "exposure?x=1")[2] == fetch(running, "exposure")[2]


def test_an_unknown_path_is_404_and_still_a_readable_page(running):
    with pytest.raises(urllib.error.HTTPError) as caught:
        fetch(running, "nonsense")
    assert caught.value.code == 404
    body = caught.value.read().decode("utf-8")
    assert "no view called" in body
    assert "reads nothing else from disk" in body


@pytest.mark.parametrize("path", ["../../etc/passwd", "etc/passwd",
                                  "%2e%2e%2fetc%2fpasswd", "examples"])
def test_no_request_can_name_a_file_on_disk(running, path):
    """The routing table is fixed, so a path is either a view or a 404.
    Nothing in the request reaches the filesystem."""
    with pytest.raises(urllib.error.HTTPError) as caught:
        fetch(running, path)
    assert caught.value.code == 404
    assert "root:" not in caught.value.read().decode("utf-8", "replace")


def test_the_response_forbids_loading_anything(running):
    _, headers, _ = fetch(running, "exposure")
    policy = headers["Content-Security-Policy"]
    assert "default-src 'none'" in policy
    assert "form-action 'none'" in policy
    assert headers["X-Content-Type-Options"] == "nosniff"
    assert headers["Referrer-Policy"] == "no-referrer"


def test_the_server_does_not_announce_its_python_version(running):
    """BaseHTTPRequestHandler joins server_version and sys_version with a
    space, so the header keeps a trailing space once sys_version is
    emptied. The property under test is that no interpreter version is
    advertised, not the exact spacing."""
    _, headers, _ = fetch(running, "")
    assert headers["Server"].strip() == "riskdesk"
    assert "Python" not in headers["Server"]


@pytest.mark.parametrize("host", ["0.0.0.0", "::", "8.8.8.8",
                                  "example.invalid"])
def test_binding_anything_but_loopback_is_refused(payload, host):
    """No authentication, so it serves one machine. A typo in a flag must
    not be the thing that puts a risk book on a network."""
    with pytest.raises(ValueError, match="loopback"):
        server.make_server(payload, host, 0)


@pytest.mark.parametrize("host", ["127.0.0.1", "localhost", "::1",
                                  "127.0.0.5"])
def test_every_loopback_spelling_is_accepted(host):
    assert server.is_loopback(host)


def test_a_name_that_merely_resolves_to_loopback_is_not_trusted():
    """Whether a name still resolves to 127.0.0.1 is not this process's
    decision to rely on."""
    assert not server.is_loopback("localhost.localdomain")
    assert not server.is_loopback("my-laptop.local")


def test_a_head_request_is_answered_like_a_get(running):
    request = urllib.request.Request(running + "/tail", method="HEAD")
    with urllib.request.urlopen(request, timeout=30) as response:
        assert response.status == 200
        assert response.headers["Content-Type"] == "text/html; charset=utf-8"


def test_the_server_makes_no_outbound_connection(running):
    """Rendering is arithmetic over data already in memory. If a view ever
    reached the network, this would hang or fail rather than pass."""
    original = socket.socket.connect
    calls = []

    def record(self, address):
        calls.append(address)
        return original(self, address)

    socket.socket.connect = record
    try:
        fetch(running, "exposure")
        fetch(running, "tail")
    finally:
        socket.socket.connect = original
    outbound = [a for a in calls
                if not (isinstance(a, tuple)
                        and str(a[0]) in ("127.0.0.1", "::1", "localhost"))]
    assert outbound == [], outbound
