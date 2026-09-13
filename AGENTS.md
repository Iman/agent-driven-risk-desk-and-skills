# Risk Desk repository guidance

The approved initial scope is historical VaR/Expected Shortfall, linear
portfolio exposure and stress, and the ORE exposure/XVA adapter. The runtime
is under `src/riskdesk`; CLI and MCP use the same functions. Skills live in
`plugins/risk-desk/skills`.

Read README.md, THIRD-PARTY.md and docs/IMPLEMENTATION.md before extending
the models. Preserve loss signs, base currency, horizon, source provenance
and degraded status. Do not equate historical loss forecasts with
risk-neutral valuation. Preserve ORE report levels and unavailable values.

Run `python -m pytest -q --color=no`. Run the pinned ORE example when changing
that adapter. Rebuild the wheel and plugin after packaging or notice changes.
The requirements lock is platform-specific, not a portable environment claim.

Do not add automated authorship or attribution. The repository uses the
user's configured Git identity and a commit-message guard. No upstream
licence is replaced by Risk Desk's own licence.
