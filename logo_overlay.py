"""Logo overlay helpers for composed images."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from PIL import Image

if TYPE_CHECKING:
    from polaroid import Config


def get_logo_path(key: str | None, library: dict[str, str]) -> str | None:
    normalized = (key or "none").strip().lower()
    if normalized == "none":
        return None

    if normalized in library:
        return library[normalized]

    available = ", ".join(sorted(library.keys())) or "(empty)"
    print(f"[WARN] logo key '{key}' 不存在，可用 key: {available}")
    return None


def load_png_rgba(path: str | None) -> Image.Image | None:
    if not path:
        return None

    png_path = Path(path)
    if not png_path.exists():
        print(f"[WARN] logo 文件不存在: {path}")
        return None

    with Image.open(png_path) as logo:
        return logo.convert("RGBA")


def _resize_to_height(img: Image.Image, target_h: int) -> Image.Image:
    target_h = max(1, target_h)
    scale = target_h / img.height
    target_w = max(1, int(round(img.width * scale)))
    return img.resize((target_w, target_h), Image.Resampling.LANCZOS)


def _compose_brand_model(brand_img: Image.Image | None, model_img: Image.Image | None, gap: int) -> Image.Image | None:
    if brand_img is None and model_img is None:
        return None
    if brand_img is None:
        return model_img
    if model_img is None:
        return brand_img

    gap = max(0, gap)
    width = brand_img.width + gap + model_img.width
    height = max(brand_img.height, model_img.height)
    overlay = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    overlay.alpha_composite(brand_img, (0, (height - brand_img.height) // 2))
    overlay.alpha_composite(model_img, (brand_img.width + gap, (height - model_img.height) // 2))
    return overlay


def apply_logo_overlay(composed: Image.Image, cfg: "Config") -> Image.Image:
    short = min(composed.width, composed.height)
    margin = int(round(short * cfg.logo.margin_ratio))
    target_h = max(1, int(round(short * cfg.logo.scale_ratio)))
    gap = int(round(short * cfg.logo.gap_ratio))

    brand_path = cfg.logo.brand_path or get_logo_path(cfg.logo.brand_key, cfg.logo.library)
    model_path = cfg.logo.model_path or get_logo_path(cfg.logo.model_key, cfg.logo.library)

    brand_img = load_png_rgba(brand_path)
    model_img = load_png_rgba(model_path)
    if brand_img is not None:
        brand_img = _resize_to_height(brand_img, target_h)
    if model_img is not None:
        model_img = _resize_to_height(model_img, target_h)

    overlay = _compose_brand_model(brand_img, model_img, gap)
    if overlay is None:
        return composed.convert("RGBA")

    alpha = overlay.split()[-1].point(lambda a: int(a * cfg.logo.opacity))
    overlay.putalpha(alpha)

    w, h = composed.size
    overlay_w, overlay_h = overlay.size

    if cfg.logo.placement == "frame_bottom_center":
        band_top = int(round(h * cfg.logo.bottom_band.top_ratio))
        band_bottom = int(round(h * cfg.logo.bottom_band.bottom_ratio))
        band_top = max(0, min(band_top, h - 1))
        band_bottom = max(band_top + 1, min(band_bottom, h))
        band_h = max(1, band_bottom - band_top)

        x = (w - overlay_w) // 2
        y = band_top + int(round((band_h - overlay_h) * cfg.logo.bottom_band.y_bias))
        y = min(max(y, band_top), band_bottom - overlay_h)

        y = min(y, h - margin - overlay_h)
        x = max(margin, min(x, w - margin - overlay_w))
    elif cfg.logo.placement == "bottom_center":
        x = (w - overlay_w) // 2
        y = h - margin - overlay_h
    elif cfg.logo.placement == "custom":
        x = int(round(w * cfg.logo.custom_xy_ratio[0] - overlay_w))
        y = int(round(h * cfg.logo.custom_xy_ratio[1] - overlay_h))
    else:
        x = w - margin - overlay_w
        y = h - margin - overlay_h

    x = max(0, min(x, max(0, w - overlay_w)))
    y = max(0, min(y, max(0, h - overlay_h)))

    composed_rgba = composed.convert("RGBA")
    composed_rgba.alpha_composite(overlay, (x, y))
    return composed_rgba
