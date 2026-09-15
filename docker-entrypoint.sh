#!/bin/sh
# Say what this image can do, and refuse to lose somebody's work quietly.
#
# Three failures this guards against. Two look like success, and the third
# looked like nothing at all.
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
#
# The third is a mount this container cannot write. The image runs as a
# fixed non-root uid, and a bind mount on Linux keeps the host's ownership,
# so writing into a directory owned by somebody else fails with EACCES.
# Docker Desktop on macOS virtualises that ownership away, which is why
# this passed on a laptop and failed on a Linux CI runner at the first
# step that writes. Measured: exit 1, stderr empty, stdout stopping mid
# demo. The fix is --user, and this says so rather than letting Python
# raise into a stream somebody redirected.

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
    # Writable before mounted. A directory that is mounted but owned by
    # another uid is the failure that is hardest to read: the command dies
    # inside Python with EACCES, and a caller that redirects stdout sees an
    # exit code and nothing else.
    if [ ! -d "$ARTIFACTS" ]; then
        echo "There is no directory at $ARTIFACTS." >&2
        echo "RISKDESK_ARTIFACTS points somewhere this image does not have." >&2
        echo "Nothing was run." >&2
        exit 66
    fi
    if [ ! -w "$ARTIFACTS" ]; then
        echo "Cannot write to $ARTIFACTS as uid $(id -u)." >&2
        echo "" >&2
        echo "This image runs as a non-root user on purpose, and a bind" >&2
        echo "mount keeps the ownership it has on the host, so a directory" >&2
        echo "owned by somebody else is not writable here. Run as your own" >&2
        echo "user so the files it writes belong to you:" >&2
        echo "" >&2
        echo "  docker run --rm --user \"\$(id -u):\$(id -g)\" \\" >&2
        echo "      -v \"\$PWD/artifacts:/artifacts\" IMAGE ${1:-}" >&2
        echo "" >&2
        echo "Nothing was run." >&2
        exit 65
    fi
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
