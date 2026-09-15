"""Package plugin instructions with the current licence and dependency notices."""
from pathlib import Path
import shutil
from zipfile import ZipFile, ZIP_DEFLATED

root=Path(__file__).resolve().parents[1]
plugin=root/'plugins/risk-desk'
hosted=root/'plugins/risk-desk-hosted'
for name in ('LICENSE','THIRD-PARTY.md','dependency-inventory.json','wheel-hashes.json'):
    shutil.copyfile(root/name,plugin/name)
shutil.copytree(root/'notices',plugin/'notices',dirs_exist_ok=True)

# The hosted plugin's skills are copies of openai-skills/. Two hand-edited
# copies of the same instructions drift, and the one nobody opens is the
# one that ships, so the copies are rebuilt here and a validation test
# fails the suite if they stop matching.
if (root/'openai-skills').is_dir():
    shutil.rmtree(hosted/'skills',ignore_errors=True)
    shutil.copytree(root/'openai-skills',hosted/'skills',
                    ignore=shutil.ignore_patterns('.DS_Store','__pycache__'))
    shutil.copyfile(root/'LICENSE',hosted/'LICENSE')
target=root/'dist/risk-desk-plugin.zip'
target.parent.mkdir(exist_ok=True)
def publishable(path):
    """Files that belong in the package.

    The same predicate decides what goes in and what the count below
    expects. They used to disagree: the writer skipped .DS_Store and the
    assertion counted every file under notices/, so a single stray macOS
    file made this script fail on its own output.
    """
    return path.is_file() and not {'__pycache__','.DS_Store'}.intersection(path.parts)


with ZipFile(target,'w',ZIP_DEFLATED) as archive:
    for path in sorted(plugin.rglob('*')):
        if publishable(path):
            archive.write(path,path.relative_to(plugin))
with ZipFile(target) as archive:
    assert archive.testzip() is None
    assert 'LICENSE' in archive.namelist()
    assert sum(name.startswith('notices/') for name in archive.namelist())==sum(
        publishable(p) for p in (root/'notices').rglob('*'))
    for runtime in ('.claude-plugin/plugin.json','.codex-plugin/plugin.json','.mcp.json'):
        assert runtime in archive.namelist(), runtime
print(target)

# Package the hosted client independently of the local runtime plugin.
hosted_target = root / 'dist/risk-desk-hosted-plugin.zip'
with ZipFile(hosted_target, 'w', ZIP_DEFLATED) as archive:
    for path in sorted(hosted.rglob('*')):
        if publishable(path):
            archive.write(path, path.relative_to(hosted))
with ZipFile(hosted_target) as archive:
    assert archive.testzip() is None
    for required in ('LICENSE', '.codex-plugin/plugin.json', '.mcp.json'):
        assert required in archive.namelist(), required
print(hosted_target)
