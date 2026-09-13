---
name: risk-setup
description: Install and verify the Risk Desk runtime when its CLI or MCP tools are missing. Use for setup, not risk analysis.
---

# Risk Setup

Install the runtime from the user's actual Risk Desk checkout with `python -m pip install .` in their chosen environment. Add `python -m pip install '.[xva]'` for the optional ORE backend. Do not guess a public repository URL.

Verify `riskdesk --help` and the three local example commands described in the repository README. The plugin starts `riskdesk-mcp` through PATH, so install the runtime in the environment used by the client. A plugin manifest alone does not install Python packages.

If the ORE wheel is unavailable for the platform, report that limitation and use the documented upstream build route; do not substitute another package named ore. No broker credentials or market-data access are needed for synthetic examples.
