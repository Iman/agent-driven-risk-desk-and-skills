"""Local MCP tools using the upstream MCP Python SDK."""
from typing import get_args

from mcp.server.fastmcp import FastMCP
from mcp.types import ToolAnnotations
from riskdesk import __version__
from riskdesk import backtest, counterparty, credit, decomposition, derivatives, frtb, limits, liquidity, scenarios
from riskdesk.analytics import tail_risk, portfolio_exposure, stress_test
from riskdesk.models import Provenance, TailRequest, PortfolioRequest, StressRequest
from riskdesk.ore import DATA_MODES, run_ore
from riskdesk.tail_models import tail_models

server = FastMCP("Risk Desk")
READ = ToolAnnotations(readOnlyHint=True, destructiveHint=False, idempotentHint=True, openWorldHint=False)
WRITE = ToolAnnotations(readOnlyHint=False, destructiveHint=False, idempotentHint=False, openWorldHint=False)
# One list, read by risk_desk_status and by the riskdesk-agent answer prompt.
CONVENTIONS = (
    "Report degraded and degraded_reason before any figure.",
    "Loss is positive; a negative VaR, ES or loss is a gain and is not floored at zero.",
    "Amounts are in the stated currency; no FX translation is performed.",
    "Each P&L or return sample already spans the stated horizon and is not rescaled by "
    "square-root-of-time; the one exception is the stated FRTB MAR33.4 liquidity-horizon rule.",
    "Preserve as_of, source, data_mode and input_sha256 when citing a result.",
    "data_mode is the caller's declaration, not a rights certificate; Risk Desk fetches no market data.",
    "Historical loss forecasts are not risk-neutral valuation; regulatory figures are not a submission.",
    "Research software; not investment advice.")


@server.tool(annotations=READ)
async def risk_desk_status() -> dict:
    """Local runtime version, tool list, accepted data modes and reporting conventions. Call first."""
    return dict(status="available", riskdesk_version=__version__, market_data=False,
                tools=sorted(t.name for t in await server.list_tools()),
                data_modes=list(get_args(Provenance.model_fields["data_mode"].annotation)),
                xva_data_modes=list(DATA_MODES),
                conventions=list(CONVENTIONS))


@server.tool(annotations=READ)
def risk_tail(request: TailRequest) -> dict:
    """Historical VaR and ES on supplied horizon P&L. Report degraded status and loss signs before numbers."""
    return tail_risk(request)


@server.tool(annotations=READ)
def risk_tail_models(request: TailRequest) -> dict:
    """VaR and ES side by side: historical, normal, Student-t, EVT, GARCH filtered historical, GARCH-EVT, GARCH-t."""
    return tail_models(request)


@server.tool(annotations=READ)
def risk_backtest(request: backtest.BacktestRequest) -> dict:
    """Backtest a VaR (and optional ES) series against realised P&L: Kupiec, Christoffersen, Basel zone, Z2."""
    return backtest.var_backtest(request)


@server.tool(annotations=READ)
def risk_exposure(request: PortfolioRequest) -> dict:
    """Gross/net exposure and concentration for signed linear positions in one stated base currency."""
    return portfolio_exposure(request)


@server.tool(annotations=READ)
def risk_stress(request: StressRequest) -> dict:
    """Apply explicit asset shocks to all linear positions. No scenario probabilities are inferred."""
    return stress_test(request)


@server.tool(annotations=READ)
def risk_derivatives_greeks(request: derivatives.DerivativesBookRequest) -> dict:
    """Cash delta, gamma, vega, theta and rho of a book of linear positions and European options."""
    return derivatives.book_greeks(request)


@server.tool(annotations=READ)
def risk_derivatives_grid(request: derivatives.ScenarioGridRequest) -> dict:
    """Full revaluation of an options book over a spot and vol shock grid, against delta-gamma-vega."""
    return derivatives.scenario_grid(request)


@server.tool(annotations=READ)
def risk_derivatives_historical(request: derivatives.HistoricalPnlRequest) -> dict:
    """Historical full-revaluation P&L, VaR and ES of an options book under supplied spot and vol moves."""
    return derivatives.historical_pnl(request)


@server.tool(annotations=READ)
def risk_covariance(request: decomposition.CovarianceRequest) -> dict:
    """Sample, EWMA or Ledoit-Wolf covariance, volatility and correlation of a supplied return history."""
    return decomposition.covariance_estimate(request)


@server.tool(annotations=READ)
def risk_var_attribution(request: decomposition.ParametricRequest) -> dict:
    """Parametric normal VaR and ES with Euler contributions and incremental VaR per position."""
    return decomposition.parametric_var(request)


