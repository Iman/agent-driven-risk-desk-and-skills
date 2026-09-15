"""Risk Desk commands share the same functions as MCP tools."""
import argparse
import json
from pathlib import Path
import sys
from riskdesk.analytics import tail_risk, portfolio_exposure, stress_test
from riskdesk.ore import run_ore
from riskdesk.report import build_report

HANDLERS = {"tail": tail_risk, "exposure": portfolio_exposure, "stress": stress_test}


def write_report(stress_path, output_path, tail_path=None, exposure_path=None):
    """Write the HTML page and return a summary of what reached it."""
    stress_payload = json.loads(Path(stress_path).read_text())
    tail_payload = json.loads(Path(tail_path).read_text()) if tail_path else None
    exposure_payload = json.loads(Path(exposure_path).read_text()) if exposure_path else None
    document, payload = build_report(stress_payload, tail_payload, exposure_payload)
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(document, encoding="utf-8")
    return dict(output=str(output_path), bytes=len(document.encode("utf-8")),
                currency=payload["currency"], as_of=payload["as_of"],
                degraded=payload["degraded"], degraded_reason=payload["degraded_reason"],
                scenarios=[s["name"] for s in payload["scenarios"]],
                tail_included=payload["tail"] is not None,
                exposure_included=payload["exposure"] is not None)


def main(argv=None):
    parser = argparse.ArgumentParser(prog="riskdesk")
    commands = parser.add_subparsers(dest="command", required=True)
    for command in HANDLERS:
        sub = commands.add_parser(command)
        sub.add_argument("--input", required=True, type=Path)
    ore = commands.add_parser("xva")
    for field in ("project", "config", "output", "data-mode"):
        ore.add_argument("--"+field, required=True)
    # The report reads a stress request and, optionally, a tail request and
    # an exposure request. An omitted panel is reported as an absent input
    # rather than invented, and never as a zero.
    page = commands.add_parser("report")
    page.add_argument("--input", required=True, type=Path)
    page.add_argument("--output", required=True, type=Path)
    page.add_argument("--tail", type=Path)
    page.add_argument("--exposure", type=Path)
    args = parser.parse_args(argv)
    try:
        if args.command == "xva":
            result = run_ore(args.project, args.config, args.output, args.data_mode)
        elif args.command == "report":
            result = write_report(args.input, args.output, args.tail, args.exposure)
        else:
            result = HANDLERS[args.command](json.loads(args.input.read_text()))
        print(json.dumps(result, indent=2, allow_nan=False))
        return 0
    except Exception as exc:
        # The JSON envelope stays on stdout, because that is the contract a
        # machine caller reads. A human line also goes to stderr, because a
        # caller that discards stdout otherwise loses the diagnosis
        # entirely while still exiting non-zero: demo.sh redirects this
        # command's stdout, so a PermissionError inside a container arrived
        # in CI as a bare exit code with an empty stderr.
        print(json.dumps({"error": type(exc).__name__, "message": str(exc)}))
        print("riskdesk {}: {}: {}".format(args.command, type(exc).__name__, exc),
              file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
