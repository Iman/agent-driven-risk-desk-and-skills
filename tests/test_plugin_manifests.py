"""The plugin manifests, checked against the directories they describe.

A manifest is a promise about files. Nothing in an ordinary build opens it,
so a plugin that names a skill directory which was renamed, or a
marketplace that points at a plugin nobody added, fails for the first
person who tries to install it and for nobody before that.

This file was written because the README pointed at plugins/risk-desk with
no Claude Code manifest and no marketplace behind it, so the one install
route the README implied did not exist.
"""
import json
from pathlib import Path
import re
import subprocess

import pytest

ROOT = Path(__file__).resolve().parent.parent
PLUGINS = ROOT / "plugins"
MARKETPLACE = ROOT / ".claude-plugin" / "marketplace.json"

pytestmark = pytest.mark.validation


def load(path):
    return json.loads(path.read_text(encoding="utf-8"))


def manifest_paths():
    """Every plugin manifest in the repository, by runtime."""
    found = []
    for plugin in sorted(p for p in PLUGINS.iterdir() if p.is_dir()):
        for runtime in (".claude-plugin", ".codex-plugin"):
            path = plugin / runtime / "plugin.json"
            if path.exists():
                found.append((plugin, runtime, path))
    return found


def skill_directories(plugin):
    skills = plugin / "skills"
    if not skills.is_dir():
        return []
    return sorted(p.name for p in skills.iterdir()
                  if p.is_dir() and not p.name.startswith("."))


def test_every_plugin_has_a_manifest_for_both_runtimes():
    """A plugin readable by one runtime and invisible to the other is the
    defect this file exists for."""
    for plugin in sorted(p for p in PLUGINS.iterdir() if p.is_dir()):
        for runtime in (".claude-plugin", ".codex-plugin"):
            assert (plugin / runtime / "plugin.json").exists(), \
                "{} has no {} manifest".format(plugin.name, runtime)


@pytest.mark.parametrize("runtime", [".claude-plugin", ".codex-plugin"])
def test_the_risk_desk_manifest_parses_and_names_itself(runtime):
    manifest = load(PLUGINS / "risk-desk" / runtime / "plugin.json")
    assert manifest["name"] == "risk-desk"
    assert manifest["license"] == "PolyForm-Noncommercial-1.0.0"
    assert manifest["author"]["name"]
    assert re.fullmatch(r"\d+\.\d+\.\d+", manifest["version"])
    assert "not investment advice" in manifest["description"]


def test_the_two_runtimes_describe_the_same_plugin():
    """Two manifests for one plugin that disagree about what it is will
    show a reader two different products depending on their runtime."""
    claude = load(PLUGINS / "risk-desk" / ".claude-plugin" / "plugin.json")
    codex = load(PLUGINS / "risk-desk" / ".codex-plugin" / "plugin.json")
    for key in ("name", "version", "description", "license", "author"):
        assert claude[key] == codex[key], key


def test_the_manifest_version_matches_the_package():
    package = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    declared = re.search(r'^version = "([^"]+)"', package, re.MULTILINE)
    assert declared, "pyproject.toml has no version"
    for _, _, path in manifest_paths():
        assert load(path)["version"] == declared.group(1), str(path)


def test_the_codex_skills_pointer_resolves_to_the_skills_on_disk():
    plugin = PLUGINS / "risk-desk"
    manifest = load(plugin / ".codex-plugin" / "plugin.json")
    pointer = manifest["skills"]
    assert pointer.startswith("./")
    directory = (plugin / pointer.removeprefix("./")).resolve()
    assert directory.is_dir()
    assert directory == (plugin / "skills").resolve()
    assert skill_directories(plugin) == ["risk-portfolio", "risk-setup",
                                         "risk-stress", "risk-tail",
                                         "risk-xva"]


def test_every_skill_directory_declares_its_own_name():
    """The runtime keys skills by the name in the front matter, so a
    directory renamed without its front matter silently ships two names."""
    plugin = PLUGINS / "risk-desk"
    for name in skill_directories(plugin):
        text = (plugin / "skills" / name / "SKILL.md").read_text(
            encoding="utf-8")
        declared = re.search(r"^name:\s*(\S+)\s*$", text, re.MULTILINE)
        assert declared, name
        assert declared.group(1) == name


def test_the_mcp_pointer_resolves_and_names_the_installed_command():
    plugin = PLUGINS / "risk-desk"
    manifest = load(plugin / ".codex-plugin" / "plugin.json")
    pointer = plugin / manifest["mcpServers"].removeprefix("./")
    assert pointer.is_file()
    servers = load(pointer)["mcpServers"]
    assert list(servers) == ["riskdesk"]
    assert servers["riskdesk"]["type"] == "stdio"
    command = servers["riskdesk"]["command"]
    assert command == "riskdesk-mcp"
    scripts = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    assert command + " = " in scripts, "no console script named " + command


