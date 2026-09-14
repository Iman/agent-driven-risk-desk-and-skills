#!/usr/bin/env python3
"""Break the analytics on purpose and check that the tests notice.

WHY THIS EXISTS. A green suite proves the tests ran, not that they can
fail. Everything this project measures is a signed monetary quantity, and
the failures that matter most are the quiet ones: a sign the wrong way
round, a quantile one observation out, gross counted as net, a validation
rule that stopped rejecting anything. All four keep the suite green if
nothing asserts on them, and all four are wrong in a way a reader of the
output cannot see.

    python3 scripts/mutate.py             every mutation
    python3 scripts/mutate.py --list      what it would try
    python3 scripts/mutate.py --only sign

Each mutation is applied to a copy of the file, the named tests are run,
and the mutation is DETECTED if they fail and SURVIVED if they pass. A
survivor is a hole in the suite, not a bug in the code. SKIPPED means the
pattern is no longer in the source, which means the code moved and the
mutation is proving nothing: it is reported separately and it is not a
pass.

Two traps this harness avoids. Bytecode is disabled with -B and
PYTHONDONTWRITEBYTECODE, because two mutations of one file that produce
identical byte counts within the same second can otherwise reuse a stale
pyc and run code that is no longer on disk. And the original file is
restored in a finally block, so an interrupted run does not leave the tree
mutated.
"""
import argparse
import os
from pathlib import Path
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parent.parent

# Mutations that change no behaviour a test could honestly assert on.
# Declaring a mutant equivalent is a way of hiding a hole, so each entry
# here carries the measurement that justifies it rather than an argument.
EQUIVALENT = {
    "quantile-boundary-inclusive":
        "measured 2026-09-15 over 199,500 (count, confidence) pairs, count "
        "2 to 400 and confidence 0.500 to 0.999: the selected VaR "
        "observation never differs, and Expected Shortfall differs by at "
        "most 4.09e-16 relative. Killing it would mean asserting a "
        "last-bit float.",
    "quantile-boundary-always-shifted":
        "measured over the same 199,500 pairs: the selected VaR "
        "observation never differs, and Expected Shortfall differs by at "
        "most 4.43e-16 relative. The conditional states the intent, that "
        "only a boundary demonstrably rounded the wrong way is moved; on "
        "this grid the unconditional shift is indistinguishable from it.",
}

ANALYTICS = "src/riskdesk/analytics.py"
MODELS = "src/riskdesk/models.py"
RISK = "tests/test_risk.py"
EXAMPLES = "tests/test_examples.py"

