#!/bin/sh
#
# Risk Desk demonstration.
#
# Runs every core command on the files in examples/, prints what each
# result means, writes one HTML report, and lists the MCP tools the local
# server exposes.
#
# Two books are shown. The first is the four-line teaching example the
# tests use. The second is a small synthetic energy book: WTI and Brent
# futures, Henry Hub and TTF gas, a JKM-linked LNG cargo and a power
# forward, with two hand-chosen scenario shapes.
#
# Every input here is synthetic. Nothing is fetched, nothing is ordered,
# and every figure printed comes from the JSON the command above it wrote.
#
# Research software. Not investment advice. See README.md.

set -eu

ROOT=$(cd "$(dirname "$0")" && pwd)
VENV="${RISKDESK_VENV:-$ROOT/.venv}"
OUT_DIR="${RISKDESK_ARTIFACTS:-$ROOT/artifacts}"

if [ -x "$VENV/bin/riskdesk" ]; then
  DESK="$VENV/bin/riskdesk"
  VPY="$VENV/bin/python"
elif command -v riskdesk >/dev/null 2>&1; then
  DESK=$(command -v riskdesk)
  VPY=$(command -v python3)
else
  printf 'error: riskdesk was not found. Run ./install.sh first.\n' >&2
  exit 1
fi

say() { printf '\n== %s\n' "$*"; }
note() { printf '  %s\n' "$*"; }

summarise() { "$VPY" -m riskdesk.summaries "$1"; }

mkdir -p "$OUT_DIR"

say "Risk Desk demonstration"
note "command:   $DESK"
note "examples:  $ROOT/examples"
note "artifacts: $OUT_DIR"
note "all inputs are synthetic; no market data is read and no order is placed"

# ------------------------------------------------- 1. the teaching example

say "1. Teaching example: historical tail risk"
note "riskdesk tail --input examples/tail.json"
"$DESK" tail --input "$ROOT/examples/tail.json" | summarise tail

say "1. Teaching example: linear exposure"
note "riskdesk exposure --input examples/portfolio.json"
"$DESK" exposure --input "$ROOT/examples/portfolio.json" | summarise exposure

say "1. Teaching example: explicit stress"
note "riskdesk stress --input examples/stress.json"
"$DESK" stress --input "$ROOT/examples/stress.json" | summarise stress

# ---------------------------------------------------- 2. the energy book

say "2. Synthetic energy book: historical tail risk"
note "riskdesk tail --input examples/energy_tail.json"
"$DESK" tail --input "$ROOT/examples/energy_tail.json" | summarise tail

say "2. Synthetic energy book: linear exposure"
note "riskdesk exposure --input examples/energy_book.json"
"$DESK" exposure --input "$ROOT/examples/energy_book.json" | summarise exposure

say "2. Synthetic energy book: explicit stress"
note "riskdesk stress --input examples/energy_stress.json"
"$DESK" stress --input "$ROOT/examples/energy_stress.json" | summarise stress

# ------------------------------------------------------------- 3. report

say "3. One self-contained HTML page from the stress and tail results"
note "riskdesk report --input examples/energy_stress.json --tail examples/energy_tail.json --output artifacts/report.html"
"$DESK" report --input "$ROOT/examples/energy_stress.json" \
  --tail "$ROOT/examples/energy_tail.json" \
  --output "$OUT_DIR/report.html" >/dev/null
note "written: $OUT_DIR/report.html"
note "it embeds its own styling and charts, so it opens with no network"

# ---------------------------------------------------------- 4. MCP tools

say "4. The MCP tools an agent sees"
"$VPY" "$ROOT/scripts/list_tools.py"

say "Done"
note "every figure above came from a synthetic file in examples/"
note "historical loss measures are not risk-neutral valuation"
note "an explicit scenario carries no probability and is not a forecast"