def test_the_marketplace_parses_and_points_at_plugins_that_exist():
    marketplace = load(MARKETPLACE)
    assert marketplace["name"] == "risk-desk"
    assert marketplace["plugins"]
    for entry in marketplace["plugins"]:
        source = (ROOT / entry["source"].removeprefix("./")).resolve()
        assert source.is_dir(), entry["source"]
        manifest = source / ".claude-plugin" / "plugin.json"
        assert manifest.exists(), "{} has no Claude manifest".format(
            entry["source"])
        assert load(manifest)["name"] == entry["name"]
        assert entry["category"] == "finance"
        assert "not investment advice" in entry["description"]


# Keep the hosted endpoint consistent across the packaged clients.
ENDPOINT = "https://riskdesk.avidquant.com"
HOSTED_SKILLS = ["risk-portfolio", "risk-stress", "risk-tail"]


def test_the_hosted_manifests_name_one_endpoint_and_only_that_one():
    """A pinned hostname. If the deploy target changes, this fails and the
    change is made deliberately in every file at once."""
    hosted = PLUGINS / "risk-desk-hosted"
    servers = load(hosted / ".mcp.json")["mcpServers"]
    assert list(servers) == ["riskdesk-hosted"]
    assert servers["riskdesk-hosted"]["type"] == "http"
    assert servers["riskdesk-hosted"]["url"] == ENDPOINT + "/mcp"
    codex = load(hosted / ".codex-plugin" / "plugin.json")
    assert codex["interface"]["websiteURL"] == ENDPOINT
    for runtime in (".claude-plugin", ".codex-plugin"):
        manifest = load(hosted / runtime / "plugin.json")
        assert ENDPOINT.removeprefix("https://") in manifest["description"]


def test_no_other_hostname_reaches_the_hosted_plugin():
    """Nothing here should carry a second host, a credential or a token."""
    hosted = PLUGINS / "risk-desk-hosted"
    allowed = (ENDPOINT,
               "https://github.com/Iman/agent-driven-risk-desk-and-skills",
               # The licence text is upstream and stays verbatim.
               "https://polyformproject.org/")
    for path in sorted(hosted.rglob("*")):
        if not path.is_file():
            continue
        if path.parent == hosted / "assets" and path.name in {
                "openai-directory-icon.png", "openai-composer-icon.png"}:
            assert path.read_bytes() == (ROOT / "assets" / path.name).read_bytes()
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            # Any other binary. The branch above pins the two icons the
            # packager generates today by comparing bytes; a third one
            # added later would otherwise crash this scan rather than
            # failing it, which is how it broke once already. A hostname
            # cannot hide in a file that is not text.
            continue
        for found in re.findall(r"https://[^\s\"'),\]]+", text):
            assert found.startswith(allowed), "{}: {}".format(path, found)
        for secret in ("api_key", "apiKey", "Authorization", "Bearer ",
                       "token"):
            assert secret not in text, "{}: {}".format(path, secret)


def test_the_hosted_plugin_states_what_the_endpoint_can_and_cannot_do():
    """A reader who believes the hosted endpoint can do everything the
    local one can is a cost these sentences exist to avoid. Verified live
    on 2026-09-15: / answered 200 and tools/list advertised risk_tail,
    risk_exposure, risk_stress and risk_desk_status."""
    readme = (PLUGINS / "risk-desk-hosted" / "README.md").read_text(
        encoding="utf-8")
    assert "The endpoint is live" in readme
    assert "riskdesk.avidquant.com/mcp" in readme
    assert "synthetic" in readme
    assert "risk_xva" in readme
    root_readme = (ROOT / "README.md").read_text(encoding="utf-8")
    assert "riskdesk.avidquant.com/mcp" in root_readme
    assert "synthetic" in root_readme


def test_the_hosted_plugin_does_not_offer_a_tool_it_cannot_run():
    """XVA reads a local ORE project directory. A remote endpoint cannot,
    so offering it would put a tool in the list that could never work."""
    hosted = PLUGINS / "risk-desk-hosted"
    assert skill_directories(hosted) == HOSTED_SKILLS
    assert not (hosted / "skills" / "risk-xva").exists()
    text = "".join((hosted / "skills" / name / "SKILL.md").read_text(
        encoding="utf-8") for name in HOSTED_SKILLS)
    assert "risk_xva" not in text
    for name in HOSTED_SKILLS:
        body = (hosted / "skills" / name / "SKILL.md").read_text(
            encoding="utf-8")
        assert "not available here" in body, name


