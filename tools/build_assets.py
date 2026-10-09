#!/usr/bin/env python3
"""Rebuild local website assets; no runtime requests are added to the site.

Dependencies: pillow numpy scipy playwright fonttools brotli.
Run from the repository root: python tools/build_assets.py --source /path/to/original-panda-study.png
"""
from __future__ import annotations

import argparse
import json
import tempfile
import urllib.request
from pathlib import Path

import numpy as np
from fontTools import subset
from fontTools.ttLib import TTFont
from PIL import Image
from playwright.sync_api import sync_playwright
from scipy import ndimage as ndi

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / "assets"
NUMERIC = {"onum", "lnum", "tnum"}
UNICODES = set(range(0x20, 0x7F)) | set(range(0xA0, 0x100)) | {
    0x2013, 0x2014, 0x2018, 0x2019, 0x201C, 0x201D, 0x2022, 0x2026, 0x2192,
}
MARK = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 26"><circle cx="12" cy="15" r="8.5" fill="none" stroke="#a8452f" stroke-width="5" stroke-dasharray="4 2.67"/><path d="M5 8.5L5.6 2l5.4 4M19 8.5L18.4 2 13 6" fill="#a8452f"/></svg>'
SMALL = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 26"><circle cx="12" cy="15" r="8.5" fill="none" stroke="#a8452f" stroke-width="5.5" stroke-dasharray="4.45 4.45"/><path d="M5 8.5L5.6 2l5.4 4M19 8.5L18.4 2 13 6" fill="#a8452f"/></svg>'
FONTS = (
    ("literata", "Literata", "literata.woff2", False),
    ("cormorantgaramond", "CormorantGaramond", "cormorant-garamond.woff2", False),
    ("sourcesans3", "SourceSans3", "source-sans.woff2", False),
    ("cormorantgaramond", "CormorantGaramond", "cormorant-garamond-italic.woff2", True),
)


def features(path):
    with TTFont(path) as font:
        return sorted({item.FeatureTag for item in font["GSUB"].table.FeatureList.FeatureRecord}) if "GSUB" in font else []


def axes(path):
    with TTFont(path) as font:
        return [axis.axisTag for axis in font["fvar"].axes] if "fvar" in font else []


def download(url, target):
    target.parent.mkdir(parents=True, exist_ok=True)
    request = urllib.request.Request(url, headers={"User-Agent": "Brandon-Jia-Asset-Builder"})
    with urllib.request.urlopen(request, timeout=60) as response:
        target.write_bytes(response.read())


def api_json(url):
    request = urllib.request.Request(url, headers={"User-Agent": "Brandon-Jia-Asset-Builder"})
    with urllib.request.urlopen(request, timeout=60) as response:
        return json.load(response)


def build_fonts(cache, refresh=False):
    report = []
    # Pin all four downloads to one upstream commit; cache it for reproducible reruns.
    pin = cache / "google-fonts-commit.txt"
    commit = None
    for family, prefix, name, italic in FONTS:
        output = ASSETS / name
        before = output.stat().st_size if output.exists() else 0
        original_features = features(output) if output.exists() else []
        rebuild = refresh or not output.exists() or not NUMERIC.issubset(original_features)
        source_features = original_features
        if rebuild:
            if commit is None:
                if pin.exists() and not refresh:
                    commit = pin.read_text(encoding="utf-8").strip()
                else:
                    commit = api_json("https://api.github.com/repos/google/fonts/commits/main")["sha"]
                    pin.parent.mkdir(parents=True, exist_ok=True)
                    pin.write_text(commit + "\n", encoding="utf-8")
            listing = api_json(f"https://api.github.com/repos/google/fonts/contents/ofl/{family}?ref={commit}")
            candidates = [entry for entry in listing if entry["name"].endswith(".ttf")
                          and entry["name"].startswith(prefix) and ("Italic" in entry["name"]) == italic]
            if len(candidates) != 1:
                raise RuntimeError(f"Expected one upstream variable font for {name}, found {len(candidates)}")
            entry = candidates[0]
            source = cache / commit / entry["name"]
            if not source.exists():
                download(entry["download_url"], source)
            source_features = features(source)
            options = subset.Options()
            options.layout_features = list(dict.fromkeys(options.layout_features + ["onum", "lnum", "tnum", "pnum", "kern", "liga"]))
            options.flavor = "woff2"
            font = TTFont(source, recalcTimestamp=False)
            cutter = subset.Subsetter(options=options)
            cutter.populate(unicodes=UNICODES)
            cutter.subset(font)
            font.flavor = "woff2"
            font.save(output)
            font.close()
        after_features = features(output)
        report.append({"file": name, "before_bytes": before, "after_bytes": output.stat().st_size,
                       "rebuilt": rebuild, "before_features": original_features,
                       "after_features": after_features, "axes": axes(output),
                       "upstream_missing": sorted(NUMERIC - set(source_features)),
                       "subset_missing": sorted(NUMERIC - set(after_features))})
    return report, commit or (pin.read_text(encoding="utf-8").strip() if pin.exists() else None)


