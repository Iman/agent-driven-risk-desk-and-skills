"""Wire the dashboard together, and make every failure legible.

WHY THIS MODULE IS SHAPED LIKE THIS. The container shipped a defect with
exactly this profile: it worked under a permissive local daemon and failed
where ownership was real, and it failed by dying with an empty stderr into
a stream somebody had redirected. A server that binds a socket and reads
files has the same two opportunities, so each one is caught here and turned
into a sentence that names the thing that went wrong and what to do.

Every exit code below is distinct, so a script can tell the cases apart
without parsing prose:

    64  the host is not a loopback address, so binding was refused
    66  an input file is missing
    67  an input file is not valid JSON, or fails its contract
    73  the port is already in use
"""
import argparse
import errno
import json
from pathlib import Path
import sys

from riskdesk.dashboard import data, server

DEFAULT_INPUTS = {
    "input": "examples/energy_stress.json",
    "tail": "examples/energy_tail.json",
    "exposure": "examples/energy_book.json",
}

EXIT_NOT_LOOPBACK = 64
EXIT_MISSING_INPUT = 66
EXIT_BAD_INPUT = 67
EXIT_PORT_IN_USE = 73


class Problem(Exception):
    """A failure with a code and a sentence a person can act on."""

    def __init__(self, code, message):
        super().__init__(message)
        self.code = code
        self.message = message


def resolve_inputs(args, root=None):
    """Work out which files to read, and say clearly when one is absent.

    The defaults are the synthetic energy book, resolved against the
    working directory, so running this from a checkout needs no flags. A
    default that is not there is not an error: it simply means the caller
    is somewhere else and should pass the paths. A path the caller asked
    for by name and which is missing IS an error, because they meant it.
    """
    root = Path(root or Path.cwd())
    chosen = {}
    for key in ("input", "tail", "exposure", "xva"):
        given = getattr(args, key, None)
        if given is not None:
            path = Path(given)
            if not path.is_file():
                raise Problem(EXIT_MISSING_INPUT,
                              "no such file for --{}: {}".format(key, path))
            chosen[key] = path
            continue
        default = DEFAULT_INPUTS.get(key)
        candidate = root / default if default else None
        chosen[key] = candidate if candidate and candidate.is_file() else None
    if chosen["input"] is None:
        raise Problem(
            EXIT_MISSING_INPUT,
            "no stress input. Run this from a checkout, where {} exists, or "
            "pass --input PATH.".format(DEFAULT_INPUTS["input"]))
    return chosen


def build_payload(chosen):
    """Read and shape, turning any contract failure into one sentence."""
    try:
        desk = data.load_desk(chosen["input"], chosen["tail"],
                              chosen["exposure"], chosen["xva"])
    except (OSError, ValueError) as exc:
        raise Problem(EXIT_BAD_INPUT,
                      "could not read an input: {}".format(exc)) from exc
    try:
        return data.build(desk)
    except (ValueError, KeyError, TypeError) as exc:
        raise Problem(EXIT_BAD_INPUT,
                      "an input does not meet its contract: {}: {}".format(
                          type(exc).__name__, exc)) from exc


def start(payload, host, port, log=None):
    """Bind, turning the two failures that actually happen into sentences."""
    try:
        return server.make_server(payload, host, port, log)
    except ValueError as exc:
        raise Problem(EXIT_NOT_LOOPBACK, str(exc)) from exc
    except OSError as exc:
        if exc.errno == errno.EADDRINUSE:
            raise Problem(
                EXIT_PORT_IN_USE,
                "port {} on {} is already in use. Pass --port with another "
                "number, or stop whatever is holding it.".format(
                    port, host)) from exc
        raise Problem(EXIT_PORT_IN_USE,
                      "could not bind {} port {}: {}".format(
                          host, port, exc)) from exc


def run(args, out=None, err=None, root=None, forever=True):
    """One call that serves, and returns an exit code rather than raising."""
    out = out or sys.stdout
    err = err or sys.stderr
    try:
        chosen = resolve_inputs(args, root)
        payload = build_payload(chosen)
        httpd = start(payload, args.host, args.port,
                      log=(lambda line: print(line, file=err)) if args.log
                      else None)
    except Problem as problem:
        # stderr, always. The container taught this repository what it costs
        # to put a diagnosis somewhere a caller may have redirected.
        print("riskdesk dashboard: " + problem.message, file=err)
        return problem.code
    host, port = httpd.server_address[0], httpd.server_address[1]
    print("Risk Desk dashboard on http://{}:{}".format(host, port), file=out)
    print("  serving {}".format(chosen["input"]), file=out)
    for key in ("exposure", "tail", "xva"):
        state = chosen[key] if chosen[key] else "not supplied"
        print("  {:<9} {}".format(key, state), file=out)
    print("  local only: this server makes no outbound request", file=out)
    print("  stop it with ctrl-c", file=out)
    out.flush()
    if not forever:
        return httpd
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("", file=out)
        print("stopped", file=out)
    finally:
        httpd.server_close()
    return 0


def add_arguments(parser):
    parser.add_argument("--input", type=Path)
    parser.add_argument("--tail", type=Path)
    parser.add_argument("--exposure", type=Path)
    parser.add_argument("--xva", type=Path)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8899)
    parser.add_argument("--log", action="store_true",
                        help="print one line per request to stderr")
    return parser


def main(argv=None):
    parser = add_arguments(argparse.ArgumentParser(prog="riskdesk dashboard"))
    return run(parser.parse_args(argv))


if __name__ == "__main__":
    raise SystemExit(main())