def test_the_hosted_skills_are_copies_of_their_sources():
    """Two hand-edited copies drift, and the one nobody opens is the one
    that ships. scripts/package_plugin.py rebuilds these."""
    source = ROOT / "openai-skills"
    assert sorted(p.name for p in source.iterdir()
                  if p.is_dir()) == HOSTED_SKILLS
    for name in HOSTED_SKILLS:
        built = PLUGINS / "risk-desk-hosted" / "skills" / name / "SKILL.md"
        assert built.read_bytes() == (source / name / "SKILL.md").read_bytes(), \
            "{} differs from openai-skills; run scripts/package_plugin.py".format(name)


def test_glama_names_the_maintainer_and_nothing_else():
    glama = load(ROOT / "glama.json")
    assert glama["maintainers"] == ["Iman"]
    assert glama["$schema"].startswith("https://glama.ai/")
    assert set(glama) == {"$schema", "maintainers"}


def test_the_marketplace_lists_every_plugin_directory():
    """A plugin added to the tree and forgotten in the marketplace is
    installable by nobody, and looks fine in a file listing."""
    listed = {entry["name"] for entry in load(MARKETPLACE)["plugins"]}
    on_disk = {p.name for p in PLUGINS.iterdir() if p.is_dir()}
    assert listed == on_disk


def test_the_readme_names_both_runtimes_with_a_command():
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    assert "Claude Code" in readme
    assert "Codex" in readme
    assert "/plugin marketplace add" in readme


# The repository was renamed from a trailing-hyphen form. GitHub redirects,
# so nothing broke on the day, and that is exactly why a stale URL can sit
# in a manifest until a directory indexes it and publishes the dead name.
REPOSITORY = "https://github.com/Iman/agent-driven-risk-desk-and-skills"
# Built rather than written out, so this file does not itself contain the
# string it forbids and need an exemption from its own check.
RETIRED_NAMES = (REPOSITORY.rsplit("/", 1)[-1] + "-",)


def tracked_text_files():
    names = subprocess.run(["git", "ls-files"], capture_output=True,
                           text=True, cwd=str(ROOT)).stdout.split()
    for name in names:
        if name.startswith(("notices/", "plugins/risk-desk/notices/")):
            continue
        path = ROOT / name
        try:
            yield name, path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue


def test_no_tracked_file_names_a_retired_repository():
    """A redirect makes a stale URL invisible until something republishes
    it. One of these was missed by hand in the Dockerfile's image.source
    label, which is precisely what a container index reads."""
    offenders = []
    for name, text in tracked_text_files():
        for retired in RETIRED_NAMES:
            for line, content in enumerate(text.splitlines(), 1):
                if retired in content:
                    offenders.append("{}:{}".format(name, line))
    assert not offenders, "retired repository name in " + ", ".join(offenders)


def test_every_manifest_url_points_at_this_repository():
    for _, _, path in manifest_paths():
        manifest = load(path)
        for key in ("homepage", "repository"):
            if key in manifest:
                assert manifest[key] == REPOSITORY, "{} {}".format(path, key)
        website = manifest.get("interface", {}).get("websiteURL")
        if website and website.startswith("https://github.com/"):
            assert website == REPOSITORY, str(path)


def test_the_readme_and_the_image_label_name_this_repository():
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    assert REPOSITORY + ".git" in readme
    assert "Iman/agent-driven-risk-desk-and-skills`" in readme
    dockerfile = (ROOT / "Dockerfile").read_text(encoding="utf-8")
    assert 'image.source="{}"'.format(REPOSITORY) in dockerfile


def test_the_manifest_icons_a_runtime_will_fetch_exist():
    """A manifest naming an icon that is not in the tree shows a broken
    image wherever a directory renders it, and nothing in a build notices.
    The packager generates these into the plugin, so they have to be
    committed as well as generated."""
    for plugin in ("risk-desk", "risk-desk-hosted"):
        manifest = load(PLUGINS / plugin / ".codex-plugin" / "plugin.json")
        interface = manifest.get("interface", {})
        for key in ("logo", "composerIcon"):
            reference = interface.get(key)
            if reference is None:
                continue
            target = PLUGINS / plugin / reference.removeprefix("./")
            assert target.is_file(), "{} {} -> {}".format(plugin, key,
                                                          reference)
            assert target.stat().st_size > 0
            tracked = subprocess.run(
                ["git", "ls-files", "--error-unmatch", str(target)],
                capture_output=True, cwd=str(ROOT))
            assert tracked.returncode == 0, \
                "{} is generated but not committed".format(target)
