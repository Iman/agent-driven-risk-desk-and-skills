# Risk Desk: the CLI and the local MCP server, pinned.
#
# WHAT THIS IMAGE IS FOR. Running the tools without installing Python, and
# getting the same interpreter every time. It is the right choice on a
# machine with no Python, on Windows, and in CI.
#
# WHAT IT CANNOT DO, and this is a large part of the project. The five
# skills are markdown that has to sit where the HOST's agent looks for it,
# because the host's agent is what reads them. The MCP server is a stdio
# process that an agent runtime launches itself, and a runtime outside this
# container cannot launch one inside it without being told how. For those,
# use ./install.sh or the plugin marketplace; see README.md.
#
# THE ORE EXTRA IS PLATFORM DEPENDENT, and this was measured rather than
# assumed. On python:3.13-slim at linux/amd64, pip resolves
# open-source-risk-engine 1.8.16.0. On the same image at linux/arm64, pip
# reports no distribution of any version. So the build attempts the extra,
# records what actually happened in /opt/risk-desk/xva-status, and the
# entrypoint prints that status rather than letting somebody discover it
# from a failing xva run. Build with --build-arg WITH_XVA=require to turn a
# missing extra into a failed build instead.

FROM python:3.13-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    RISKDESK_ARTIFACTS=/artifacts

WORKDIR /src

# The package first, so editing a document does not invalidate the
# dependency layer.
COPY pyproject.toml README.md LICENSE ./
COPY src src

ARG WITH_XVA=auto
RUN set -eu; \
    mkdir -p /opt/risk-desk; \
    python -m pip install --upgrade pip; \
    python -m pip install "."; \
    if [ "$WITH_XVA" = "never" ]; then \
        echo "not attempted: build argument WITH_XVA=never" > /opt/risk-desk/xva-status; \
    elif python -m pip install ".[xva]"; then \
        printf 'installed: %s\n' "$(python -m pip show open-source-risk-engine | sed -n 's/^Version: //p')" > /opt/risk-desk/xva-status; \
    elif [ "$WITH_XVA" = "require" ]; then \
        echo "the ORE extra was required by WITH_XVA=require and did not install" >&2; \
        exit 1; \
    else \
        echo "not available for this image platform; the image ships the core scope" > /opt/risk-desk/xva-status; \
    fi; \
    cat /opt/risk-desk/xva-status

# The examples, the demonstration and the helper scripts travel with the
# image so `docker run IMAGE demo` has something to run over.
COPY examples /opt/risk-desk/examples
COPY scripts /opt/risk-desk/scripts
COPY demo.sh /opt/risk-desk/demo.sh

# The licence, the credits and the disclaimer travel with it too, so anyone
# who exec's in can read what they are running and under what terms.
COPY DISCLAIMER.md LICENSE THIRD-PARTY.md SECURITY.md /opt/risk-desk/
COPY notices /opt/risk-desk/notices

COPY docker-entrypoint.sh /usr/local/bin/docker-entrypoint.sh
RUN chmod +x /usr/local/bin/docker-entrypoint.sh /opt/risk-desk/demo.sh

# Not root. This tool reads files and writes files and opens no socket to
# the outside; none of that needs privileges.
#
# The consequence, which is documented rather than worked around: on Linux
# a bind mount keeps the host's ownership, so writing into a directory
# owned by somebody else fails for this uid. Run with
# --user "$(id -u):$(id -g)". Docker Desktop on macOS remaps that
# ownership and hides the problem, which is how it reached CI unnoticed.
RUN useradd --create-home --uid 10001 desk \
 && mkdir -p /artifacts \
 && chown -R desk:desk /artifacts /opt/risk-desk
USER desk

# No VOLUME instruction, deliberately. Declaring one makes Docker create an
# anonymous volume at run time, so a mount check can never fire, and --rm
# then discards that volume: the exact loss the check exists to prevent,
# made invisible by the instruction meant to advertise it.

ENTRYPOINT ["docker-entrypoint.sh"]
CMD ["doctor"]

LABEL org.opencontainers.image.title="risk desk" \
      org.opencontainers.image.description="Historical VaR and Expected Shortfall, linear exposure, explicit stress and local ORE XVA. Research software, not investment advice." \
      org.opencontainers.image.licenses="PolyForm-Noncommercial-1.0.0" \
      org.opencontainers.image.source="https://github.com/Iman/agent-driven-risk-desk-and-skills"
