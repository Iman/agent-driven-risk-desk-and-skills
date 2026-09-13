"""Risk Desk commands share the same functions as MCP tools."""
import argparse
import json
from pathlib import Path
import sys
from riskdesk.analytics import tail_risk, portfolio_exposure, stress_test
from riskdesk.ore import run_ore

HANDLERS = {"tail": tail_risk, "exposure": portfolio_exposure, "stress": stress_test}


def main(argv=None):
    parser = argparse.ArgumentParser(prog="riskdesk")
    commands = parser.add_subparsers(dest="command", required=True)
    for command in HANDLERS:
        sub = commands.add_parser(command)
        sub.add_argument("--input", required=True, type=Path)
    ore = commands.add_parser("xva")
    for field in ("project", "config", "output", "data-mode"):
        ore.add_argument("--"+field, required=True)
    args = parser.parse_args(argv)
    try:
        if args.command == "xva":
            result = run_ore(args.project, args.config, args.output, args.data_mode)
        else:
            result = HANDLERS[args.command](json.loads(args.input.read_text()))
        print(json.dumps(result, indent=2, allow_nan=False))
        return 0
    except Exception as exc:
        print(json.dumps({"error": type(exc).__name__, "message": str(exc)}))
        return 1


if __name__ == "__main__":
    sys.exit(main())
