"""Package plugin instructions with the current licence and dependency notices."""
from pathlib import Path
import shutil
from zipfile import ZipFile, ZIP_DEFLATED

root=Path(__file__).resolve().parents[1]
plugin=root/'plugins/risk-desk'
for name in ('LICENSE','THIRD-PARTY.md','dependency-inventory.json','wheel-hashes.json'):
    shutil.copyfile(root/name,plugin/name)
shutil.copytree(root/'notices',plugin/'notices',dirs_exist_ok=True)
target=root/'dist/risk-desk-plugin.zip'
target.parent.mkdir(exist_ok=True)
with ZipFile(target,'w',ZIP_DEFLATED) as archive:
    for path in sorted(plugin.rglob('*')):
        if path.is_file() and not {'__pycache__','.DS_Store'}.intersection(path.parts):
            archive.write(path,path.relative_to(plugin))
with ZipFile(target) as archive:
    assert archive.testzip() is None
    assert 'LICENSE' in archive.namelist()
    assert sum(name.startswith('notices/') for name in archive.namelist())==sum(p.is_file() for p in (root/'notices').rglob('*'))
print(target)