@server.tool(annotations=READ)
def risk_es_attribution(request: decomposition.HistoricalRequest) -> dict:
    """Historical-simulation ES with Euler contributions per position."""
    return decomposition.historical_es(request)


@server.tool(annotations=READ)
def risk_factor_exposure(request: decomposition.FactorRequest) -> dict:
    """Factor betas and the split of portfolio variance into systematic and idiosyncratic parts."""
    return decomposition.factor_exposure(request)


@server.tool(annotations=READ)
def risk_limits(request: limits.LimitRequest) -> dict:
    """Grade a limit set against exposure, tail and stress results already returned by Risk Desk."""
    return limits.check_limits(request)


@server.tool(annotations=READ)
def risk_what_if(request: limits.WhatIfRequest) -> dict:
    """Apply proposed trades to a book, recompute exposure, stress and tail, and grade limits after."""
    return limits.what_if(request)


@server.tool(annotations=READ)
def risk_liquidity(request: liquidity.LiquidityRequest) -> dict:
    """Days to liquidate, holdings by day, spread cost and liquidity-adjusted VaR."""
    return liquidity.liquidity_risk(request)


@server.tool(annotations=READ)
def risk_stress_replay(request: scenarios.ReplayRequest) -> dict:
    """Replay a dated historical window from the caller's own price levels on linear positions."""
    return scenarios.historical_replay(request)


@server.tool(annotations=READ)
def risk_scenario_library() -> dict:
    """The dated historical windows Risk Desk knows, with sources. Dates only; no prices are shipped."""
    return scenarios.scenario_library()


@server.tool(annotations=READ)
def risk_reverse_stress(request: scenarios.ReverseStressRequest) -> dict:
    """The most plausible shock under a supplied covariance that produces a target loss."""
    return scenarios.reverse_stress(request)


@server.tool(annotations=READ)
def risk_scenario_scale(request: scenarios.ScaleRequest) -> dict:
    """Scale a scenario so the book loses a target amount."""
    return scenarios.scale_scenario(request)


@server.tool(annotations=READ)
def risk_saccr(request: counterparty.SaccrRequest) -> dict:
    """Basel SA-CCR exposure at default for one netting set (CRE52), with every intermediate figure."""
    return counterparty.saccr_ead(request)


@server.tool(annotations=READ)
def risk_exposure_profile(request: counterparty.ExposureProfileRequest) -> dict:
    """Peak PFE, EPE, Effective EE and Effective EPE from a simulated exposure profile such as ORE's."""
    return counterparty.exposure_profile_summary(request)


@server.tool(annotations=READ)
def risk_credit_asrf(request: credit.AsrfRequest) -> dict:
    """Vasicek asymptotic single risk factor credit VaR, expected and unexpected loss."""
    return credit.asrf_credit_var(request)


@server.tool(annotations=READ)
def risk_credit_copula(request: credit.CopulaRequest) -> dict:
    """Seeded one-factor Gaussian copula Monte Carlo credit VaR and ES for a finite portfolio."""
    return credit.copula_credit_var(request)


@server.tool(annotations=READ)
def risk_frtb_imcc(request: frtb.ImccRequest) -> dict:
    """FRTB liquidity-adjusted, stress-scaled ES and IMCC from supplied ES figures (MAR33)."""
    return frtb.frtb_imcc(request)


@server.tool(annotations=READ)
def risk_frtb_ima_capital(request: frtb.ImaCapitalRequest) -> dict:
    """FRTB IMA aggregate capital, multiplier, amber-desk surcharge and RWA (MAR33, MAR32.9)."""
    return frtb.frtb_ima_capital(request)


@server.tool(annotations=READ)
def risk_frtb_pla(request: frtb.PlaRequest) -> dict:
    """FRTB P&L attribution test: Spearman and Kolmogorov-Smirnov metrics and the desk zone (MAR32)."""
    return frtb.frtb_pla(request)


@server.tool(annotations=READ)
def risk_frtb_backtest(request: frtb.BacktestRequest) -> dict:
    """FRTB VaR backtesting exception counts at 97.5% and 99%, desk verdict or bank zone (MAR32)."""
    return frtb.frtb_backtest(request)


@server.tool(annotations=READ)
def risk_frtb_sbm_fx(request: frtb.FxSbmRequest) -> dict:
    """FRTB standardised sensitivities-based FX delta and vega capital (MAR21)."""
    return frtb.frtb_sbm_fx(request)


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
