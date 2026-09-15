"""The local HTTP server, and the rules about what it will bind to.

Standard library only: no framework, no new dependency, nothing added to
notices, wheel-hashes.json or the lock.

Two properties this module is responsible for, both enforced rather than
documented. It binds a loopback address and refuses anything else, so the
dashboard cannot be exposed to a network by a typo in a flag. And it reads
no path from the request: the routing table is fixed, so a request cannot
name a file on disk.
"""
import ipaddress
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from riskdesk.dashboard import page

LOOPBACK_NAMES = {"localhost", "ip6-localhost", "ip6-loopback"}


def is_loopback(host):
    """Is this host an address that only this machine can reach?

    Names are allowed only for the well known loopback spellings. Anything
    else, including a name that happens to resolve to 127.0.0.1 today, is
    refused: whether it still resolves that way is not this process's
    decision to rely on.
    """
    if host in LOOPBACK_NAMES:
        return True
    try:
        return ipaddress.ip_address(host).is_loopback
    except ValueError:
        return False


def require_loopback(host):
    if not is_loopback(host):
        raise ValueError(
            "refusing to bind {!r}: this dashboard serves one machine and "
            "has no authentication, so it binds a loopback address only. "
            "Use 127.0.0.1 or ::1.".format(host))
    return host


def make_handler(payload, log=None):
    """A handler class closed over one already-shaped payload.

    The payload is built once, before the socket exists, so a request
    cannot trigger a calculation and no view can disagree with another
    because the inputs moved between two requests.
    """

    class Handler(BaseHTTPRequestHandler):
        server_version = "riskdesk"
        sys_version = ""

        def do_GET(self):
            slug = self.path.split("?", 1)[0].strip("/") or "overview"
            if slug in page.RENDERERS:
                body = page.render(payload, slug)
                status = 200
            else:
                body = page.not_found(payload, slug)
                status = 404
            encoded = body.encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(encoded)))
            # The page embeds everything it needs, so nothing should be
            # fetched from anywhere. Saying so in a header means a browser
            # enforces it rather than the claim resting on the markup.
            self.send_header("Content-Security-Policy",
                             "default-src 'none'; style-src 'unsafe-inline'; "
                             "img-src data:; form-action 'none'; "
                             "frame-ancestors 'none'; base-uri 'none'")
            self.send_header("Referrer-Policy", "no-referrer")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.end_headers()
            self.wfile.write(encoded)

        def do_HEAD(self):
            self.do_GET()

        def log_message(self, fmt, *args):
            if log is not None:
                log("{} {}".format(self.address_string(), fmt % args))

    return Handler


def make_server(payload, host="127.0.0.1", port=8899, log=None):
    """Bind and return a server. The caller runs and closes it."""
    require_loopback(host)
    return ThreadingHTTPServer((host, port), make_handler(payload, log))
