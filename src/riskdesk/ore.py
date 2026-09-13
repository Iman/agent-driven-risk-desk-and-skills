"""Run a self-contained ORE input bundle in an isolated Python process."""
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import xml.etree.ElementTree as ET


def prepare_config(project, config, output):
    project, output = Path(project).resolve(), Path(output).resolve()
    config = (project / config).resolve()
    if not config.is_relative_to(project) or not config.is_file():
        raise ValueError("config must be a file within the ORE project")
    if output.is_relative_to(project):
        raise ValueError("output must be outside the input project so inputs remain immutable")
    tree = ET.parse(config)
    if tree.getroot().tag != "ORE":
        raise ValueError("expected an ORE configuration")
    for analytic in ("simulation", "xva"):
        node = tree.find(f"./Analytics/Analytic[@type='{analytic}']/Parameter[@name='active']")
        if node is None or (node.text or "").upper() not in ("Y", "TRUE"):
            raise ValueError("require active simulation and xva; reuse of an old cube is not supported")
    input_node = tree.find("./Setup/Parameter[@name='inputPath']")
    output_node = tree.find("./Setup/Parameter[@name='outputPath']")
    if input_node is None or output_node is None:
        raise ValueError("ORE setup requires inputPath and outputPath")
    inputs = (project / (input_node.text or "")).resolve()
    if not inputs.is_relative_to(project) or not inputs.is_dir():
        raise ValueError("inputPath must be inside project")
    input_names = {"marketDataFile", "fixingDataFile", "curveConfigFile", "conventionsFile",
                   "marketConfigFile", "pricingEnginesFile", "portfolioFile", "calendarAdjustment",
                   "currencyConfiguration", "simulationConfigFile", "csaFile"}
    output_names = {"logFile", "outputFileName", "scenariodump", "cubeFile", "scenarioFile",
                    "aggregationScenarioDataFileName", "rawCubeOutputFile", "netCubeOutputFile"}
    for node in tree.iter("Parameter"):
        name, value = node.get("name"), node.text or ""
        if name in input_names:
            path = (inputs / value).resolve()
            if not path.is_relative_to(project) or not path.is_file():
                raise ValueError("input reference is missing or outside project: " + name)
        if name in output_names and value and (Path(value).name != value or "\\" in value):
            raise ValueError("output filenames must be simple filenames: " + name)
    # No symlinks: the recorded input inventory must describe actual local bytes.
    files = sorted(p for p in project.rglob("*") if p.is_file())
    if any(p.is_symlink() for p in project.rglob("*")):
        raise ValueError("ORE input project must not contain symlinks")
    hashes = {str(p.relative_to(project)): hashlib.sha256(p.read_bytes()).hexdigest() for p in files}
    output.mkdir(parents=True, exist_ok=False)
    input_node.text = str(inputs)
    output_node.text = str(output)
    fail = tree.find("./Setup/Parameter[@name='continueOnError']")
    if fail is None:
        fail = ET.SubElement(tree.find("Setup"), "Parameter", name="continueOnError")
    fail.text = "false"
    target = output / "effective-ore.xml"
    tree.write(target, encoding="unicode")
    return target, hashes


def run_ore(project, config, output, data_mode, timeout=600):
    if data_mode not in ("synthetic", "user-licensed", "upstream-example"):
        raise ValueError("data_mode must be synthetic, user-licensed or upstream-example")
    target, hashes = prepare_config(project, config, output)
    with (target.parent / "worker.log").open("w") as log:
        process = subprocess.run([sys.executable, "-m", "riskdesk.ore_worker", str(target)],
                                 cwd=Path(project).resolve(), stdout=log, stderr=subprocess.STDOUT,
                                 timeout=timeout, check=False)
    if process.returncode:
        raise RuntimeError("ORE failed; inspect " + str(target.parent / "worker.log"))
    result = json.loads((target.parent / "ore-result.json").read_text())
    if result["errors"]:
        raise RuntimeError("ORE reported errors; inspect ore-result.json. No XVA summary accepted.")
    if not result["reports"].get("xva", {}).get("rows"):
        raise RuntimeError("ORE produced no XVA rows")
    result.update(data_mode=data_mode, input_hashes=hashes, degraded=False, degraded_reason=None,
                  assumptions=["Risk-neutral ORE valuation/exposure, not real-world loss forecasting.",
                               "Preserve ORE column names and sign conventions; do not add netting-set and trade rows together.",
                               "No-error execution does not establish calibration quality or regulatory approval."],
                  artifact=str(target.parent / "riskdesk-xva.json"))
    Path(result["artifact"]).write_text(json.dumps(result, indent=2, allow_nan=False)+"\n")
    return result
