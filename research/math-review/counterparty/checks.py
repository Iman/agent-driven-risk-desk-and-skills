"""Independent SA-CCR (CRE52) recomputation, compared with the published CRE99 EADs and with
riskdesk.counterparty.saccr_ead.

The trade inputs are imported from the one copy in tests/test_counterparty.py. The SA-CCR
arithmetic below is written separately from the module. Supervisory constants are CRE52.72
Table 2 as transcribed in reference.md; the CRE99 EADs are images on bis.org and were not
re-read in this review, so the published column rests on the transcription in reference.md.
"""
from collections import defaultdict
import math
from pathlib import Path
from statistics import NormalDist
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from _review import ROOT, Review  # noqa: E402
sys.path.insert(0, str(ROOT / "tests"))
from test_counterparty import EXAMPLE_1, EXAMPLE_2, EXAMPLE_3, WEEKLY  # noqa: E402  (inputs only)
from riskdesk.counterparty import saccr_ead  # noqa: E402  (called for comparison only)

META = dict(as_of="2026-11-04", currency="USD", source="independent math review", data_mode="synthetic")
REF = "plugins/risk-desk/skills/risk-counterparty/reference.md"
PHI = NormalDist().cdf
TEN_DAYS = 10 / 250
SF = dict(interest_rate=0.005, fx=0.04)
VOL = dict(interest_rate=0.50, fx=0.15)
CREDIT_SF = dict(AAA=0.0038, AA=0.0038, A=0.0042, BBB=0.0054, BB=0.0106, B=0.016, CCC=0.06, IG=0.0038, SG=0.0106)


def params(t):
    """(SF, rho, sigma) per CRE52.72 Table 2 as transcribed at REF:59-75."""
    cls = t["asset_class"]
    if cls in SF:
        return SF[cls], None, VOL[cls]
    if cls == "credit":
        index = t.get("index", False)
        return CREDIT_SF[t["rating"]], 0.8 if index else 0.5, 0.8 if index else 1.0
    if cls == "equity":
        return (0.20, 0.8, 0.75) if t.get("index") else (0.32, 0.5, 1.2)
    return (0.40, 0.4, 1.5) if t.get("electricity") else (0.18, 0.4, 0.7)


def effective_notional(t, mpor=None):
    sf, rho, vol = params(t)
    d = t["notional"]
    if t["asset_class"] in ("interest_rate", "credit"):
        d *= max((math.exp(-0.05 * t["start"]) - math.exp(-0.05 * t["end"])) / 0.05, TEN_DAYS)
    mf = 1.5 * math.sqrt(mpor / 250) if mpor else math.sqrt(min(max(t["maturity"], TEN_DAYS), 1.0))
    sign = 1 if t["position"] == "long" else -1
    if "option" in t:
        lam = t.get("shift", 0)
        p, k, x = t["underlying_price"] + lam, t["strike"] + lam, t["exercise"]
        d1 = (math.log(p / k) + 0.5 * vol * vol * x) / (vol * math.sqrt(x))
        sign *= PHI(d1) if t["option"] == "call" else -PHI(-d1)
    return d * mf * sign


def single_factor(entries):
    return math.sqrt(sum(rho * a for a, rho in entries) ** 2 + sum((1 - rho * rho) * a * a for a, rho in entries))


def ead(trades, margined=False, collateral=0.0, threshold=0, minimum_transfer_amount=0, nica=0,
        mpor_business_days=None, **_):
    mpor = mpor_business_days if margined else None
    by_class, addon = defaultdict(list), {}
    for t in trades:
        by_class[t["asset_class"]].append((t, effective_notional(t, mpor)))
    ir = defaultdict(lambda: [0.0, 0.0, 0.0])
    for t, d in by_class["interest_rate"]:
        ir[t["hedging_set"]][0 if t["end"] < 1 else 1 if t["end"] <= 5 else 2] += d
    if ir:
        addon["interest_rate"] = sum(0.005 * math.sqrt(a * a + b * b + c * c + 1.4 * a * b + 1.4 * b * c + 0.6 * a * c)
                                     for a, b, c in ir.values())
    fx = defaultdict(float)
    for t, d in by_class["fx"]:
        fx[t["hedging_set"]] += d
    if fx:
        addon["fx"] = sum(0.04 * abs(v) for v in fx.values())
    for cls in ("credit", "equity"):
        entity = defaultdict(float)
        for t, d in by_class[cls]:
            entity[t["reference"]] += params(t)[0] * d
        if entity:
            rho = {t["reference"]: params(t)[1] for t, _ in by_class[cls]}
            addon[cls] = single_factor([(a, rho[name]) for name, a in entity.items()])
    sets = defaultdict(lambda: defaultdict(float))
    for t, d in by_class["commodity"]:
        sets[t["hedging_set"]][t["reference"]] += params(t)[0] * d
    if sets:
        addon["commodity"] = sum(single_factor([(a, 0.4) for a in types.values()]) for types in sets.values())
    total = sum(addon.values())
    v_c = sum(t["market_value"] for t in trades) - collateral
    rc = max(v_c, threshold + minimum_transfer_amount - nica, 0.0) if margined else max(v_c, 0.0)
    multiplier = min(1.0, 0.05 + 0.95 * math.exp(v_c / (2 * 0.95 * total)))
    result = 1.4 * (rc + multiplier * total)
    if margined:  # CRE52.2 cap, the reading recorded at REF:97-98: same V and C, unmargined MF and RC
        result = min(result, ead(trades, collateral=collateral))
    return result


