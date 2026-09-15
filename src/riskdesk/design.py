"""The desk design system, copied into this repository on purpose.

WHERE THIS CAME FROM. The token layer and the component rules below were
copied from the Avid Quant desk design system, which lives in a separate
and private repository:

    optiondesk.avidquant.com/src/optiondesk_hosted/static/tokens.css
    optiondesk.avidquant.com/src/optiondesk_hosted/static/components.css
    optiondesk.avidquant.com/docs/DESIGN-SYSTEM.md

COPIED, NOT IMPORTED, and that is deliberate. This repository is public and
self-contained, adds no dependency, fetches nothing at runtime and has no
submodule. The cost of copying is that the two can drift, so: THESE TOKENS
AND THAT FILE MUST BE KEPT IN STEP. If a token changes there, change it
here. `tests/test_design_system.py` pins the structure this file must
keep, and `scripts/contrast.py` re-measures the contrast rather than
trusting the figure measured on the other service's markup.

WHAT WAS DELIBERATELY NOT COPIED.

  The LEGACY BRIDGE block, which redefines --bg, --panel, --ink, --muted,
  --line, --accent, --up, --down and the --warn-* trio. Those exist to
  re-tint a vendored Option Desk renderer without editing it. There is no
  vendored renderer here; this repository owns every rule it emits, so a
  bridge would be nine names nothing reads.

  The adoption plan in DESIGN-SYSTEM.md lines 267 to 291. It tells Risk
  Desk to serve the sheets from /assets/ routes, link them after an inline
  block and rely on `style-src 'self'`. That describes the HOSTED Risk Desk
  service, which vendors this package. This dashboard has no asset route,
  serves a fixed routing table, and sends `default-src 'none'` with inline
  styles only. Following it here would mean adding a file-serving route
  and relaxing the policy, breaking two guarantees this repository tests
  for. So the CSS is inlined instead, which is what the page already did.

  The gain and loss glyph and border-style tokens, which give a third,
  non-chromatic channel. The charts here already carry two channels
  besides colour: a bar's side of the zero line, and the signed figure
  printed beside it. Adding a token nothing paints is the thing that
  system's own notes warn against, so they are left out until a chart
  actually draws one.

THE STATE TOKENS, AND THE ONE THAT IS NOT USED HERE.

  --od-degraded is bound to this project's degraded flag. That flag has
  exactly one source, `analytics.envelope(warnings=...)`, and exactly one
  warning feeds it: the small-sample threshold in `analytics.py`.

  --od-synthetic is bound to `data_mode == "synthetic"`, which every
  shipped example is. Before this change the page printed that word in
  plain grey and gave it no weight at all.

  --od-stale IS DEFINED AND DELIBERATELY UNUSED. Stale means figures that
  are real but older than their stated horizon. This project has no
  freshness state: the only "stale" in the source is the ORE adapter's
  refusal to reuse an old simulation cube, which is a different thing. It
  is kept, rather than deleted, so the token set stays comparable with the
  file it was copied from. Binding the small-sample warning to it would
  paint a degraded page in the amber that means stale, which is the exact
  mistake the other service made by trusting a class name.
"""

# Dark is the default, declared on bare :root. Light redefines the same
# names inside the media query. No rule below declares a colour of its own
# in either mode: every one reads a token, which is what makes both modes
# come from one place. There is no theme toggle and no class on the body,
# because this page runs under a policy that allows no script.
TOKENS = """
:root {
  --od-ground: #000000;
  --od-surface: #15171b;
  --od-surface-raised: #1b1f25;
  --od-surface-sunken: #0a0b0d;

  --od-line: #23262c;
  --od-line-strong: #343943;

  --od-text: #e8eaed;
  --od-text-muted: #939aa6;
  --od-text-faint: #6b7280;

  --od-accent: #6ea0ff;
  --od-accent-ink: #06121f;

  --od-gain: #3ddc84;
  --od-gain-ground: #0b2318;
  --od-loss: #ff6b6b;
  --od-loss-ground: #2a1013;

  --od-stale: #fcd34d;
  --od-stale-ground: #2a1f06;
  --od-degraded: #fdba74;
  --od-degraded-ground: #2a1206;
  --od-synthetic: #c4b5fd;
  --od-synthetic-ground: #1a142e;

  --od-axis: #6b7280;

  --od-font-sans: ui-sans-serif, system-ui, -apple-system, "Segoe UI",
                  Roboto, "Helvetica Neue", Arial, sans-serif;
  --od-font-mono: ui-monospace, SFMono-Regular, "SF Mono", Menlo, Consolas,
                  "Liberation Mono", monospace;

  --od-font-size-1: 20px;
  --od-font-size-2: 17px;
  --od-font-size-3: 14px;
  --od-font-size-4: 13px;
  --od-font-size-5: 12px;
  --od-font-size-6: 11px;
  --od-font-size-7: 10px;

  --od-line-tight: 1.25;
  --od-line-body: 1.45;
  --od-line-loose: 1.6;

  --od-weight-normal: 400;
  --od-weight-medium: 600;
  --od-weight-strong: 650;

  --od-tracking-tight: -0.015em;
  --od-tracking-figure: -0.02em;
  --od-tracking-none: 0;
  --od-tracking-label: 0.07em;

  --od-measure: 92ch;

  --od-space-1: 2px;
  --od-space-2: 4px;
  --od-space-3: 6px;
  --od-space-4: 8px;
  --od-space-5: 12px;
  --od-space-6: 16px;
  --od-space-7: 24px;
  --od-space-8: 32px;

  --od-cell-pad-y: 5px;
  --od-cell-pad-x: 9px;

  --od-radius-1: 4px;
  --od-radius-2: 6px;
  --od-radius-3: 8px;
  --od-radius-pill: 999px;

  --od-border-hair: 1px;
  --od-border-rule: 2px;
  --od-border-flag: 3px;

  --od-degraded-hatch: repeating-linear-gradient(
      135deg,
      rgba(253, 186, 116, 0.12) 0,
      rgba(253, 186, 116, 0.12) 6px,
      rgba(0, 0, 0, 0) 6px,
      rgba(0, 0, 0, 0) 12px);
}

@media (prefers-color-scheme: light) {
  :root {
    --od-ground: #ffffff;
    --od-surface: #f6f6f7;
    --od-surface-raised: #ffffff;
    --od-surface-sunken: #ececee;

    --od-line: #d4d4d8;
    --od-line-strong: #a1a1aa;

    --od-text: #1d1d1f;
    --od-text-muted: #5a5a60;
    --od-text-faint: #77777d;

    --od-accent: #1d4ed8;
    --od-accent-ink: #ffffff;

    --od-gain: #15803d;
    --od-gain-ground: #e9f6ee;
    --od-loss: #b91c1c;
    --od-loss-ground: #fdecec;

    --od-stale: #854d0e;
    --od-stale-ground: #fdf6e3;
    --od-degraded: #9a3412;
    --od-degraded-ground: #fdf0e7;
    --od-synthetic: #5b21b6;
    --od-synthetic-ground: #f3efff;

    --od-axis: #8a8a90;

    --od-degraded-hatch: repeating-linear-gradient(
        135deg,
        rgba(154, 52, 18, 0.10) 0,
        rgba(154, 52, 18, 0.10) 6px,
        rgba(255, 255, 255, 0) 6px,
        rgba(255, 255, 255, 0) 12px);
  }
}

:root { color-scheme: dark; }

@media (prefers-color-scheme: light) {
  :root { color-scheme: light; }
}
"""

