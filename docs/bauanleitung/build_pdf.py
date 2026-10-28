"""Build docs/bauanleitung/Bauanleitung_Kartonaut1.pdf from docs/Bauanleitung_Kartonaut1.md
and docs/Platine_revB1_Bestueckung_Pruefung.md (Teil II, seit 28.10.2026).

Same pipeline as docs/build_design_guide.py: Markdown -> HTML (python-markdown) -> PDF (Chrome headless).
The HTML is written next to the Markdown so that the relative image paths resolve, and deleted afterwards.
Before: MS_CONFIG=erstflug python cad/modular.py, python docs/bauanleitung/zeichnungen.py and
python docs/platine/bestueckungsplan.py.

Run:  python docs/bauanleitung/build_pdf.py
Browsers: Chrome/Edge on Windows, else chromium/google-chrome on PATH, else Playwright's Chromium through node
(`require('playwright')`), which is what the cloud session uses (a bare headless Chromium hangs there on network calls).
"""
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

import markdown

HERE = Path(__file__).resolve().parent
SRC = HERE.parent / "Bauanleitung_Kartonaut1.md"
SRC2 = HERE.parent / "Platine_revB1_Bestueckung_Pruefung.md"      # Teil II
HTML = HERE.parent / "_Bauanleitung_Kartonaut1_build.html"
PDF = HERE / "Bauanleitung_Kartonaut1.pdf"
BROWSERS = [Path(r"C:\Program Files\Google\Chrome\Application\chrome.exe"),
            Path(r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"),
            *[Path(p) for p in map(shutil.which, ("chromium", "chromium-browser", "google-chrome")) if p]]

PLAYWRIGHT_JS = """
const { chromium } = require('playwright');
(async () => {
  const [html, pdf] = process.argv.slice(2);
  const browser = await chromium.launch({ args: ['--no-sandbox'] });
  const page = await browser.newPage();
  await page.goto('file://' + html, { waitUntil: 'load', timeout: 60000 });
  await page.pdf({ path: pdf, format: 'A4', printBackground: true, preferCSSPageSize: true });
  await browser.close();
})().catch(e => { console.error(e); process.exit(1); });
"""

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
td:first-child { white-space: nowrap; }
"""


def render(md_path):
    md = md_path.read_text(encoding="utf-8")
    return markdown.markdown(md, extensions=["tables", "toc", "fenced_code", "attr_list", "md_in_html"],
                             extension_configs={"toc": {"toc_depth": "2-3", "title": "Inhalt"}})


def main():
    body = render(SRC)
    if SRC2.exists():
        body += '<hr class="pb">' + render(SRC2)
    html = f'<!doctype html><html lang="de"><head><meta charset="utf-8"><title>Bauanleitung Kartonaut 1</title>' \
           f'<style>{CSS}</style></head><body>{body}</body></html>'
    HTML.write_text(html, encoding="utf-8")
    PDF.unlink(missing_ok=True)
    for browser in BROWSERS:          # Chrome first; Edge headless printed nothing on this machine (2026-10-21)
        if not browser.exists():
            continue
        profile = Path(tempfile.mkdtemp(prefix="ba_profile_"))
        cmd = [str(browser), "--headless=new", "--disable-gpu", "--no-first-run", "--no-sandbox",
               f"--user-data-dir={profile}", "--no-pdf-header-footer", "--virtual-time-budget=10000",
               f"--print-to-pdf={PDF}", HTML.as_uri()]
        subprocess.run(cmd, check=False, timeout=180, capture_output=True)
        shutil.rmtree(profile, ignore_errors=True)
        if PDF.exists():
            break
    if not PDF.exists() and shutil.which("node"):
        js = Path(tempfile.mkdtemp(prefix="ba_pw_")) / "html2pdf.js"
        js.write_text(PLAYWRIGHT_JS, encoding="utf-8")
        subprocess.run(["node", str(js), str(HTML), str(PDF)], check=False, timeout=180, capture_output=True)
        shutil.rmtree(js.parent, ignore_errors=True)
    if not PDF.exists():
        print("no browser produced a PDF; HTML left at", HTML)
        return 1
    HTML.unlink()
    print("wrote", PDF, PDF.stat().st_size // 1024, "kB")
    return 0


if __name__ == "__main__":
    sys.exit(main())
