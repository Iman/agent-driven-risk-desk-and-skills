"""Reproduce the pinned ORE example with an explicit, self-contained input bundle."""
import argparse
import json
from pathlib import Path
import shutil
import subprocess
import xml.etree.ElementTree as ET
from riskdesk.ore import run_ore

REVISION = "b1f239332fdd51e5c514dd6de34a665fe0ff8326"


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--upstream',required=True,type=Path)
    parser.add_argument('--work',required=True,type=Path)
    args=parser.parse_args()
    revision=subprocess.check_output(['git','rev-parse','HEAD'],cwd=args.upstream,text=True).strip()
    if revision != REVISION:
        raise ValueError('upstream checkout must be ORE v1.8.16.0 at '+REVISION)
    args.work.mkdir(parents=True,exist_ok=False)
    project=args.work/'inputs'
    shutil.copytree(args.upstream/'Examples/ORE-Python/Input',project/'Input')
    shutil.copytree(args.upstream/'Examples/Input',project/'Shared')
    config=project/'Input/ore.xml'
    config.write_text(config.read_text().replace('../../Input/','../Shared/'))
    market=project/'Shared/todaysmarket.xml'
    tree=ET.parse(market)
    for group in tree.findall('Securities'):
        for security in list(group):
            if security.get('name') in ('SECURITY_2','ISIN:XS0983610930'):
                group.remove(security)
    tree.write(market,encoding='unicode')
    result=run_ore(project,'Input/ore.xml',args.work/'output','upstream-example')
    report=result['reports']['xva']['rows']
    assert len(report)==2 and report[1]['MVA'] is None
    assert len(result['reports']['exposure_nettingset_CPTY_A']['rows'])==82
    assert abs(report[0]['CVA']-42600.768114722014)<.001
    assert abs(report[0]['CVA']-report[1]['CVA'])<1e-8
    print(json.dumps({'upstream_revision':revision,'currency':result['currency'],
                      'CVA':report[0]['CVA'],'DVA':report[0]['DVA'],
                      'exposure_dates':82,'errors':result['errors'],
                      'checks':'report translation and pinned numerical regression, not independent model validation'},indent=2))


if __name__=='__main__':
    main()
