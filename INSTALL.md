# Install Risk Desk

Seven routes. They are not alternatives to each other in the way a list
suggests: the first installs the software, and most of the rest only tell
an agent where to find it.

**Installing a plugin does not install the runtime.** That is the one
mistake worth avoiding, and it is the reason routes 3, 4 and 6 all start
by pointing at route 1.

| Route | What it gives you | Needs Python |
| --- | --- | --- |
| 1. Installer | The `riskdesk` command, the MCP server, the dashboard | yes |
| 2. Manual checkout | The same, with the steps visible | yes |
| 3. Claude Code plugin | Skills and MCP wiring for Claude Code | yes, first |
| 4. Codex plugin | Skills and MCP wiring for Codex | yes, first |
| 5. Hosted service | Three tools over HTTP, nothing installed | no |
| 6. MCP without a plugin | The tools in any MCP client | yes, first |
| 7. Container | The CLI and the demo with no Python on the host | no |

## Requirements

Git, and a Python the project supports. `pyproject.toml` declares 3.11 or
later. The pinned dependency set and the ORE wheel were tested on CPython
3.13 on macOS ARM64, and CI runs the suite on 3.11, 3.12 and 3.13.

## 1. Full local installer

```sh
git clone https://github.com/Iman/agent-driven-risk-desk-and-skills.git
cd agent-driven-risk-desk-and-skills
./install.sh
./demo.sh
```

`install.sh` creates `.venv`, installs the package with its development
extra, attempts the optional ORE extra and says plainly whether that
worked, then runs the test suite. It writes nothing outside the checkout,
puts nothing on your `PATH`, and registers nothing with any agent runtime.

`demo.sh` runs every command over the example books and prints what each
result means. Both are POSIX sh, print no colour, and exit non-zero on any
failure.

### Installer controls

```sh
./install.sh --help
```

| Flag | Effect |
| --- | --- |
| `--venv DIR` | Environment directory, default `./.venv` |
| `--python BIN` | Interpreter to build the environment with |
| `--no-xva` | Skip the optional ORE extra |
| `--no-tests` | Do not run the suite at the end |

### The optional ORE extra

`riskdesk xva` needs `open-source-risk-engine`, whose wheel exists for a
limited set of Python and platform combinations. The installer attempts it
and reports the outcome rather than failing. Without it you have
historical tail risk, exposure and stress, which is most of the project.

Measured, so you know what to expect: the wheel resolves on macOS ARM64
under CPython 3.13, and on `python:3.13-slim` at linux/amd64. It does not
resolve at linux/arm64, where pip reports no distribution of any version.

## 2. Manual checkout

The same thing with the steps visible:

```sh
git clone https://github.com/Iman/agent-driven-risk-desk-and-skills.git
cd agent-driven-risk-desk-and-skills
python3.13 -m venv .venv
.venv/bin/python -m pip install '.[dev]'
.venv/bin/python -m pip install '.[xva]'   # optional, may not resolve
.venv/bin/python -m pytest -q --color=no
```

Then:

```sh
.venv/bin/riskdesk exposure --input examples/energy_book.json
.venv/bin/riskdesk dashboard                 # http://127.0.0.1:8899
```

## 3. Claude Code plugin

Install the runtime first, by route 1 or 2. Then:

```text
/plugin marketplace add Iman/agent-driven-risk-desk-and-skills
/plugin install risk-desk@risk-desk
```

The plugin declares one stdio MCP server that starts `riskdesk-mcp` through
`PATH`. Either activate `.venv` in the environment that launches the agent,
or point the client at `.venv/bin/riskdesk-mcp` by absolute path.

## 4. Codex plugin

Install the runtime first. Then either configure
`plugins/risk-desk` through a Codex marketplace, or add the server
directly:

```sh
codex mcp add riskdesk -- "$PWD/.venv/bin/riskdesk-mcp"
```

The Codex manifest points at `skills/` and `.mcp.json` in the same
directory. See [docs/OPENAI.md](docs/OPENAI.md) for the hosted variant.

## 5. Hosted service

Nothing to install. `https://riskdesk.avidquant.com/mcp` answers over
Streamable HTTP and needs no login.

It provides three calculation tools and a status tool, serves a synthetic
demo book, and **cannot run `risk_xva`**, because that reads an ORE project
directory on your own machine. For real positions the local install is the
better choice: it computes on your machine and sends nothing anywhere.

Connection settings for ChatGPT and Codex are in
[docs/OPENAI.md](docs/OPENAI.md). What the service does with data you send
it is in [PRIVACY.md](PRIVACY.md).

## 6. MCP without a plugin

Any MCP client can start the server directly. The plugin's own
`plugins/risk-desk/.mcp.json` is the shape:

```json
{
  "mcpServers": {
    "riskdesk": {
      "type": "stdio",
      "command": "riskdesk-mcp",
      "args": []
    }
  }
}
```

Replace `riskdesk-mcp` with the absolute path inside `.venv/bin` if the
client does not inherit your environment. The server speaks stdio, binds
no socket, and makes no market-data or broker request.

## 7. Container

No Python on the host:

```sh
docker build -t risk-desk .
docker run --rm risk-desk                     # what this image can do
docker run --rm --user "$(id -u):$(id -g)" \
    -v "$PWD/artifacts:/artifacts" risk-desk demo
```

`--user` is not decoration. The image runs as a fixed non-root uid, and on
Linux a bind mount keeps the ownership it has on the host, so without it
the container cannot write your directory. Run it without and the
entrypoint refuses with exit 65 and prints the line above.

The image states its own scope. Exit codes: 64 a writing command with no
mount, 65 a mount it cannot write, 66 an artifacts path that does not
exist, 69 `xva` with no ORE backend in this image.

The skills are read by the agent on your host, not by the image, so the
container is a route to the CLI and the demo rather than to an agent
setup.

## Removing it

There is no uninstaller because there is nothing to uninstall. Delete the
checkout. `install.sh` writes only inside it.

If you added an MCP server to an agent runtime, remove that entry too. If
you installed the Claude Code plugin, remove it with
`/plugin uninstall risk-desk`. `pip` leaves its own cache, which is not
this project's to delete.

## If something does not work

`./install.sh` prints the interpreter it chose, the environment it built
and whether the ORE extra installed. Start there.

The most common outcome is an agent that lists no tools, and the cause is
almost always that the plugin was installed without the runtime, or that
`riskdesk-mcp` is not on the `PATH` the agent launches with. Check it
directly:

```sh
.venv/bin/riskdesk-mcp < /dev/null
```

That should start and exit without a traceback. If the command is not
found, route 1 has not been run in that environment.