# name, file, what to find, what to replace it with, which tests must fail
MUTATIONS = [
    # ---- signs. Loss is positive here; a flipped sign reads as a profit.
    ("var-sign", ANALYTICS,
     "result.update(var=float(value_at_risk(returns, beta=backend_confidence))*request.portfolio_value,",
     "result.update(var=-float(value_at_risk(returns, beta=backend_confidence))*request.portfolio_value,",
     RISK),
    ("es-sign", ANALYTICS,
     "expected_shortfall=float(cvar(returns, beta=backend_confidence))*request.portfolio_value,",
     "expected_shortfall=-float(cvar(returns, beta=backend_confidence))*request.portfolio_value,",
     RISK),
    ("var-floored-at-zero", ANALYTICS,
     "result.update(var=float(value_at_risk(returns, beta=backend_confidence))*request.portfolio_value,",
     "result.update(var=max(0.0, float(value_at_risk(returns, beta=backend_confidence))*request.portfolio_value),",
     RISK),
    ("stress-loss-sign", ANALYTICS,
     "rows.append(dict(name=scenario.name, pnl=pnl, loss=-pnl,",
     "rows.append(dict(name=scenario.name, pnl=pnl, loss=pnl,",
     RISK),
    ("stressed-nav-sign", ANALYTICS,
     "stressed_nav=request.nav+pnl,",
     "stressed_nav=request.nav-pnl,",
     RISK),

    # ---- the quantile boundary, which is where an off-by-one hides.
    ("quantile-boundary-not-corrected", ANALYTICS,
     "        backend_confidence = math.nextafter(request.confidence, 1.0)",
     "        backend_confidence = request.confidence",
     RISK),
    ("quantile-boundary-inclusive", ANALYTICS,
     "            and count*(1-request.confidence) > tail_mass):",
     "            and count*(1-request.confidence) >= tail_mass):",
     RISK),
    ("quantile-boundary-always-shifted", ANALYTICS,
     "    if (exact_mass == exact_mass.to_integral_value()\n"
     "            and count*(1-request.confidence) > tail_mass):",
     "    if True:",
     RISK),
    ("tail-mass-from-binary-float", ANALYTICS,
     "    exact_mass = Decimal(count) * (1 - Decimal(str(request.confidence)))",
     "    exact_mass = Decimal(count * (1 - request.confidence))",
     RISK),

    # ---- normalisation. Both the divide and the multiply back, because
    # dropping either leaves a number with the wrong unit, not an error.
    ("pnl-not-normalised", ANALYTICS,
     "    returns = np.asarray(request.pnl) / request.portfolio_value",
     "    returns = np.asarray(request.pnl, dtype=float)",
     RISK),
    ("var-not-rescaled", ANALYTICS,
     "result.update(var=float(value_at_risk(returns, beta=backend_confidence))*request.portfolio_value,",
     "result.update(var=float(value_at_risk(returns, beta=backend_confidence)),",
     RISK),
    ("overflow-guard-removed", ANALYTICS,
     "    if not np.isfinite(returns).all():",
     "    if False:",
     RISK),

    # ---- gross against net, and what leverage is divided by.
    ("gross-counts-signed-values", ANALYTICS,
     "        gross_by_asset[position.asset] += abs(position.market_value)",
     "        gross_by_asset[position.asset] += position.market_value",
     RISK),
    ("net-counts-absolute-values", ANALYTICS,
     "        net_by_asset[position.asset] += position.market_value",
     "        net_by_asset[position.asset] += abs(position.market_value)",
     RISK),
    ("gross-leverage-divided-by-net", ANALYTICS,
     "gross_leverage=gross/request.nav,",
     "gross_leverage=gross/net,",
     RISK),
    ("net-leverage-divided-by-gross", ANALYTICS,
     "                  net_leverage=net/request.nav,",
     "                  net_leverage=net/gross,",
     RISK),
    ("concentration-share-of-net", ANALYTICS,
     "gross_shares={asset: amount/gross if gross else 0.0",
     "gross_shares={asset: amount/net if net else 0.0",
     RISK),
    ("short-position-stressed-as-long", ANALYTICS,
     "        contributions = {p.id: p.market_value*scenario.shocks[p.asset] for p in request.positions}",
     "        contributions = {p.id: abs(p.market_value)*scenario.shocks[p.asset] for p in request.positions}",
     RISK),

    # ---- the degraded flag, which every caller is told to read first.
    ("degraded-never-set", ANALYTICS,
     "degraded=bool(warnings),",
     "degraded=False,",
     RISK),
    ("degraded-reason-dropped", ANALYTICS,
     'degraded_reason="; ".join(warnings) if warnings else None,',
     "degraded_reason=None,",
     EXAMPLES),
    ("small-sample-threshold-widened", ANALYTICS,
     "] if tail_mass < 20 else []",
     "] if tail_mass < 26 else []",
     EXAMPLES),
    ("input-hash-is-a-constant", ANALYTICS,
     "input_sha256=hashlib.sha256(\n"
     "                    json.dumps(raw, sort_keys=True, allow_nan=False).encode()).hexdigest(),",
     'input_sha256="0"*64,',
     RISK),

    # ---- the validation rules. Each one turned off silently accepts an
    # input the contract says is unusable.
    ("missing-asset-shock-accepted", MODELS,
     "            if set(scenario.shocks) != assets:",
     "            if False:",
     RISK),
    ("duplicate-position-ids-accepted", MODELS,
     "        if len({p.id for p in self.positions}) != len(self.positions):",
     "        if False:",
     RISK),
    ("duplicate-scenario-names-accepted", MODELS,
     "        if len({s.name for s in self.scenarios}) != len(self.scenarios):",
     "        if False:",
     RISK),
    ("shock-worse-than-total-loss-accepted", MODELS,
     "            if any(value < -1 for value in scenario.shocks.values()):",
     "            if False:",
     RISK),
    ("options-accepted-as-linear", MODELS,
     '    instrument_type: Literal["linear"]',
     '    instrument_type: Literal["linear", "option"]',
     RISK),
    ("unknown-fields-accepted", MODELS,
     '    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)',
     '    model_config = ConfigDict(extra="ignore", allow_inf_nan=False)',
     RISK),
    ("nonfinite-numbers-accepted", MODELS,
     '    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)',
     '    model_config = ConfigDict(extra="forbid", allow_inf_nan=True)',
     RISK),
    ("confidence-of-one-accepted", MODELS,
     "    confidence: float = Field(gt=0, lt=1)",
     "    confidence: float = Field(gt=0, le=1)",
     RISK),
    ("zero-portfolio-value-accepted", MODELS,
     "    portfolio_value: float = Field(gt=0)",
     "    portfolio_value: float = Field(ge=0)",
     RISK),
    ("single-observation-accepted", MODELS,
     "    pnl: list[float] = Field(min_length=2, max_length=1_000_000)",
     "    pnl: list[float] = Field(min_length=1, max_length=1_000_000)",
     RISK),
    ("zero-horizon-accepted", MODELS,
     "    horizon_days: int = Field(gt=0, le=3650, strict=True)",
     "    horizon_days: int = Field(ge=0, le=3650, strict=True)",
     RISK),
]