# The component rules. The chart block below was written by that system
# for exactly this markup: these SVGs are styled entirely by class, with no
# presentational fill or stroke attribute, which is what makes them
# retintable without touching a chart function.
COMPONENTS = """
body { font-family: var(--od-font-sans); margin: 0;
       padding: var(--od-space-8); color: var(--od-text);
       background: var(--od-ground); line-height: var(--od-line-body);
       font-size: var(--od-font-size-4); }
h1 { font-size: var(--od-font-size-1); margin: 0 0 var(--od-space-2) 0;
     letter-spacing: var(--od-tracking-tight);
     font-weight: var(--od-weight-strong); }
h2 { font-size: var(--od-font-size-3); margin: var(--od-space-8) 0
     var(--od-space-4) 0; font-weight: var(--od-weight-strong); }
h3 { font-size: var(--od-font-size-4); margin: var(--od-space-7) 0
     var(--od-space-2) 0; font-weight: var(--od-weight-medium); }
p, li { font-size: var(--od-font-size-4); max-width: var(--od-measure); }
.meta { font-size: var(--od-font-size-5); color: var(--od-text-muted);
        max-width: var(--od-measure); }

.flag { display: inline-block; padding: var(--od-space-2) var(--od-space-5);
        border-radius: var(--od-radius-1);
        font-size: var(--od-font-size-5);
        font-weight: var(--od-weight-medium); }
.flag.ok { background: var(--od-gain-ground); color: var(--od-gain); }
.flag.degraded { background: var(--od-degraded-ground);
                 color: var(--od-degraded);
                 background-image: var(--od-degraded-hatch); }
.flag.synthetic { background: var(--od-synthetic-ground);
                  color: var(--od-synthetic); }

.convention { border-left: var(--od-border-flag) solid var(--od-accent);
              padding: var(--od-space-4) var(--od-space-5);
              background: var(--od-surface); color: var(--od-text);
              font-size: var(--od-font-size-5);
              max-width: var(--od-measure); }

table { border-collapse: collapse; font-size: var(--od-font-size-5);
        margin: var(--od-space-4) 0;
        font-variant-numeric: tabular-nums; }
th, td { border: var(--od-border-hair) solid var(--od-line);
         padding: var(--od-cell-pad-y) var(--od-cell-pad-x);
         text-align: right; }
th { background: var(--od-surface); color: var(--od-text-muted);
     font-size: var(--od-font-size-7);
     letter-spacing: var(--od-tracking-label);
     text-transform: uppercase; font-weight: var(--od-weight-medium); }
th:first-child, td:first-child { text-align: left; }

.chart { max-width: 100%; height: auto;
         margin: var(--od-space-2) 0 var(--od-space-4) 0; }
.chart .axis { stroke: var(--od-axis); stroke-width: 1; }
.chart .bar.loss, .chart .bar.short { fill: var(--od-loss); }
.chart .bar.gain, .chart .bar.long { fill: var(--od-gain); }
.chart .bar.flat { fill: var(--od-text-faint); }
.chart .bar.share, .chart .bin { fill: var(--od-accent); }
.chart .mark { stroke-width: var(--od-border-rule); }
.chart .mark.var { stroke: var(--od-loss); }
.chart .mark.es { stroke: var(--od-synthetic); stroke-dasharray: 5 3; }
.chart .label, .chart .value, .chart .tick, .chart .marklabel {
    font-family: var(--od-font-sans); font-size: var(--od-font-size-6);
    fill: var(--od-text); }
.chart .tick { fill: var(--od-text-muted); }
.chart .label { text-anchor: end; }

footer { margin-top: var(--od-space-8); font-size: var(--od-font-size-6);
         color: var(--od-text-faint); max-width: var(--od-measure); }
"""

STYLE = TOKENS + COMPONENTS
