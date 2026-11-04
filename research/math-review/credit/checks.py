"""Independent check of riskdesk.credit.asrf_credit_var against the CRE99 Table 1 risk weights.

The Vasicek quantile and the CRE31.5 corporate formulas are written here with the stdlib
NormalDist. CRE99_READ was read from the bis.org CRE99 chapter (version in force 2023-01-01,
published 2020-03-27) on 2026-11-04 in this review, through a web fetch whose summariser split
the flattened table columns; it is kept beside the test copy on purpose, as a second reading of
the same table with its own provenance, and the two are compared below.
"""
import math
from pathlib import Path
from statistics import NormalDist
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from _review import ROOT, Review  # noqa: E402
sys.path.insert(0, str(ROOT / "tests"))
from test_credit import CRE99_TABLE_1  # noqa: E402  (the engineers' transcription, compared only)
from riskdesk.credit import asrf_credit_var  # noqa: E402  (called for comparison only)

META = dict(as_of="2026-11-04", currency="EUR", source="independent math review", data_mode="synthetic",
            horizon_days=365)
SOURCE = ("https://www.bis.org/committees/bcbs/basel-framework/standard/cre/99/inforce/2023-01-01/"
          "published/2020-03-27, Table 1, corporate column, turnover EUR 50 million, M 2.5")
CRE99_READ = {0.0005: 17.47, 0.001: 26.36, 0.0025: 43.97, 0.004: 55.75, 0.005: 61.88, 0.0075: 73.58,
              0.01: 82.06, 0.013: 89.73, 0.015: 93.86, 0.02: 102.09, 0.025: 108.58, 0.03: 114.17,
              0.04: 124.07, 0.05: 133.20, 0.06: 141.88, 0.10: 171.63, 0.15: 196.92, 0.20: 211.76}
N = NormalDist()


def corporate(pd, lgd=0.40):
    """CRE31.5 corporate correlation, maturity factor b, and K per unit EAD at M = 2.5."""
    w = (1 - math.exp(-50 * pd)) / (1 - math.exp(-50))
    rho = 0.12 * w + 0.24 * (1 - w)
    b = (0.11852 - 0.05478 * math.log(pd)) ** 2
    rate = N.cdf((N.inv_cdf(pd) + math.sqrt(rho) * N.inv_cdf(0.999)) / math.sqrt(1 - rho))
    return rho, b, lgd * rate - lgd * pd


def main():
    r = Review("credit", "ASRF credit VaR: independent check against CRE99 Table 1", __file__)
    r.equal("table-readings-agree", "bis.org reading in this review equals the test transcription",
            SOURCE, CRE99_READ, CRE99_TABLE_1, compared="test copy")
    for pd, published in sorted(CRE99_READ.items()):
        rho, b, k = corporate(pd)
        rw = 12.5 * k / (1 - 1.5 * b) * 100
        r.close(f"rw-pd{pd:g}", f"risk weight %, PD {pd:g}, LGD 40%", SOURCE + "; table rounds to 0.01",
                published, rw, abs_tol=0.005, compared="published")
        out = asrf_credit_var(dict(META, confidence=0.999, obligors=[
            dict(id="x", exposure=1.0, pd=pd, lgd=0.40, correlation=rho)]))
        r.close(f"ul-pd{pd:g}", f"module unexpected loss per unit EAD, PD {pd:g}", "CRE31.5 term written here",
                k, out["unexpected_loss"], rel_tol=1e-10)
    return r.write()


if __name__ == "__main__":
    main()
