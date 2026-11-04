# Independent numerical review of the Risk Desk models

Each area recomputes key results from first principles (stdlib arithmetic, exact binomial sums, numerical
integration, brute-force search, or a separate implementation of the regulatory formula) and calls the module
under review only to compare. A published figure is used where one exists and could be located. The model ids
and statuses are in [docs/models/INVENTORY.md](../../docs/models/INVENTORY.md); interpretations are in
[docs/models/ASSUMPTIONS.md](../../docs/models/ASSUMPTIONS.md).

## Rerun everything

From the repository root, in the project environment:

    python research/math-review/run_all.py
    python docs/models/build_assumptions.py
    python -m pytest tests/test_governance.py -q --color=no

The first command runs every area, rewrites each `numerical-results.json` and `report.md`, and writes
[manifest.json](manifest.json); it exits 1 if any check fails. The second regenerates the assumptions register
from the functions' returned `assumptions` lists. The third is the staleness gate: it fails when a model module
has no inventory row, or when any reviewed module differs from the sha256 recorded in the manifest.

## Areas

| Folder | Module under review | What the reference is |
|---|---|---|
| [backtest](backtest/report.md) | backtest.py | exact binomial CDF (fractions) for the MAR99 traffic light and zone starts at T = 250, 500, 1000; hand Kupiec and Christoffersen likelihood ratios with stdlib chi-square tails; hand Z2; a separate 20,000-draw simulation of the Z2 null |
| [tail](tail/report.md) | analytics.py, tail_models.py | hand order statistic and fractional tail mass; normal ES by quadrature of the quantile; Student-t ES by integrating the density; EVT VaR put back into McNeil and Frey eq. (9) and ES by integrating the GPD survival; hand GARCH filter recursion |
| [counterparty](counterparty/report.md) | counterparty.py | a separate CRE52 implementation, against the five CRE99 and BCBS 279 EADs and against the module; FX, equity, negative-rate and margined-cap cases against the module only |
| [credit](credit/report.md) | credit.py | CRE99 Table 1 corporate risk weights (read from bis.org on 2026-11-04) from a stdlib CRE31.5 implementation |
| [decomposition](decomposition/report.md) | decomposition.py | loops for portfolio variance, quadrature for normal ES, central differences for Euler components, full recomputation for incremental VaR, sorted-loss ES and components, covariance loops and EWMA recursion, OLS by normal equations |
| [scenarios](scenarios/report.md) | scenarios.py | grid plus ternary search along the equal-loss line with an explicit 2x2 inverse, unbounded and with a binding floor; scaling multiple by hand |
| [frtb](frtb/report.md) | frtb.py | sqrt(LH/10) closed form for one-horizon books; weighted squares; hand IMCC; own average ranks and empirical CDFs for PLA; MAR32.19 boundary; hand FX SBM over three scenarios |
| [derivatives](derivatives/report.md) | derivatives.py | own BSM and Black-76 prices (stdlib NormalDist) and central differences in the rate |
| [liquidity](liquidity/report.md) | liquidity.py | hand days to liquidate, Bangia et al. cost, day-by-day schedule, order-statistic VaR plus cost |

limits.py and ore.py are hashed in the manifest but have no area: limits.py is rule evaluation without
numerical content beyond comparisons, and ore.py adapts an external engine whose numbers this repository does
not check (INVENTORY.md M13, M29).

## Tolerances

Each tolerance is fixed by the precision of its reference, not by the observed difference: relative 1e-12 to
1e-9 for closed-form arithmetic in double precision; relative 1e-7 to 1e-9 for quadrature, finite differences
and search, and absolute 1e-6 for the searched reverse-stress shocks; half the last printed digit for published
tables (0.005 percentage points for CRE99 Table 1, 0.5 thousand for CRE99 EADs), and exact equality after
rounding for the two-decimal MAR99 Table 2 percentages; four combined standard errors for the simulated Z2
p-value. Each row of every report.md shows its own tolerance. A failed check is recorded as
FAIL and reported; tolerances are not widened to make a check pass.

One check was replaced during the review, and is recorded here rather than dropped silently. In tail/, the
first version asserted that the Option Desk GARCH-t posterior converges on a seeded i.i.d. t(4) sample. It did
not converge, and the check failed. The module does not promise convergence: it promises a degraded flag when
convergence fails (src/riskdesk/tail_models.py:125-127). The check now tests that flag, and the observed
non-convergence is printed in its description.

## What this review does not establish

- Fitness of any model for a portfolio, forecast accuracy, or supervisory approval.
- Regulatory transcriptions other than CRE99 Table 1: the CRE99 SA-CCR EADs (images on bis.org; a web fetch
  on 2026-11-04 could not read them), the CRE52.72 and MAR21 constants, MAR99 Table 2 and MAR32.9 Table 1 are
  the engineers' transcriptions in the skill references. Where a check compares to them, its source says so.
- Interpretations of ambiguous text (ASSUMPTIONS.md Part B). A check that agrees with an interpretation shows
  the code implements that reading, not that the reading is correct.
- Models with no check here rest on their unit tests alone: M02, M07, M08, M13, M14, M16, M17, M21, M23, M25
  and M29 (M03 is exercised only indirectly, through the scenarios checks; the Ledoit-Wolf branch of M09 and
  the Monte Carlo column of M04 have no check here).

## Staleness

manifest.json records the git head, the sha256 of every reviewed module, the Option Desk head and any
uncommitted engine changes, the package versions and the sha256 of every results file.
src/riskdesk/analytics.py (an overflow fix) and src/riskdesk/derivatives.py (removal of the local Black-76
rho correction after Option Desk 4a282d9) changed after the first review; the hashes were re-recorded and
the review rerun with 0 failures. Any later change to a reviewed module makes tests/test_governance.py fail
until the commands above are rerun and the outputs committed.