def cutout(src, box, out):
    im = Image.open(src).convert("RGB").crop(box)
    a = np.array(im).astype(int)
    near = (a >= 225).all(axis=2)
    lab, _ = ndi.label(near)
    border = set(lab[0, :]) | set(lab[-1, :]) | set(lab[:, 0]) | set(lab[:, -1])
    border.discard(0)
    ext = np.isin(lab, list(border))
    rgba = np.dstack([a, np.where(ext, 0, 255)]).astype("uint8")
    img = Image.fromarray(rgba, "RGBA")
    img = img.crop(img.getbbox())
    if out.suffix == ".webp":
        img.save(out, "WEBP", lossless=True, method=6)
    else:
        img.save(out, optimize=True)
    return {"file": out.name, "width": img.width, "height": img.height, "bytes": out.stat().st_size}


def render_assets(browser):
    (ROOT / "favicon.svg").write_text(MARK + "\n", encoding="utf-8")
    (ROOT / "mark-small.svg").write_text(SMALL + "\n", encoding="utf-8")
    page = browser.new_page(viewport={"width": 256, "height": 256}, device_scale_factor=1)
    with tempfile.TemporaryDirectory() as temporary:
        temporary = Path(temporary)
        icon_template = temporary / "icon.html"
        icon_template.write_text('<!doctype html><html><head><style>html,body{margin:0;width:100%;height:100%;display:grid;place-items:center}img{display:block;height:100%;width:auto}</style></head><body><img src="' + (ROOT / "mark-small.svg").as_uri() + '"></body></html>', encoding="utf-8")
        page.goto(icon_template.as_uri(), wait_until="load")
        page.screenshot(path=str(temporary / "icon.png"), omit_background=True)
        with Image.open(temporary / "icon.png") as icon:
            icon.save(ROOT / "favicon.ico", sizes=[(16, 16), (32, 32), (48, 48)])
        page.set_viewport_size({"width": 180, "height": 180})
        icon_template.write_text('<!doctype html><html><head><style>html,body{margin:0;width:100%;height:100%;display:grid;place-items:center;background:#fff}img{display:block;height:120px;width:auto}</style></head><body><img src="' + (ROOT / "favicon.svg").as_uri() + '"></body></html>', encoding="utf-8")
        page.goto(icon_template.as_uri(), wait_until="load")
        page.screenshot(path=str(ROOT / "apple-touch-icon.png"))
        template = temporary / "og.html"
        template.write_text('''<!doctype html><html><head><meta charset="utf-8"><style>
@font-face{font-family:Display;src:url("[[DISPLAY_FONT]]");font-weight:300 700}
@font-face{font-family:NameCJK;src:url("[[CJK_FONT]]")}
@font-face{font-family:Sans;src:url("[[SANS_FONT]]");font-weight:200 900}
*{box-sizing:border-box}html,body{margin:0;width:1200px;height:630px;background:#fff}
.copy{position:absolute;left:84px;top:150px}.name{margin:0;font:600 132px/1 Display;color:#362924}
.cn{margin:18px 0 0;font:400 40px/1.3 NameCJK;letter-spacing:.2em;color:#6a5f58}
.meta{margin:30px 0 0;font:600 28px/1.2 Sans;letter-spacing:.14em;color:#a8452f}
.rule{position:absolute;left:84px;right:84px;bottom:96px;height:3px;background:#a8452f}
.panda{position:absolute;width:300px;height:auto;right:140px;bottom:96px}
</style></head><body><div class="copy"><p class="name">Brandon Jia</p><p class="cn">贾越衡</p><p class="meta">MATHEMATICS &amp; RESEARCH</p></div><div class="rule"></div><img class="panda" src="[[PANDA_ASSET]]" alt=""></body></html>'''.replace("[[DISPLAY_FONT]]", (ASSETS / "cormorant-garamond.woff2").as_uri()).replace("[[CJK_FONT]]", (ASSETS / "chinese-name.woff2").as_uri()).replace("[[SANS_FONT]]", (ASSETS / "source-sans.woff2").as_uri()).replace("[[PANDA_ASSET]]", (ASSETS / "panda-peek.png").as_uri()), encoding="utf-8")
        page.set_viewport_size({"width": 1200, "height": 630})
        page.goto(template.as_uri(), wait_until="load")
        page.evaluate("document.fonts.ready")
        assert page.evaluate("[...document.images].every(image => image.complete && image.naturalWidth > 0)")
        page.screenshot(path=str(ASSETS / "og-image.png"))
    page.close()
    with Image.open(ASSETS / "og-image.png") as image:
        image.convert("RGB").save(ASSETS / "og-image.png", optimize=True)
    assert (ASSETS / "og-image.png").stat().st_size < 300_000


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=ROOT / "original-panda-study.png")
    parser.add_argument("--cache-dir", type=Path, default=ROOT / "tools/.cache")
    parser.add_argument("--browser", type=Path, help="Optional local Chromium/Chrome executable")
    parser.add_argument("--refresh-fonts", action="store_true")
    parser.add_argument("--audit-fonts", action="store_true", help="Read existing font features without changing files")
    args = parser.parse_args()
    if args.audit_fonts:
        print(json.dumps([{ "file": name, "bytes": (ASSETS / name).stat().st_size,
                          "features": features(ASSETS / name), "axes": axes(ASSETS / name)}
                         for _, _, name, _ in FONTS if (ASSETS / name).exists()], indent=2))
        return
    if not args.source.is_file():
        parser.error("original-panda-study.png is missing; supply its real path with --source")
    with Image.open(args.source) as source:
        if source.size != (1536, 1024):
            parser.error("The approved study sheet must be 1536 x 1024 pixels")
    ASSETS.mkdir(exist_ok=True)
    fonts, commit = build_fonts(args.cache_dir, args.refresh_fonts)
    # Preserve the approved homepage peek exactly; derive other poses from the sheet.
    poses = []
    peek = ASSETS / "panda-peek.png"
    if not peek.exists():
        cutout(args.source, (1195, 660, 1515, 835), peek)
    with Image.open(peek) as image:
        poses.append({"file": peek.name, "width": image.width, "height": image.height, "bytes": peek.stat().st_size})
        image.save(ASSETS / "panda-peek.webp", "WEBP", lossless=True, method=6)
        poses.append({"file": "panda-peek.webp", "width": image.width, "height": image.height, "bytes": (ASSETS / "panda-peek.webp").stat().st_size})
    for box, filename in [((40, 610, 380, 850), "panda-curled.webp"), ((800, 590, 1120, 850), "panda-linework.webp")]:
        pose = cutout(args.source, box, ASSETS / filename)
        if pose["bytes"] >= 50_000:
            raise RuntimeError(f"{filename} exceeds 50 KB; refine the crop or lossless encoding")
        poses.append(pose)
    with sync_playwright() as playwright:
        options = {"headless": True}
        if args.browser:
            options["executable_path"] = str(args.browser)
        browser = playwright.chromium.launch(**options)
        try:
            render_assets(browser)
        finally:
            browser.close()
    report = {"google_fonts_commit": commit, "fonts": fonts, "poses": poses,
              "og_image": {"width": 1200, "height": 630, "bytes": (ASSETS / "og-image.png").stat().st_size},
              "note": "Upstream-missing features are reported honestly; no synthetic OpenType features are added."}
    (ROOT / "tools/asset-report.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
