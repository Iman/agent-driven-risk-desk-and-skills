# Risk Desk submission validation

## Current local draft, 6 November 2026

UNKNOWN: legal enforceability and regulatory applicability remain for qualified
review. The revised hosted controls have not been deployed. Portal acceptance,
review conversations, identity/domain verification and production rendering have
not been checked for this draft. Repository ownership and upstream licences remain
unchanged. Do not treat this record as a compliance attestation.

VERIFIED: the hosted suite executed 356 tests and passed. The public
packaging checks executed 27 tests and passed.
Both browser acknowledgement and data-permission regressions are covered by the
hosted checks. Synthetic demos remain available.

The rebuilt hosted ZIP has 32 files and 12 skills. Every archived file matches
its current source, the archive integrity check passes, and the MCP server declares
`extensions.com.openai.auth.type: "none"`, following the
[authentication reference](https://developers.openai.com/plugins/build/plugins#configure-mcp-authentication).
The import JSON matches its canonical private-repository copy and validates against
the [official schema](https://developers.openai.com/plugins/schemas/chatgpt-app-submission.v1.json).
All 29 tool names and declared annotation values match the local hosted registry.
The import contains 9 positive and 5 negative review specifications. These are not
completed conversation tests.

Artifact digests, byte counts and the check timestamp are in
`dist/risk-desk-openai-validation.json`. The schema copy is
`dist/chatgpt-app-submission.schema.json`. Upload the import JSON, not the schema.
No commit, push, deployment or submission accompanies these local changes.

## Historical record, before these draft changes

The dated evidence below describes earlier builds. Its production and test claims
must not be read as verification of the current working tree.

# OpenAI submission package validation

Checked on 6 November 2026 at 10:51 UTC. Package version: 0.2.0.

The artifacts were rebuilt from the working tree, including the approved
audit changes. They are not a committed release. Rebuilding a hosted
client ZIP does not deploy the analytics service.

## Verified

- `dist/chatgpt-app-submission.json` validates against the current
  [official OpenAI import schema](https://developers.openai.com/plugins/schemas/chatgpt-app-submission.v1.json).
  The schema used is saved as `dist/chatgpt-app-submission.schema.json`.
- The import JSON matches the canonical file in the private hosted-service
  repository. It includes the portal metadata used by the Option Desk
  submission layout, with Risk Desk's own URLs, version and prompts.
- All 29 tool names and annotation values match production MCP discovery
  and the local registry without `risk_xva`. The live input and output
  schemas validate as JSON Schemas.
- Nine positive and three negative review specifications match the hosted
  plugin manifest. These are specifications, not ChatGPT test results.
- Eight distinct tools completed their default requests over MCP. A ninth
  call checked the supplied synthetic exposure fixture. All nine responses
  match their output schemas. Exposure, SA-CCR and credit VaR values match
  the numeric review expectations.
- The public status, privacy, terms and support URLs returned HTTP 200
  with the project's smoke-check user agent.
- `NO_COLOR=1 .venv/bin/python -m pytest -q --color=no tests/test_plugin_manifests.py`
  executed 27 tests: 27 passed. Its packaging test rebuilt the archives.
- `risk-desk-hosted-plugin.zip` contains 31 files and twelve skills.
  `risk-desk-hosted-skills.zip` contains 24 files and twelve skills.
  Every archived file matches its current source, and both ZIP integrity
  checks passed.

Artifact sizes, SHA-256 digests and the check timestamp are recorded in
`dist/risk-desk-openai-validation.json`. Import the submission JSON, not
the schema or validation record.

## Not checked

The ChatGPT review conversations, negative-prompt routing, portal import,
domain ownership challenge and submitter declarations remain unchecked.
Schema validation permits the supplemental portal fields but does not
prove that the portal imports them. No commit, deployment or submission
was performed. The earlier audit changes have not been deployed.

## Authentication declaration correction

The maintainer subsequently uploaded the hosted ZIP. The portal requested
an explicit `extensions.com.openai.auth.type` for its MCP server. The
uploaded `.mcp.json` omitted that declaration; the submission import
JSON's connection notes did not satisfy the package requirement.

The hosted server entry now declares `{"type": "none"}` under
`extensions["com.openai"].auth`, following the
[official authentication reference](https://developers.openai.com/plugins/build/plugins#configure-mcp-authentication).
An assertion added to the existing manifest check failed before the
change. All 27 packaging tests passed afterward and rebuilt the ZIP.
Comparing archive contents confirmed that only `.mcp.json` changed.
The wheel and source distribution were also rebuilt successfully.

The full suite initially hit sandbox restrictions on loopback sockets.
Repeating `NO_COLOR=1 .venv/bin/python -m pytest -q --color=no -rs --tb=short`
with socket permission executed all 818 tests: 818 passed, none skipped,
with one SciPy constant-input warning from the rejection test.

This closes the missing declaration in the local source and archive.
Portal acceptance remains unverified until the corrected ZIP is uploaded.
