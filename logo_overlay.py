"""Logo overlay helpers for composed images."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from PIL import Image, ImageDraw, ImageFont

if TYPE_CHECKING:
    from polaroid import Config


def load_logo_image(path: str | None) -> Image.Image | None:
    if not path:
        return None

    image_path = Path(path)
    if not image_path.exists():
        return None

    with Image.open(image_path) as img:
        return img.convert("RGBA")


def _resize_to_height(img: Image.Image, target_h: int) -> Image.Image:
    target_h = max(1, target_h)
    scale = target_h / img.height
    target_w = max(1, int(round(img.width * scale)))
    return img.resize((target_w, target_h), Image.Resampling.LANCZOS)


def render_text(text: str, font_path: str | None, target_h: int, color: tuple[int, int, int]) -> Image.Image:
    content = text.strip()
    if not content:
        return Image.new("RGBA", (1, max(1, target_h)), (0, 0, 0, 0))

    draw_probe = ImageDraw.Draw(Image.new("RGBA", (1, 1), (0, 0, 0, 0)))

    if font_path:
        try:
            font = ImageFont.truetype(font_path, size=max(1, target_h))
        except OSError:
            font = ImageFont.load_default()
    else:
        font = ImageFont.load_default()

    bbox = draw_probe.textbbox((0, 0), content, font=font)
    width = max(1, bbox[2] - bbox[0])
    height = max(1, bbox[3] - bbox[1])

    text_img = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(text_img)
    draw.text((-bbox[0], -bbox[1]), content, font=font, fill=(*color, 255))

    if text_img.height != max(1, target_h):
        text_img = _resize_to_height(text_img, target_h)

    return text_img


def compose_brand_model(brand_img: Image.Image | None, model_img: Image.Image | None, gap: int) -> Image.Image:
    elements = [img for img in (brand_img, model_img) if img is not None]
    if not elements:
        return Image.new("RGBA", (1, 1), (0, 0, 0, 0))

    if len(elements) == 1:
        return elements[0]

    gap = max(0, gap)
    width = brand_img.width + gap + model_img.width
    height = max(brand_img.height, model_img.height)
    overlay = Image.new("RGBA", (width, height), (0, 0, 0, 0))

    y1 = (height - brand_img.height) // 2
    y2 = (height - model_img.height) // 2
    overlay.alpha_composite(brand_img, (0, y1))
    overlay.alpha_composite(model_img, (brand_img.width + gap, y2))
    return overlay


def _build_logo_item(item, target_h: int, color: tuple[int, int, int], font_path: str | None) -> Image.Image | None:
    item_type = item.type.lower()
    if item_type == "image":
        img = load_logo_image(item.image_path)
        return None if img is None else _resize_to_height(img, target_h)

    if item_type == "text":
        if not item.text:
            return None
        return render_text(item.text, font_path, target_h, color)

    return None


def apply_logo_overlay(composed: Image.Image, cfg: "Config") -> Image.Image:
    short = min(composed.width, composed.height)
    margin = int(round(short * cfg.logo.margin_ratio))
    target_h = max(1, int(round(short * cfg.logo.scale_ratio)))
    gap = int(round(short * cfg.logo.gap_ratio))

    brand_img = _build_logo_item(cfg.logo.brand, target_h, cfg.logo.text_color, cfg.logo.font_path)
    model_img = _build_logo_item(cfg.logo.model, target_h, cfg.logo.text_color, cfg.logo.font_path)
    overlay = compose_brand_model(brand_img, model_img, gap)

    if overlay.width <= 1 and overlay.height <= 1:
        return composed.convert("RGBA")

    alpha = overlay.split()[-1].point(lambda a: int(a * cfg.logo.opacity))
    overlay.putalpha(alpha)

    w, h = composed.size
    overlay_w, overlay_h = overlay.size

    if cfg.logo.placement == "bottom_right":
        x = w - margin - overlay_w
        y = h - margin - overlay_h
    elif cfg.logo.placement == "bottom_center":
        x = (w - overlay_w) // 2
        y = h - margin - overlay_h
    else:
        x = int(round(w * cfg.logo.custom_xy_ratio[0] - overlay_w))
        y = int(round(h * cfg.logo.custom_xy_ratio[1] - overlay_h))

    x = max(0, min(x, max(0, w - overlay_w)))
    y = max(0, min(y, max(0, h - overlay_h)))

    composed_rgba = composed.convert("RGBA")
    composed_rgba.alpha_composite(overlay, dest=(x, y))
    return composed_rgba
