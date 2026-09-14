#!/usr/bin/env python3
"""Capture the README image from a report page that was just generated.

The one image in the README is the part a reader trusts without reading, so
it is taken from a file this script generates in the same run rather than
from a page somebody kept. Playwright and its Chromium are not project
dependencies, which is why this is a script and not a test: the image is
committed, and regenerating it is a deliberate act.

    python3 scripts/screenshot_report.py \\
        --python .venv/bin/python \\
        --stress examples/energy_stress.json \\
        --tail examples/tail.json \\
        --output docs/images/report-energy-stress.png

Install the capture tool first, in any Python, not necessarily the project
environment: `pip install playwright` then `python -m playwright install
chromium`.
"""
import argparse
from pathlib import Path
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parent.parent


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--python", default=sys.executable,
                        help="interpreter that has riskdesk installed")
    parser.add_argument("--stress", default="examples/energy_stress.json")
    parser.add_argument("--tail", default="examples/energy_tail.json")
    parser.add_argument("--output",
                        default="docs/images/report-energy-stress.png")
    parser.add_argument("--width", type=int, default=1100)
    parser.add_argument("--colors", type=int, default=64,
                        help="palette size for the saved PNG")
    args = parser.parse_args(argv)

    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("playwright is not importable in " + sys.executable)
        print("pip install playwright && python -m playwright install chromium")
        return 1

    output = (ROOT / args.output).resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as work:
        page_path = Path(work) / "report.html"
        finished = subprocess.run(
            [args.python, "-m", "riskdesk.cli", "report",
             "--input", str(ROOT / args.stress),
             "--tail", str(ROOT / args.tail),
             "--output", str(page_path)],
            cwd=str(ROOT), capture_output=True, text=True)
        if finished.returncode:
            print(finished.stdout.strip())
            print(finished.stderr.strip())
            return 1
        with sync_playwright() as play:
            browser = play.chromium.launch()
            page = browser.new_page(viewport={"width": args.width,
                                              "height": 900},
                                    device_scale_factor=1.5)
            page.goto(page_path.as_uri())
            page.screenshot(path=str(output), full_page=True)
            browser.close()
    # The page is flat colour and text, so an adaptive palette keeps it
    # legible at a fraction of the truecolour size. README images are read
    # on phones over mobile data; a megabyte of PNG is a cost with no
    # matching gain. Skipped silently when Pillow is absent.
    try:
        from PIL import Image
    except ImportError:
        pass
    else:
        with Image.open(output) as image:
            image.convert("RGB").quantize(
                colors=args.colors, method=Image.Quantize.MEDIANCUT).save(
                    output, optimize=True)
    print("wrote {} ({} bytes)".format(
        output.relative_to(ROOT), output.stat().st_size))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
