from __future__ import annotations

import json
from pathlib import Path

import cv2
import numpy as np
from PIL import Image
import pypdfium2 as pdfium


ROOT = Path(__file__).resolve().parent.parent
PAGE_OUT_DIR = ROOT / "website_assets" / "images" / "pages"
CROP_OUT_DIR = ROOT / "website_assets" / "images" / "crops"
DATA_OUT_DIR = ROOT / "website_assets" / "data"
MANIFEST_FILE = DATA_OUT_DIR / "portfolio_crops.js"

PAGE_SCALE = 160 / 72
FALLBACK_RENDER_SCALE = 220 / 72
FALLBACK_MIN_AREA_RATIO = 0.018
OBJECT_MIN_AREA_RATIO = 0.022
MIN_DIMENSION_PX = 220
DESIRED_SHEETS_PER_PROJECT = 5
IMAGES_PER_SHEET = 3

PROJECTS = {
    "l4": {
        "pdf": ROOT / "Rong Chen-L4-Portfolio2023-2024.pdf",
        "pages": [3, 4, 5, 6, 8, 10, 12, 14, 16, 18, 20, 24, 28, 32, 36, 40, 43, 46, 49, 51],
    },
    "reuse": {
        "pdf": next(ROOT.glob("RongChen_k2336224_Logbook_IR5101*Reuse.pdf")),
        "pages": [4, 5, 7, 8, 9, 10, 15, 17, 19, 21, 23, 24, 26, 28, 30, 34, 39, 42, 48, 50],
    },
    "fashion": {
        "pdf": ROOT / "RongChen_K2336224_Passion for Fashion_Portfolio.pdf",
        "pages": [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 18, 20, 23, 26],
    },
    "bar": {
        "pdf": ROOT / "RongChen_K2336224_Student Bar_portfolio.pdf",
        "pages": [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 15, 17, 19, 21, 23, 25, 27],
    },
}


def export_full_page(slug: str, page_number: int, page: pdfium.PdfPage) -> Path:
    target_dir = PAGE_OUT_DIR / slug
    target_dir.mkdir(parents=True, exist_ok=True)
    image = page.render(scale=PAGE_SCALE).to_pil().convert("RGB")
    target = target_dir / f"page-{page_number:02d}.png"
    image.save(target, quality=95)
    return target


def crop_score(width: int, height: int, area_ratio: float) -> float:
    orientation_bonus = 0.25 if width >= height else 0.12
    resolution_bonus = min(width * height / 1_500_000, 1.2)
    return area_ratio * 6 + orientation_bonus + resolution_bonus


def save_crop(
    image: Image.Image,
    slug: str,
    page_number: int,
    crop_index: int,
    source: str,
    area_ratio: float,
) -> dict:
    target_dir = CROP_OUT_DIR / slug
    target_dir.mkdir(parents=True, exist_ok=True)
    filename = f"page-{page_number:02d}-crop-{crop_index:02d}.jpg"
    target = target_dir / filename
    image.convert("RGB").save(target, quality=92, optimize=True)
    width, height = image.size
    return {
      "src": f"website_assets/images/crops/{slug}/{filename}",
      "page": page_number,
      "width": width,
      "height": height,
      "aspect": round(width / height, 4),
      "areaRatio": round(area_ratio, 5),
      "source": source,
      "score": round(crop_score(width, height, area_ratio), 5),
    }


def dedupe_boxes(boxes: list[tuple[int, int, int, int]], width: int, height: int) -> list[tuple[int, int, int, int]]:
    def area(box: tuple[int, int, int, int]) -> int:
        x0, y0, x1, y1 = box
        return max(0, x1 - x0) * max(0, y1 - y0)

    def overlap_ratio(a: tuple[int, int, int, int], b: tuple[int, int, int, int]) -> float:
        ax0, ay0, ax1, ay1 = a
        bx0, by0, bx1, by1 = b
        ix0 = max(ax0, bx0)
        iy0 = max(ay0, by0)
        ix1 = min(ax1, bx1)
        iy1 = min(ay1, by1)
        intersection = max(0, ix1 - ix0) * max(0, iy1 - iy0)
        if intersection <= 0:
            return 0.0
        return intersection / min(area(a), area(b))

    cleaned: list[tuple[int, int, int, int]] = []
    for box in sorted(boxes, key=area, reverse=True):
        x0, y0, x1, y1 = box
        if x1 - x0 < width * 0.1 or y1 - y0 < height * 0.1:
            continue
        aspect = (x1 - x0) / max(1, y1 - y0)
        if aspect > 8 or aspect < 0.12:
            continue
        if any(overlap_ratio(box, existing) > 0.82 for existing in cleaned):
            continue
        cleaned.append(box)
    return cleaned


