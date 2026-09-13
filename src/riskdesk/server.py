"""Local MCP tools using the upstream MCP Python SDK."""
from mcp.server.fastmcp import FastMCP
from mcp.types import ToolAnnotations
from riskdesk.analytics import tail_risk, portfolio_exposure, stress_test
from riskdesk.models import TailRequest, PortfolioRequest, StressRequest
from riskdesk.ore import run_ore

server = FastMCP("Risk Desk")
READ = ToolAnnotations(readOnlyHint=True, destructiveHint=False, idempotentHint=True, openWorldHint=False)
WRITE = ToolAnnotations(readOnlyHint=False, destructiveHint=False, idempotentHint=False, openWorldHint=False)


@server.tool(annotations=READ)
def risk_tail(request: TailRequest) -> dict:
    """Historical VaR and ES on supplied horizon P&L. Report degraded status and loss signs before numbers."""
    return tail_risk(request)


@server.tool(annotations=READ)
def risk_exposure(request: PortfolioRequest) -> dict:
    """Gross/net exposure and concentration for signed linear positions in one stated base currency."""
    return portfolio_exposure(request)


@server.tool(annotations=READ)
def risk_stress(request: StressRequest) -> dict:
    """Apply explicit asset shocks to all linear positions. No scenario probabilities are inferred."""
    return stress_test(request)


@server.tool(annotations=WRITE)
def risk_xva(project: str, config: str, output: str, data_mode: str) -> dict:
    """Run a trusted local ORE XML project in a worker. Output must be new and outside the input project.

    Requires riskdesk[xva]. Refuses ORE errors and stale-cube reuse. Preserve ORE
    report signs and row levels; risk-neutral XVA is separate from historical VaR.
    """
    return run_ore(project, config, output, data_mode)


def main():
    server.run(transport="stdio")


if __name__ == "__main__":
    main()
