---
name: risk-setup
description: Install and verify the Risk Desk runtime when its CLI or MCP tools are missing. Use for setup, not risk analysis.
---

# Risk Setup

Install the runtime from the user's actual Risk Desk checkout with `python -m pip install .` in their chosen environment. Add `python -m pip install '.[xva]'` for the optional ORE backend. Do not guess a public repository URL.

The runtime needs `optiondesk-engine` 0.3.0, which is not on a package index. If pip reports `No matching distribution found for optiondesk-engine`, follow the Option Desk engine section of INSTALL.md: build the wheel from the recorded option-desk commit, check its sha256 against `wheel-hashes.json`, and point pip at it with `PIP_FIND_LINKS`. Do not install another build of the same version number, and do not copy the engine's source into the checkout.

Verify `riskdesk --help` and the local example commands described in the repository README. Over MCP, call `risk_desk_status`: it returns the installed version and every registered tool. The plugin starts `riskdesk-mcp` through PATH, so install the runtime in the environment used by the client. A plugin manifest alone does not install Python packages.

If the ORE wheel is unavailable for the platform, report that limitation and use the documented upstream build route; do not substitute another package named ore. No broker credentials or market-data access are needed for synthetic examples.
