"""ORE process boundary: native global settings and logs stay in this worker."""
import json
import math
from pathlib import Path
import sys


def execute(config):
    try:
        import ORE
    except ImportError as exc:
        raise RuntimeError("Install riskdesk[xva] for the ORE backend") from exc
    params = ORE.Parameters()
    params.fromFile(str(config))
    app = ORE.OREApp(params, False)
    app.run()
    reports = {}
    getters = {0:"dataAsSize", 1:"dataAsReal", 2:"dataAsString", 3:"dataAsDate", 4:"dataAsPeriod"}
    for name in app.getReportNames():
        if name != "xva" and not name.startswith("exposure_"):
            continue
        report = app.getReport(name)
        columns = [report.header(i) for i in range(report.columns())]
        values = []
        for i in range(report.columns()):
            kind = report.columnType(i)
            entries = list(getattr(report, getters[kind])(i))
            if kind == 3:
                entries = [entry.ISO() for entry in entries]
            elif kind == 4:
                entries = [str(entry) for entry in entries]
            elif kind == 1:
                # ORE's Null<Real> sentinel represents an unavailable/disabled measure.
                entries = [None if entry == ORE.nullDouble() else entry for entry in entries]
            values.append(entries)
        reports[name] = {"columns": columns, "rows": [dict(zip(columns, row)) for row in zip(*values)]}
    import xml.etree.ElementTree as ET
    tree = ET.parse(config)
    flags = {p.get("name"):p.text for p in tree.findall("./Analytics/Analytic[@type='xva']/Parameter")}
    result = dict(backend="Open Source Risk Engine", backend_version=app.version(),
                  currency=flags.get("baseCurrency"),
                  as_of=tree.findtext("./Setup/Parameter[@name='asofDate']"),
                  requested_xva_flags={k:v for k,v in flags.items() if k in
                      ("cva", "dva", "fva", "colva", "collateralFloor", "mva", "kva")},
                  backend_git_hash=app.gitHash(), errors=list(app.getErrors()), reports=reports)
    app.closeLog()
    (Path(config).parent / "ore-result.json").write_text(json.dumps(result, indent=2, allow_nan=False)+"\n")


if __name__ == "__main__":
    execute(sys.argv[1])
