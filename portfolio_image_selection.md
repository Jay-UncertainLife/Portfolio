# Portfolio Image Selection

This website version rebuilds the portfolio as a sequence of A3 landscape boards in `portfolio_wix_layout.html`.
Assets are regenerated with `scripts/export_portfolio_pages.py` and now include both full-page exports and isolated single-image crops.

## Export workflow

- Run `python scripts/export_portfolio_pages.py`
- Full-page output: `website_assets/images/pages`
- Crop output: `website_assets/images/crops`
- Web manifest: `website_assets/data/portfolio_crops.js`
- Render scale: `160 dpi` for full pages, `220 dpi` for fallback crop segmentation

## Selected pages by project

### Level 4 Portfolio

- PDF: `Rong Chen-L4-Portfolio2023-2024.pdf`
- Exported pages: `3, 4, 5, 6, 8, 10, 12, 14, 16, 18, 20, 24, 28, 32, 36, 40, 43, 46, 49, 51`
- Output folder: `website_assets/images/pages/l4`

### Radical Reuse

- PDF: `RongChen_k2336224_Logbook_IR5101：Radical Reuse.pdf`
- Exported pages: `4, 5, 7, 8, 9, 10, 15, 17, 19, 21, 23, 24, 26, 28, 30, 34, 39, 42, 48, 50`
- Output folder: `website_assets/images/pages/reuse`

### Passion for Fashion

- PDF: `RongChen_K2336224_Passion for Fashion_Portfolio.pdf`
- Exported pages: `1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 18, 20, 23, 26`
- Output folder: `website_assets/images/pages/fashion`

### Student Bar

- PDF: `RongChen_K2336224_Student Bar_portfolio.pdf`
- Exported pages: `1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 15, 17, 19, 21, 23, 25, 27`
- Output folder: `website_assets/images/pages/bar`

## Layout intent

- Portfolio section uses A3 landscape board proportions throughout.
- Every board includes a short brief, phase label and source page reference.
- Text is fixed in a stable side panel; the remaining board area is reserved for image composition.
- Website boards are assembled from isolated image crops so incomplete full-page screenshots are not used as final board content.
