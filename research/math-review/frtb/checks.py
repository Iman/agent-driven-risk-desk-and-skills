"""Independent checks of riskdesk.frtb: the MAR33.4 liquidity-horizon cascade against the
sqrt(LH/10) closed form, IMCC by hand, PLA metrics by own ranking and empirical CDFs, FX SBM by
hand, and the MAR32.19 desk-limit boundary under the reading recorded in reference.md.
"""
import math
from pathlib import Path
import sys

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from _review import Review  # noqa: E402
from riskdesk import frtb  # noqa: E402  (called for comparison only)

META = dict(as_of="2026-11-04", currency="USD", source="independent math review", data_mode="synthetic")
REF = "plugins/risk-desk/skills/risk-frtb/reference.md"
LH = (10, 20, 40, 60, 120)  # MAR33.4 Table 1 as transcribed at REF:17-18


def lh_es(c):
    return math.sqrt(c[0] ** 2 + sum((c[j] * math.sqrt((LH[j] - LH[j - 1]) / 10)) ** 2 for j in range(1, 5)))


def ranks(x):
    order = sorted(range(len(x)), key=lambda i: x[i])
    out, i = [0.0] * len(x), 0
    while i < len(order):
        j = i
        while j + 1 < len(order) and x[order[j + 1]] == x[order[i]]:
            j += 1
        for k in range(i, j + 1):
            out[order[k]] = (i + j) / 2 + 1
        i = j + 1
    return out


def pearson(a, b):
    ma, mb = sum(a) / len(a), sum(b) / len(b)
    num = sum((x - ma) * (y - mb) for x, y in zip(a, b))
    return num / math.sqrt(sum((x - ma) ** 2 for x in a) * sum((y - mb) ** 2 for y in b))


def ks_count(a, b):
    """Largest gap between the two empirical CDFs, in counts of one observation (0.004 at 250)."""
    return max(abs(sum(x <= v for x in a) - sum(y <= v for y in b)) for v in a + b)