def extract_image_object_crops(slug: str, page_number: int, page: pdfium.PdfPage) -> list[dict]:
    page_width, page_height = page.get_size()
    crop_records: list[dict] = []
    image_objects = [obj for obj in page.get_objects() if getattr(obj, "type", None) == 3]

    if len(image_objects) == 1:
        x0, y0, x1, y1 = image_objects[0].get_bounds()
        coverage = ((x1 - x0) * (y1 - y0)) / (page_width * page_height)
        if coverage > 0.82:
            return []

    crop_index = 1
    for obj in image_objects:
        x0, y0, x1, y1 = obj.get_bounds()
        bounds_width = max(0.0, x1 - x0)
        bounds_height = max(0.0, y1 - y0)
        area_ratio = (bounds_width * bounds_height) / (page_width * page_height)

        if area_ratio < OBJECT_MIN_AREA_RATIO:
            continue

        bitmap = obj.get_bitmap(render=False, scale_to_original=True).to_pil().convert("RGB")
        width, height = bitmap.size
        if width < MIN_DIMENSION_PX or height < MIN_DIMENSION_PX:
            continue

        crop_records.append(save_crop(bitmap, slug, page_number, crop_index, "pdf-object", area_ratio))
        crop_index += 1

    return crop_records


def extract_fallback_panel_crops(slug: str, page_number: int, page: pdfium.PdfPage) -> list[dict]:
    rendered = page.render(scale=FALLBACK_RENDER_SCALE).to_pil().convert("RGB")
    array = np.array(rendered)
    gray = cv2.cvtColor(array, cv2.COLOR_RGB2GRAY)
    mask = cv2.threshold(gray, 242, 255, cv2.THRESH_BINARY_INV)[1]

    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (15, 15))
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)

    height, width = mask.shape
    total_area = width * height
    _, _, stats, _ = cv2.connectedComponentsWithStats(mask, 8)

    boxes: list[tuple[int, int, int, int]] = []
    for index in range(1, stats.shape[0]):
        x, y, w, h, area = stats[index]
        area_ratio = area / total_area
        if area_ratio < FALLBACK_MIN_AREA_RATIO:
            continue
        if w < width * 0.12 or h < height * 0.12:
            continue

        pad_x = max(10, int(w * 0.025))
        pad_y = max(10, int(h * 0.025))
        x0 = max(0, x - pad_x)
        y0 = max(0, y - pad_y)
        x1 = min(width, x + w + pad_x)
        y1 = min(height, y + h + pad_y)
        boxes.append((x0, y0, x1, y1))

    crop_records: list[dict] = []
    for crop_index, (x0, y0, x1, y1) in enumerate(dedupe_boxes(boxes, width, height), start=1):
        crop = rendered.crop((x0, y0, x1, y1))
        crop_width, crop_height = crop.size
        if crop_width < MIN_DIMENSION_PX or crop_height < MIN_DIMENSION_PX:
            continue
        area_ratio = ((x1 - x0) * (y1 - y0)) / total_area
        crop_records.append(save_crop(crop, slug, page_number, crop_index, "fallback-segmentation", area_ratio))

    return crop_records


def evenly_sample(items: list[dict], count: int) -> list[dict]:
    if len(items) <= count:
        return items
    step = (len(items) - 1) / (count - 1)
    sampled = [items[round(step * index)] for index in range(count)]
    deduped: list[dict] = []
    seen: set[str] = set()
    for item in sampled:
        key = item["src"]
        if key in seen:
            continue
        deduped.append(item)
        seen.add(key)
    if len(deduped) == count:
        return deduped
    for item in items:
        key = item["src"]
        if key in seen:
            continue
        deduped.append(item)
        seen.add(key)
        if len(deduped) == count:
            break
    return deduped


def build_project_manifest(crops: list[dict]) -> dict:
    sorted_crops = sorted(
        crops,
        key=lambda item: (item["page"], -item["score"], -item["areaRatio"], item["src"]),
    )
    required = DESIRED_SHEETS_PER_PROJECT * IMAGES_PER_SHEET
    selected = evenly_sample(sorted_crops, min(required, len(sorted_crops)))
    return {
        "sheets": max(4, min(DESIRED_SHEETS_PER_PROJECT, len(selected) // IMAGES_PER_SHEET)),
        "crops": selected,
        "totalCrops": len(crops),
    }


def export_project(slug: str, pdf_path: Path, pages: list[int]) -> dict:
    pdf = pdfium.PdfDocument(str(pdf_path))
    all_crops: list[dict] = []

    for page_number in pages:
        page = pdf[page_number - 1]
        export_full_page(slug, page_number, page)

        page_crops = extract_image_object_crops(slug, page_number, page)
        if not page_crops:
            page_crops = extract_fallback_panel_crops(slug, page_number, page)
        all_crops.extend(page_crops)

    manifest = build_project_manifest(all_crops)
    manifest["pages"] = pages
    return manifest


def write_manifest(manifest: dict) -> None:
    DATA_OUT_DIR.mkdir(parents=True, exist_ok=True)
    payload = "window.portfolioCropManifest = " + json.dumps(manifest, ensure_ascii=False, indent=2) + ";\n"
    MANIFEST_FILE.write_text(payload, encoding="utf-8")


def main() -> None:
    PAGE_OUT_DIR.mkdir(parents=True, exist_ok=True)
    CROP_OUT_DIR.mkdir(parents=True, exist_ok=True)

    manifest: dict[str, dict] = {}
    for slug, config in PROJECTS.items():
        project_manifest = export_project(slug, config["pdf"], config["pages"])
        manifest[slug] = project_manifest
        print(f"exported {slug}: {len(project_manifest['crops'])} curated crops from {project_manifest['totalCrops']} extracted images")

    write_manifest(manifest)
    print(f"wrote manifest: {MANIFEST_FILE}")


if __name__ == "__main__":
    main()
