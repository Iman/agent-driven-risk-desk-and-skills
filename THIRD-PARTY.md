# Credits and third-party licences

Risk Desk's own code uses PolyForm Noncommercial 1.0.0. Upstream software
retains its own licences, copyright notices and disclaimers.

| Project | Version used | Role | Licence |
| --- | --- | --- | --- |
| skfolio contributors | 1.1.0 | Empirical VaR and CVaR/Expected Shortfall | BSD-3-Clause |
| Open Source Risk Engine, Quaternion/Acadia and contributors | 1.8.16.0 | QuantLib/QuantExt-based simulation, exposure and XVA | Modified BSD; full bundled notice retained |
| MCP Python SDK contributors | 1.30.0 | Local typed MCP transport | MIT |
| Pydantic contributors | Recorded in dependency inventory | Input contracts | MIT |

[dependency-inventory.json](dependency-inventory.json) records the resolved
Python dependency tree from the tested environment. All 47 upstream
distributions had located notice files; 79 unchanged files are retained in
[notices/](notices/), with hashes. These notices travel in the wheel, source
archive and plugin package. Packages are installed separately; their binary
files are not copied into Risk Desk.

The inventory is evidence of the tested environment, not a universal lock
for every platform. It includes certifi's MPL-2.0 material, the dual licence
for python-dateutil, and bundled numerical-library notices. Do not replace
these with the top-level licence label or claim all dependencies are MIT.
Redistribution of modified upstream files or a bundled runtime requires
checking that distribution's full obligations. No such files are modified
or bundled here.

`scripts/ore_smoke.py` reads the ORE v1.8.16.0 examples from an external
checkout, revision `b1f239332fdd51e5c514dd6de34a665fe0ff8326`.
It relocates input references and removes two unused security curves that
lacked spread inputs. Those local fixture changes do not alter the ORE
library. The example market inputs are not distributed with Risk Desk and
are labelled `upstream-example`, not verified historical market data.

Original URLs:

- https://github.com/skfolio/skfolio
- https://github.com/OpenSourceRisk/Engine
- https://github.com/modelcontextprotocol/python-sdk
- https://github.com/pydantic/pydantic

Market-data rights and methodology rights are separate from software
licences. Risk Desk does not distribute ISDA SIMM material or claim rights
to a user's market data. The earlier candidate review under `research/`
is not a list of installed or approved dependencies.