def interpreter():
    candidate = ROOT / ".venv" / "bin" / "python"
    return str(candidate) if candidate.exists() else sys.executable


def run_tests(target, python):
    environment = dict(os.environ, PYTHONDONTWRITEBYTECODE="1")
    finished = subprocess.run(
        [python, "-B", "-m", "pytest", target, "-q", "--no-header",
         "--color=no", "-p", "no:cacheprovider", "-x"],
        cwd=str(ROOT), capture_output=True, text=True, env=environment,
        timeout=900)
    return finished.returncode == 0, finished.stdout.strip().splitlines()


def _clear_bytecode():
    for cache in ROOT.rglob("__pycache__"):
        if ".venv" in str(cache):
            continue
        for item in cache.glob("*.pyc"):
            item.unlink(missing_ok=True)


def apply_one(name, relative, find, replace, tests, python):
    path = ROOT / relative
    original = path.read_text(encoding="utf-8")
    if find not in original:
        return "SKIPPED", "pattern not present: {}".format(find[:40])
    mutated = original.replace(find, replace, 1)
    if mutated == original:
        return "SKIPPED", "replacement changed nothing"
    try:
        path.write_text(mutated, encoding="utf-8")
        passed, output = run_tests(tests, python)
    finally:
        path.write_text(original, encoding="utf-8")
        _clear_bytecode()
    if not passed:
        return "DETECTED", output[-1] if output else "tests failed"

    # The named file is the fast check and the one that ought to catch it.
    # Before calling anything a survivor, run the whole suite, because
    # "this file does not catch it" and "nothing catches it" are different
    # claims and only the second is a hole.
    try:
        path.write_text(mutated, encoding="utf-8")
        passed_all, all_output = run_tests("tests", python)
    finally:
        path.write_text(original, encoding="utf-8")
        _clear_bytecode()
    if not passed_all:
        return "ELSEWHERE", (all_output[-1] if all_output
                             else "caught by the wider suite")
    if name in EQUIVALENT:
        return "EQUIVALENT", EQUIVALENT[name][:52]
    return "SURVIVED", output[-1] if output else "tests passed"


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--list", action="store_true",
                        help="print the mutations and exit")
    parser.add_argument("--only", help="run mutations whose name contains this")
    args = parser.parse_args(argv)

    if args.list:
        for name, relative, _, _, tests in MUTATIONS:
            print("{:38} {:28} {}".format(name, relative, tests))
        print("{} mutations".format(len(MUTATIONS)))
        return 0

    python = interpreter()
    chosen = [m for m in MUTATIONS if not args.only or args.only in m[0]]
    print("mutating with {}".format(python))
    print("{} mutations\n".format(len(chosen)))

    results = []
    for name, relative, find, replace, tests in chosen:
        started = time.time()
        verdict, detail = apply_one(name, relative, find, replace, tests,
                                    python)
        results.append((name, verdict))
        print("{:38} {:9} {:>6.1f}s  {}".format(
            name, verdict, time.time() - started, detail[:52]))

    def named(verdict):
        return [name for name, result in results if result == verdict]

    survived, skipped = named("SURVIVED"), named("SKIPPED")
    elsewhere, equivalent = named("ELSEWHERE"), named("EQUIVALENT")
    print()
    print("{} detected by the named file, {} detected elsewhere in the "
          "suite, {} equivalent, {} survived, {} skipped".format(
              len(named("DETECTED")), len(elsewhere), len(equivalent),
              len(survived), len(skipped)))
    if equivalent:
        print("{} equivalent mutant(s), which change no behaviour a test "
              "could honestly assert on:".format(len(equivalent)))
        for name in equivalent:
            print("  {}: {}".format(name, EQUIVALENT[name]))
    if elsewhere:
        print("caught, but not by the file named for them: {}".format(
            ", ".join(elsewhere)))
    if skipped:
        print("skipped mutations no longer match the source, which means "
              "the code moved: {}".format(", ".join(skipped)))
    if survived:
        print("SURVIVORS, each one a hole in the suite: {}".format(
            ", ".join(survived)))
        return 1
    return 0 if not skipped else 2


if __name__ == "__main__":
    raise SystemExit(main())
