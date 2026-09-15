#!/bin/sh
# Say what this image can do, and refuse to lose somebody's work quietly.
#
# Two failures this guards against, both of which look like success.
#
# The first is a report written inside the container with no volume
# mounted: the summary on stdout is identical to a real run, and the file
# is gone when the container exits.
#
# The second is the ORE extra. It has no distribution for every platform
# this image is built on, so `xva` can be genuinely absent. Discovering
# that from an import error inside a worker process is a bad way to find
# out, so the status recorded at build time is printed here and `xva` is
# refused up front with the reason.

set -eu

HOME_DIR=/opt/risk-desk
ARTIFACTS="${RISKDESK_ARTIFACTS:-/artifacts}"
XVA_STATUS="$(cat "$HOME_DIR/xva-status" 2>/dev/null || echo unknown)"

writes_files() {
    case "${1:-}" in
        report|demo) return 0 ;;
        *) return 1 ;;
    esac
}

doctor() {
    echo "Risk Desk in a container"
    echo "  riskdesk:   $(command -v riskdesk || echo 'not on PATH')"
    echo "  version:    $(riskdesk --help >/dev/null 2>&1 && python -c 'import riskdesk; print(riskdesk.__version__)')"
    echo "  python:     $(python -c 'import platform; print(platform.python_version(), platform.machine())')"
    echo "  ORE extra:  $XVA_STATUS"
    echo "  artifacts:  $ARTIFACTS"
    echo "  examples:   $HOME_DIR/examples"
    echo ""
    echo "  Commands:"
    echo "    demo                      run the full demonstration"
    echo "    tail|exposure|stress      read a JSON input, print a result"
    echo "    report                    write one self-contained HTML page"
    echo "    xva                       run a local ORE project"
    echo "    mcp                       serve the MCP tools over stdio"
    echo ""
    echo "  Mount a directory to keep what it writes:"
    echo "    docker run --rm -v \"\$PWD/artifacts:/artifacts\" IMAGE demo"
    echo ""
    echo "  The skills are read by the agent on your host, not by this"
    echo "  image. See README.md for the plugin install."
}

if [ "${1:-}" = "xva" ]; then
    case "$XVA_STATUS" in
        installed:*) : ;;
        *)
            echo "This image has no ORE backend: $XVA_STATUS" >&2
            echo "Rebuild on a platform where the wheel resolves, or run" >&2
            echo "the xva command outside the container. Nothing was run." >&2
            exit 69
            ;;
    esac
fi

if writes_files "${1:-}"; then
    if ! mountpoint -q "$ARTIFACTS" 2>/dev/null \
       && [ "$(ls -A "$ARTIFACTS" 2>/dev/null | wc -l)" -eq 0 ]; then
        echo "No volume is mounted at $ARTIFACTS." >&2
        echo "" >&2
        echo "This command writes a file, and that file is what you came" >&2
        echo "for. Without a mount it is written inside this container and" >&2
        echo "lost when the container exits, while the summary on stdout" >&2
        echo "looks exactly like a successful run." >&2
        echo "" >&2
        echo "  docker run --rm -v \"\$PWD/artifacts:/artifacts\" IMAGE ${1:-}" >&2
        echo "" >&2
        echo "Set RISKDESK_ALLOW_EPHEMERAL=1 for a genuinely throwaway run." >&2
        if [ "${RISKDESK_ALLOW_EPHEMERAL:-0}" != "1" ]; then
            exit 64
        fi
        echo "RISKDESK_ALLOW_EPHEMERAL is set: continuing, and what this" >&2
        echo "run writes will be discarded." >&2
    fi
fi

case "${1:-doctor}" in
    doctor|"") doctor ;;
    demo) shift; exec "$HOME_DIR/demo.sh" "$@" ;;
    mcp) shift; exec riskdesk-mcp "$@" ;;
    *) exec riskdesk "$@" ;;
esac
