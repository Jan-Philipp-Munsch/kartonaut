"""Build docs/DesignGuide_Mainboard_revB.pdf from the Markdown source.

Markdown -> HTML (python-markdown, tables + toc) -> PDF (Chrome or Edge headless, print-to-pdf).
The HTML is written next to the Markdown so that the relative image paths resolve, and deleted
afterwards. Figures: hardware/mainboard/figures.py and outline.py must have run before.

Run:  python docs/build_design_guide.py
"""
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

import markdown

HERE = Path(__file__).resolve().parent
SRC = HERE / "DesignGuide_Mainboard_revB.md"
HTML = HERE / "_DesignGuide_Mainboard_revB_build.html"
PDF = HERE / "DesignGuide_Mainboard_revB.pdf"
BROWSERS = [Path(r"C:\Program Files\Google\Chrome\Application\chrome.exe"),
            Path(r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe")]

CSS = """
@page { size: A4; margin: 18mm 16mm 18mm 16mm; }
body { font-family: Calibri, "Segoe UI", Arial, sans-serif; font-size: 10.5pt; line-height: 1.38; color: #222; max-width: 100%; }
h1 { font-size: 22pt; margin: 0 0 4pt 0; }
h2 { font-size: 15pt; margin-top: 22pt; border-bottom: 1px solid #999; padding-bottom: 2pt; page-break-after: avoid; }
h3 { font-size: 12pt; margin-top: 14pt; page-break-after: avoid; }
p.subtitle { color: #555; margin-top: 0; }
img { max-width: 100%; height: auto; display: block; margin: 8pt auto; page-break-inside: avoid; }
table { border-collapse: collapse; font-size: 9pt; margin: 6pt 0 10pt 0; width: 100%; page-break-inside: auto; }
th, td { border: 1px solid #bbb; padding: 3pt 5pt; vertical-align: top; text-align: left; }
th { background: #eee; }
tr { page-break-inside: avoid; }
code { font-family: Consolas, "Courier New", monospace; font-size: 9pt; background: #f3f3f3; padding: 0 2pt; }
pre { background: #f6f6f6; border: 1px solid #ddd; padding: 6pt; font-size: 8.5pt; overflow-x: auto; white-space: pre-wrap; }
blockquote { border-left: 3px solid #c0392b; margin: 8pt 0; padding: 2pt 10pt; color: #444; background: #fdf3f2; }
.toc { font-size: 9.5pt; columns: 2; }
.toc ul { margin: 0; padding-left: 14pt; }
hr.pb { page-break-after: always; border: none; }
"""


def main():
    md = SRC.read_text(encoding="utf-8")
    body = markdown.markdown(md, extensions=["tables", "toc", "fenced_code", "attr_list", "md_in_html"],
                             extension_configs={"toc": {"toc_depth": "2-3", "title": "Inhalt"}})
    html = f'<!doctype html><html lang="de"><head><meta charset="utf-8"><title>Design Guide Mainboard rev B</title>' \
           f'<style>{CSS}</style></head><body>{body}</body></html>'
    HTML.write_text(html, encoding="utf-8")
    PDF.unlink(missing_ok=True)
    for browser in BROWSERS:          # Chrome first; Edge headless printed nothing on this machine (2026-10-21)
        if not browser.exists():
            continue
        profile = Path(tempfile.mkdtemp(prefix="dg_profile_"))
        cmd = [str(browser), "--headless=new", "--disable-gpu", "--no-first-run", f"--user-data-dir={profile}",
               "--no-pdf-header-footer", "--virtual-time-budget=10000", f"--print-to-pdf={PDF}", HTML.as_uri()]
        subprocess.run(cmd, check=False, timeout=180, capture_output=True)
        shutil.rmtree(profile, ignore_errors=True)
        if PDF.exists():
            break
    if not PDF.exists():
        print("no browser produced a PDF; HTML left at", HTML)
        return 1
    HTML.unlink()
    print("wrote", PDF, PDF.stat().st_size // 1024, "kB")
    return 0


if __name__ == "__main__":
    sys.exit(main())
