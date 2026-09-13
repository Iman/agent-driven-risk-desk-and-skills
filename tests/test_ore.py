import json
from pathlib import Path
from types import SimpleNamespace
import pytest
from riskdesk.ore import prepare_config, run_ore


def project(tmp_path):
    root=tmp_path/'project';(root/'Input').mkdir(parents=True)
    (root/'Input/ore.xml').write_text('''<ORE><Setup>
    <Parameter name="inputPath">Input</Parameter><Parameter name="outputPath">Output</Parameter>
    </Setup><Analytics><Analytic type="simulation"><Parameter name="active">Y</Parameter></Analytic>
    <Analytic type="xva"><Parameter name="active">Y</Parameter></Analytic></Analytics></ORE>''')
    return root


def test_config_must_generate_fresh_cube_and_preserve_input(tmp_path):
    root=project(tmp_path);before=(root/'Input/ore.xml').read_bytes()
    config, hashes=prepare_config(root,'Input/ore.xml',tmp_path/'output')
    assert config.exists() and 'Input/ore.xml' in hashes
    assert (root/'Input/ore.xml').read_bytes()==before
    with pytest.raises(FileExistsError):prepare_config(root,'Input/ore.xml',tmp_path/'output')


def test_inactive_simulation_cannot_import_a_stale_cube(tmp_path):
    root=project(tmp_path);p=root/'Input/ore.xml';p.write_text(p.read_text().replace('>Y<','>N<'))
    with pytest.raises(ValueError):prepare_config(root,'Input/ore.xml',tmp_path/'out')


def test_path_outside_project_is_refused(tmp_path):
    root=project(tmp_path)
    with pytest.raises(ValueError):prepare_config(root,'../outside.xml',tmp_path/'out')
    with pytest.raises(ValueError):prepare_config(root,'Input/ore.xml',root/'out')


def test_backend_errors_never_produce_accepted_xva(tmp_path,monkeypatch):
    root=project(tmp_path);out=tmp_path/'out'
    def worker(*args,**kwargs):
        (out/'ore-result.json').write_text(json.dumps({'errors':['missing spread'], 'reports':{'xva':{'rows':[{}]}}}))
        return SimpleNamespace(returncode=0)
    monkeypatch.setattr('riskdesk.ore.subprocess.run',worker)
    with pytest.raises(RuntimeError,match='reported errors'):run_ore(root,'Input/ore.xml',out,'synthetic')
    assert not (out/'riskdesk-xva.json').exists()
