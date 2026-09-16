---
description: Write one self-contained HTML page from the stress, tail and exposure results
argument-hint: [OUTPUT_PATH]
arguments: [output]
---

Write the report page to $output, or `artifacts/report.html` when no path
is given.

1. `riskdesk report --input examples/energy_stress.json --tail
   examples/energy_tail.json --exposure examples/energy_book.json --output
   artifacts/report.html`. When a path was given, use `--output $output`.
   Replace the three inputs with the caller's own files when they have
   them; `--tail` and `--exposure` are optional and `--input` is not.
2. Report what the command printed: the byte count, whether the tail and
   exposure panels were included, and the degraded flag.
3. An omitted input produces a section saying the input was absent. That
   is not the same as a measure of zero, and the page says so in those
   words. Do not summarise such a section as "no risk".
4. The page embeds its own styling and charts. It opens with no network
   and renders the same on a machine that has none.
5. Tell the caller where the file is. It is written where they said and
   nowhere else, and nothing else was left behind.
6. Every figure on the page came from the same functions the CLI and the
   MCP tools call. The page recomputes nothing.
