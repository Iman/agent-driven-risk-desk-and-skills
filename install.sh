#!/bin/sh
#
# Risk Desk installer.
#
# From a checkout:
#
#     ./install.sh
#
# It creates .venv in this directory with a supported Python, installs the
# package with its development extra, attempts the optional ORE extra and
# says plainly whether that worked, then runs the test suite.
#
# Everything it writes is inside this checkout: .venv and whatever pip
# leaves in its own cache. Nothing is placed on PATH, nothing is registered
# with an agent runtime, and no network service is started.
#
# The ORE extra is optional on purpose. Its wheel exists for a limited set
# of Python and platform combinations, and historical VaR, exposure and
# stress do not need it. A machine without it gets a working desk minus the
# xva command, and this script says so rather than failing.
#
# Research software. Not investment advice. See README.md.

set -eu

ROOT=$(cd "$(dirname "$0")" && pwd)
VENV="${RISKDESK_VENV:-$ROOT/.venv}"
WITH_TESTS=1
WITH_XVA=1

say() { printf '%s\n' "$*"; }
die() { printf 'error: %s\n' "$*" >&2; exit 1; }

usage() {
  say "Risk Desk installer"
  say ""
  say "Usage: ./install.sh [options]"
  say ""
  say "  --venv DIR    environment directory (default: ./.venv)"
  say "  --python BIN  interpreter to build the environment with"
  say "  --no-xva      skip the optional ORE extra"
  say "  --no-tests    do not run the test suite at the end"
  say "  --help        this text"
}

PYTHON="${RISKDESK_PYTHON:-}"
while [ $# -gt 0 ]; do
  case "$1" in
    --venv) [ $# -ge 2 ] || die "--venv needs a directory"; VENV="$2"; shift 2 ;;
    --python) [ $# -ge 2 ] || die "--python needs an interpreter"; PYTHON="$2"; shift 2 ;;
    --no-xva) WITH_XVA=0; shift ;;
    --no-tests) WITH_TESTS=0; shift ;;
    --help|-h) usage; exit 0 ;;
    *) printf 'unknown option: %s\n' "$1" >&2; usage >&2; exit 2 ;;
  esac
done

# pyproject requires 3.11 or later. The ORE wheel and the recorded
# dependency lock were tested on 3.13, so 3.13 is tried first and the
# others are accepted rather than preferred.
supported() {
  [ -x "$1" ] || command -v "$1" >/dev/null 2>&1 || return 1
  "$1" -c 'import sys; raise SystemExit(0 if sys.version_info[:2] >= (3, 11) else 1)' \
    >/dev/null 2>&1
}

if [ -n "$PYTHON" ]; then
  supported "$PYTHON" || die "$PYTHON is not a Python 3.11 or later interpreter"
else
  for candidate in python3.13 python3.12 python3.11 python3; do
    if supported "$candidate"; then PYTHON="$candidate"; break; fi
  done
  [ -n "$PYTHON" ] || die "no Python 3.11 or later found; install one or pass --python"
fi

say "== Risk Desk install"
say "   checkout:    $ROOT"
say "   environment: $VENV"
say "   interpreter: $("$PYTHON" -c 'import sys; print(sys.executable)')"
say "   version:     $("$PYTHON" -c 'import platform; print(platform.python_version(), platform.machine())')"

if [ ! -x "$VENV/bin/python" ]; then
  say "== Creating the environment"
  "$PYTHON" -m venv "$VENV" || die "could not create $VENV"
else
  say "== Reusing the existing environment"
fi
VPY="$VENV/bin/python"
[ -x "$VPY" ] || die "no interpreter at $VPY"

say "== Installing riskdesk with its development extra"
"$VPY" -m pip install --upgrade --quiet pip || die "could not upgrade pip"
"$VPY" -m pip install --quiet "$ROOT[dev]" || die "could not install riskdesk[dev]"

XVA_STATUS="skipped by --no-xva"
if [ "$WITH_XVA" -eq 1 ]; then
  say "== Attempting the optional ORE extra"
  if "$VPY" -m pip install --quiet "$ROOT[xva]" >"$VENV/xva-install.log" 2>&1; then
    XVA_STATUS="installed: $("$VPY" -m pip show open-source-risk-engine \
      | sed -n 's/^Version: //p')"
  else
    XVA_STATUS="not installed; see $VENV/xva-install.log"
  fi
fi

if [ "$WITH_TESTS" -eq 1 ]; then
  say "== Running the test suite"
  ( cd "$ROOT" && "$VPY" -m pytest -q --color=no ) || die "the test suite failed"
fi

say ""
say "== Done"
say "   riskdesk:    $VENV/bin/riskdesk"
say "   MCP server:  $VENV/bin/riskdesk-mcp"
say "   ORE extra:   $XVA_STATUS"
say ""
say "   Next: ./demo.sh"