def main():
    r = Review("frtb", "FRTB IMA, PLA, backtesting and FX SBM: independent numerical review", __file__)
    for j, horizon in enumerate(LH):
        cascade = [100.0 if i <= j else 0.0 for i in range(5)]  # every factor has liquidity horizon `horizon`
        r.close(f"cascade-single-lh-{horizon}", f"one-horizon book at LH {horizon} = ES_T sqrt(LH/10)",
                f"MAR33.4 closed form, {REF}:25-27", 100.0 * math.sqrt(horizon / 10),
                frtb.liquidity_adjusted_es(cascade), rel_tol=1e-14)
    mixed = [120.0, 90.0, 70.0, 40.0, 25.0]
    r.close("cascade-mixed", "mixed cascade with weights 1, 1, 2, 2, 6 on the squares", f"{REF}:20-26",
            math.sqrt(120 ** 2 + 90 ** 2 + 2 * 70 ** 2 + 2 * 40 ** 2 + 6 * 25 ** 2),
            frtb.liquidity_adjusted_es(mixed), rel_tol=1e-14)

    sets = dict(portfolio=dict(reduced_stressed=[80, 60, 40, 20, 10], full_current=[100, 70, 50, 20, 10],
                               reduced_current=[90, 65, 45, 20, 8]),
                ir=dict(reduced_stressed=[50, 30, 20, 0, 0], full_current=[40, 30, 10, 0, 0],
                        reduced_current=[45, 32, 12, 0, 0]),
                eq=dict(reduced_stressed=[60, 50, 40, 30, 20], full_current=[70, 50, 40, 30, 25],
                        reduced_current=[50, 40, 30, 20, 15]))
    scaled = {k: lh_es(v["reduced_stressed"]) * max(1.0, lh_es(v["full_current"]) / lh_es(v["reduced_current"]))
              for k, v in sets.items()}  # MAR33.6 ratio floored at 1, applied per class too (REF:43-47)
    out = frtb.frtb_imcc(dict(META, base_horizon_days=10, portfolio=sets["portfolio"],
                              risk_classes=dict(interest_rate=sets["ir"], equity=sets["eq"])))
    r.close("imcc", "IMCC = 0.5 IMCC(C) + 0.5 sum IMCC(C_i), class ratios floored", f"MAR33.15, {REF}:37-47",
            0.5 * scaled["portfolio"] + 0.5 * (scaled["ir"] + scaled["eq"]), out["imcc"], rel_tol=1e-14)

    rng = np.random.default_rng(32)
    hpl = rng.standard_normal(250)
    for name, noise in (("close", 0.2), ("loose", 0.9)):
        rtpl = (hpl + noise * rng.standard_normal(250)).round(3).tolist()
        h = hpl.round(3).tolist()
        out = frtb.frtb_pla(dict(META, desk="D", rtpl=rtpl, hpl=h))
        rho, count = pearson(ranks(rtpl), ranks(h)), ks_count(rtpl, h)
        zone = ("green" if rho > 0.80 and count < 22.5 else "red" if rho < 0.70 or count > 30 else "amber")
        r.close(f"pla-spearman-{name}", "Spearman by own average ranks and Pearson", f"{REF}:106-108", rho,
                out["spearman"], rel_tol=1e-12)
        r.equal(f"pla-ks-{name}", "KS in counts of 0.004 by brute-force empirical CDFs", f"{REF}:109-113",
                count, out["ks_count"])
        r.equal(f"pla-zone-{name}", "zone from MAR32.42 Table 2 thresholds", f"{REF}:114-123", zone, out["zone"])

    for count, var_index, expected in ((12, "99", True), (13, "99", False), (30, "975", True), (31, "975", False)):
        apl = [-2.0] * count + [1.0] * (250 - count)
        quiet = [1.0] * 250
        out = frtb.frtb_backtest(dict(META, level="desk", apl=apl, hpl=quiet,
                                      var_99=[1.0] * 250 if var_index == "99" else [5.0] * 250,
                                      var_975=[1.0] * 250 if var_index == "975" else [5.0] * 250))
        r.equal(f"desk-limit-{var_index}-{count}", f"{count} exceptions at {var_index}: desk passes?",
                f"MAR32.19 read as 'more than 12' and 'more than 30', {REF}:91-99", expected, out["passes"])

    delta = [dict(currency="EUR", sensitivity=1000.0), dict(currency="JPY", sensitivity=-500.0)]
    vega = [dict(currency="EUR", option_maturity_years=1.0, sensitivity=300.0),
            dict(currency="EUR", option_maturity_years=3.0, sensitivity=-120.0)]
    for reduce in (False, True):
        rw = 0.15 / math.sqrt(2) if reduce else 0.15  # USD, EUR and JPY are all specified (REF:147-152)
        ws = [1000.0 * rw, -500.0 * rw]
        rho_v = math.exp(-0.01 * abs(3 - 1) / 1)
        totals = {}
        for scen, gamma, rho in (("low", max(2 * 0.6 - 1, 0.75 * 0.6), max(2 * rho_v - 1, 0.75 * rho_v)),
                                 ("medium", 0.6, rho_v), ("high", min(1.25 * 0.6, 1.0), min(1.25 * rho_v, 1.0))):
            d = math.sqrt(ws[0] ** 2 + ws[1] ** 2 + 2 * gamma * ws[0] * ws[1])
            v = math.sqrt(300.0 ** 2 + 120.0 ** 2 + 2 * rho * 300.0 * -120.0)
            totals[scen] = d + v
        out = frtb.frtb_sbm_fx(dict(META, apply_specified_pair_reduction=reduce, delta=delta, vega=vega))
        r.close(f"sbm-fx-capital-reduce-{reduce}", "FX delta+vega capital, max over three scenarios",
                f"MAR21.4-21.7, MAR21.86-21.95 at {REF}:125-167", max(totals.values()), out["capital"], rel_tol=1e-12)
    return r.write()


if __name__ == "__main__":
    main()