def run(trades, **terms):
    return saccr_ead(dict(META, netting_set="NS", trades=trades, **terms))


def main():
    r = Review("counterparty", "SA-CCR: independent recomputation against CRE99 and the module", __file__)
    published = [("example-1", EXAMPLE_1, {}, 569, "CRE99.40"), ("example-2", EXAMPLE_2, {}, 381, "CRE99.58"),
                 ("example-3", EXAMPLE_3, {}, 5406, "CRE99.76"),
                 ("example-4", EXAMPLE_1 + EXAMPLE_2, {}, 936, "BCBS 279 Annex 4a"),
                 ("example-5", EXAMPLE_1 + EXAMPLE_3, WEEKLY, 1879, "CRE99.97")]
    for name, trades, terms, value, para in published:
        mine = ead(trades, **terms)
        r.close(f"{name}-published", f"independent EAD vs published (USD thousands, whole-thousand rounding)",
                f"{para} as transcribed at {REF}:84-88; image not re-read", value, mine, abs_tol=0.5,
                compared="published")
        r.close(f"{name}-module", "module EAD vs independent EAD", "CRE52 recomputation in this script",
                mine, run(trades, **terms)["ead"], rel_tol=1e-12)

    # No published worked example exists for these; first principles only (maintainer decision: partially verified).
    fx = [dict(id="f1", asset_class="fx", notional=1000, market_value=10, maturity=0.5, position="long",
               hedging_set="EUR/USD"),
          dict(id="f2", asset_class="fx", notional=400, market_value=-5, maturity=2, position="short",
               hedging_set="EUR/USD"),
          dict(id="f3", asset_class="fx", notional=500, market_value=3, maturity=1, position="long",
               hedging_set="GBP/USD", option="call", underlying_price=1.25, strike=1.30, exercise=0.5)]
    eq = [dict(id="e1", asset_class="equity", notional=800, market_value=20, maturity=1, position="long",
               reference="Firm X"),
          dict(id="e2", asset_class="equity", notional=300, market_value=-4, maturity=0.25, position="short",
               reference="Firm X"),
          dict(id="e3", asset_class="equity", notional=1000, market_value=-15, maturity=3, position="short",
               reference="SPX", index=True)]
    for name, trades in (("fx-no-published-example", fx), ("equity-no-published-example", eq)):
        r.close(name, "module EAD vs independent EAD; constants as transcribed, no published example",
                f"CRE52.59, CRE52.66, CRE52.72 as at {REF}:50-51, 59-75", ead(trades), run(trades)["ead"],
                rel_tol=1e-12)
    ir_option = [dict(id="n1", asset_class="interest_rate", notional=1000, market_value=2, maturity=3,
                      position="long", hedging_set="EUR", start=1, end=3, option="call",
                      underlying_price=-0.002, strike=-0.001, exercise=1, shift=0.01)]
    r.close("negative-rate-shift", "IR option with negative P and K shifted by lambda: module vs independent",
            f"CRE52.40 FAQ2 as read at {REF}:43", ead(ir_option), run(ir_option)["ead"], rel_tol=1e-12)
    short = [dict(id="s1", asset_class="interest_rate", notional=10_000, market_value=5, maturity=0.04,
                  position="long", hedging_set="USD", start=0, end=0.04)]
    terms = dict(margined=True, collateral=0, threshold=0, minimum_transfer_amount=0, nica=0,
                 remargining_period_business_days=10, mpor_business_days=20)
    out = run(short, **terms)
    r.close("margined-cap-binding", "margined EAD capped at the unmargined EAD (cap binds)",
            f"CRE52.2 reading at {REF}:97-98", ead(short, **terms), out["ead"], rel_tol=1e-12)
    r.equal("margined-cap-flag", "module reports the cap as applied", f"{REF}:97-98", True, out["cap_applied"])
    return r.write()


if __name__ == "__main__":
    main()
