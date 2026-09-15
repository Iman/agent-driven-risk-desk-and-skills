#!/usr/bin/env python3
"""Capture a README image from a report page that was just generated.

The images in the README are the part a reader trusts without reading, so
each is taken from a file this script generates in the same run rather than
from a page somebody kept. Playwright and its Chromium are not project
dependencies, which is why this is a script and not a test: the images are
committed, and regenerating one is a deliberate act.

The whole page:

    python3 scripts/screenshot_report.py \\
        --python .venv/bin/python \\
        --output docs/images/report-energy-stress.png

One section of it, clipped to the section's own bounding box read from the
live DOM, so the crop is the section rather than a guessed rectangle:

    python3 scripts/screenshot_report.py \\
        --python .venv/bin/python \\
        --section "Linear portfolio exposure" \\
        --output docs/images/report-energy-exposure.png

Install the capture tool first, in any Python, not necessarily the project
environment: `pip install playwright` then `python -m playwright install
chromium`.
"""
import argparse
from pathlib import Path
import re
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parent.parent

# Reads the live DOM: everything from the named h2 up to the next h2, so a
# section that grows a chart is still captured whole.
SECTION_BOX = """
(heading) => {
  const tops = Array.from(document.querySelectorAll('h2'));
  const start = tops.find(node => node.textContent.trim() === heading);
  if (!start) { return null; }
  const stop = tops[tops.indexOf(start) + 1] || null;
  let bottom = stop ? stop.getBoundingClientRect().top + window.scrollY
                    : document.body.scrollHeight;
  const box = start.getBoundingClientRect();
  const top = box.top + window.scrollY;
  return {x: 0, y: Math.max(top - 12, 0),
          width: document.body.scrollWidth,
          height: Math.max(bottom - top - 8, 1)};
}
"""


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--python", default=sys.executable,
                        help="interpreter that has riskdesk installed")
    parser.add_argument("--stress", default="examples/energy_stress.json")
    parser.add_argument("--tail", default="examples/energy_tail.json")
    parser.add_argument("--exposure", default="examples/energy_book.json")
    parser.add_argument("--output",
                        default="docs/images/report-energy-stress.png")
    parser.add_argument("--section",
                        help="capture only this h2 section, not the page")
    parser.add_argument("--width", type=int, default=1100)
    parser.add_argument("--scale", type=float, default=1.5)
    parser.add_argument("--colors", type=int, default=64,
                        help="palette size for the saved PNG")
    parser.add_argument("--color-scheme", default="dark",
                        choices=("dark", "light"),
                        help="the tokens are dark first; headless Chromium "
                             "defaults to light, so this is set explicitly")
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
        command = [args.python, "-m", "riskdesk.cli", "report",
                   "--input", str(ROOT / args.stress),
                   "--output", str(page_path)]
        if args.tail:
            command += ["--tail", str(ROOT / args.tail)]
        if args.exposure:
            command += ["--exposure", str(ROOT / args.exposure)]
        finished = subprocess.run(command, cwd=str(ROOT), capture_output=True,
                                  text=True)
        if finished.returncode:
            print(finished.stdout.strip())
            print(finished.stderr.strip())
            return 1
        with sync_playwright() as play:
            browser = play.chromium.launch()
            page = browser.new_page(viewport={"width": args.width,
                                              "height": 900},
                                    device_scale_factor=args.scale,
                                    color_scheme=args.color_scheme)
            page.goto(page_path.as_uri())
            if args.section:
                box = page.evaluate(SECTION_BOX, args.section)
                if box is None:
                    print("no h2 reads exactly: " + args.section)
                    browser.close()
                    return 1
                page.screenshot(path=str(output), full_page=True, clip=box)
            else:
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
    try:
        shown = output.relative_to(ROOT)
    except ValueError:
        shown = output
    print("wrote {} ({} bytes)".format(shown, output.stat().st_size))
    return 0


def capture_dashboard(argv=None):
    """Capture dashboard views from a server this script starts and stops.

    The server runs as a subprocess of the project interpreter, because the
    interpreter that has Playwright is not the one that has the project's
    dependencies. That is also the more faithful capture: it photographs
    the command a reader will actually run, over a real socket, rather than
    a page rendered in memory.

        python3 scripts/screenshot_report.py --python .venv/bin/python

    Port 0, so a capture cannot collide with a dashboard already running.
    """
    parser = argparse.ArgumentParser(description="capture dashboard views")
    parser.add_argument("--python", default=sys.executable)
    parser.add_argument("--views", nargs="+",
                        default=["overview", "exposure", "tail"])
    parser.add_argument("--out-dir", default="docs/images")
    parser.add_argument("--prefix", default="dashboard")
    parser.add_argument("--width", type=int, default=1100)
    parser.add_argument("--scale", type=float, default=1.25)
    parser.add_argument("--colors", type=int, default=32)
    parser.add_argument("--color-scheme", default="dark",
                        choices=("dark", "light"))
    args = parser.parse_args(argv)

    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("playwright is not importable in " + sys.executable)
        print("pip install playwright && python -m playwright install chromium")
        return 1

    process = subprocess.Popen(
        [args.python, "-m", "riskdesk.cli", "dashboard", "--port", "0"],
        cwd=str(ROOT), stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        text=True)
    base = None
    for _ in range(40):
        line = process.stdout.readline()
        if not line:
            break
        found = re.search(r"(http://127\.0\.0\.1:\d+)", line)
        if found:
            base = found.group(1)
            break
    if base is None:
        process.terminate()
        print("the dashboard did not report a URL")
        print(process.stderr.read()[-2000:])
        return 1

    written = []
    try:
        with sync_playwright() as play:
            browser = play.chromium.launch()
            page = browser.new_page(viewport={"width": args.width,
                                              "height": 900},
                                    device_scale_factor=args.scale,
                                    color_scheme=args.color_scheme)
            for view in args.views:
                target = (ROOT / args.out_dir
                          / "{}-{}.png".format(args.prefix, view))
                target.parent.mkdir(parents=True, exist_ok=True)
                page.goto("{}/{}".format(base, view))
                page.screenshot(path=str(target), full_page=True)
                written.append(target)
            browser.close()
    finally:
        process.terminate()
        process.wait(timeout=30)

    try:
        from PIL import Image
    except ImportError:
        pass
    else:
        for target in written:
            with Image.open(target) as image:
                image.convert("RGB").quantize(
                    colors=args.colors,
                    method=Image.Quantize.MEDIANCUT).save(target,
                                                          optimize=True)
    total = 0
    for target in written:
        size = target.stat().st_size
        total += size
        try:
            shown = target.relative_to(ROOT)
        except ValueError:
            shown = target
        print("wrote {} ({} bytes)".format(shown, size))
    print("total {} bytes across {} views".format(total, len(written)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
