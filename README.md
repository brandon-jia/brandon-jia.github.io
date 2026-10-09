# Brandon Jia personal website

A static personal website for GitHub Pages, with self-hosted fonts and artwork, no framework, no build step for viewing, and no runtime network requests to external services. Publish the `main` branch from the repository root.

- `index.html`: homepage, sharing metadata, and optional paper/art/sidenote blocks.
- `resume/`: HTML résumé with a one-page US Letter print layout.
- `site.css`: typography, responsive layout, motion, and print styles.
- `site.js`: scroll progress, active navigation, sliding tail, and one-time reveals.
- `404.html`: missing-page response with root-relative assets for GitHub Pages.
- `assets/`: local fonts, font licenses, panda poses, sharing image, and résumé PDF.
- `resume-source/`: LaTeX résumé source.
- `tools/`: reproducible asset builder and font audit report.

## Rebuild the PDF

With a local TeX distribution installed, run from the repository root:

```sh
cd resume-source
pdflatex -interaction=nonstopmode -halt-on-error Brandon-Jia-Highlights.tex
pdflatex -interaction=nonstopmode -halt-on-error Brandon-Jia-Highlights.tex
```

Copy the resulting PDF to `assets/Brandon-Jia-Highlights.pdf`. Keep both résumé formats in sync when editing facts.

## Regenerate assets

The approved `original-panda-study.png` is a separate source image, excluded from Git. Supply its real path:

```sh
python -m pip install pillow numpy scipy playwright fonttools brotli
python -m playwright install chromium
python tools/build_assets.py --source /path/to/original-panda-study.png
```

The builder writes the sharing image, icons, transparent poses, font subsets, and `tools/asset-report.json`. Font downloads occur at build time only. Variable axes are retained. Source Sans 3 has tabular lining digits by default but no separate `lnum` or `tnum` feature tags; its `onum` feature is preserved. The other Latin fonts contain all three tags.

## Add paper links, summaries, paintings, or notes

Find the comments beginning `Brandon:` in `index.html`. Fill every placeholder with real URLs, original images, titles, descriptions, summaries, or notes, then uncomment the relevant block. For paintings, add the files to `assets/art/`, supply real image dimensions and alt text, and add an Art link to the navigation. Optional LinkedIn and Scholar/ORCID links are commented out in both footers.

The footer month is manual. Update its visible text and `datetime` value, and the sitemap dates, when making substantive changes. Confirm the JSON-LD topic list before relying on it as your public profile description.

The homepage and résumé work when opened locally with `file://`. The 404 page deliberately uses root-relative paths and should be tested through an HTTP server. All essential content remains visible without JavaScript and with reduced motion enabled.
