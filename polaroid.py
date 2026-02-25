#!/usr/bin/env python3
"""Batch formatter for polaroid scanned photos."""

from __future__ import annotations

import argparse
import json
import math
import shutil
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from PIL import Image, ImageEnhance, ImageFilter, ImageOps

from logo_overlay import apply_single_logo_bottom_center, resolve_logo_path
from logo_settings import AUTO_SCAN, BOTTOM_BAND, LOGO_DIR, LOGO_ID, LOGO_LIST, MARGIN_RATIO, OPACITY, SCALE_RATIO

MIN_SAFE_KEEP_RATIO = 0.60
GOLDEN_RATIO = 1.618


@dataclass
class Canvas:
    width: int
    height: int


@dataclass
class Foreground:
    paper_scale_mode: str
    paper_scale_override: float | None


@dataclass
class SafeCrop:
    left: float
    right: float
    top: float
    bottom: float


@dataclass
class Background:
    safe_crop: SafeCrop
    extra_scale: float
    brightness: float
    saturation: float


@dataclass
class Sharpen:
    enabled: bool
    target: str
    radius: float
    percent: int
    threshold: int




@dataclass
class LogoItem:
    type: str
    image_path: str | None
    text: str | None


@dataclass
class LogoConfig:
    enabled: bool
    placement: str
    custom_xy_ratio: tuple[float, float]
    margin_ratio: float
    scale_ratio: float
    gap_ratio: float
    opacity: float
    brand: LogoItem
    model: LogoItem
    text_color: tuple[int, int, int]
    font_path: str | None

@dataclass
class LogoConfig:
    enabled: bool
    placement: str
    custom_xy_ratio: tuple[float, float]
    margin_ratio: float
    scale_ratio: float
    gap_ratio: float
    opacity: float
    library: dict[str, str]
    brand_key: str
    model_key: str
    brand_path: str | None
    model_path: str | None


@dataclass
class BottomBand:
    top_ratio: float
    bottom_ratio: float
    y_bias: float


@dataclass
class LogoConfig:
    enabled: bool
    placement: str
    custom_xy_ratio: tuple[float, float]
    margin_ratio: float
    scale_ratio: float
    gap_ratio: float
    opacity: float
    bottom_band: BottomBand
    library: dict[str, str]
    brand_key: str
    model_key: str
    brand_path: str | None
    model_path: str | None


@dataclass
class BottomBand:
    top_ratio: float
    bottom_ratio: float
    y_bias: float


@dataclass
class LogoConfig:
    enabled: bool
    placement: str
    custom_xy_ratio: tuple[float, float]
    margin_ratio: float
    scale_ratio: float
    gap_ratio: float
    opacity: float
    bottom_band: BottomBand
    library: dict[str, str]
    brand_key: str
    model_key: str
    brand_path: str | None
    model_path: str | None


@dataclass
class BottomBand:
    top_ratio: float
    bottom_ratio: float
    y_bias: float


@dataclass
class LogoConfig:
    enabled: bool
    placement: str
    custom_xy_ratio: tuple[float, float]
    margin_ratio: float
    scale_ratio: float
    gap_ratio: float
    opacity: float
    bottom_band: BottomBand
    library: dict[str, str]
    brand_key: str
    model_key: str
    brand_path: str | None
    model_path: str | None


@dataclass
class BottomBand:
    top_ratio: float
    bottom_ratio: float
    y_bias: float


@dataclass
class LogoConfig:
    enabled: bool
    placement: str
    custom_xy_ratio: tuple[float, float]
    margin_ratio: float
    scale_ratio: float
    gap_ratio: float
    opacity: float
    bottom_band: BottomBand
    library: dict[str, str]
    brand_key: str
    model_key: str
    brand_path: str | None
    model_path: str | None


@dataclass
class Config:
    inbox_dir: Path
    out_dir: Path
    done_dir: Path
    output_suffix: str
    output_extension: str
    canvas: Canvas
    foreground: Foreground
    background: Background
    sharpen: Sharpen
    logo: LogoConfig
    jpeg_quality: int
    move_processed_to_done: bool
    supported_extensions: tuple[str, ...]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="批量处理宝丽来扫描图，输出统一版式 JPEG。")
    parser.add_argument("--config", default="config.json", help="配置文件路径（默认: config.json）")
    parser.add_argument("--dry-run", action="store_true", help="仅打印将要处理的文件，不实际写出/移动")
    parser.add_argument("--once", action="store_true", help="单次运行后退出（为兼容自动化流程保留该参数）")
    return parser.parse_args()


def load_config(path: Path) -> Config:
    if not path.exists():
        raise FileNotFoundError(f"配置文件不存在: {path}")

    with path.open("r", encoding="utf-8") as f:
        raw = json.load(f)

    try:
        canvas = Canvas(width=int(raw["canvas"]["width"]), height=int(raw["canvas"]["height"]))

        fg_raw = raw.get("foreground", {})
        foreground = Foreground(
            paper_scale_mode=str(fg_raw.get("paper_scale_mode", "golden")).lower(),
            paper_scale_override=(
                None
                if fg_raw.get("paper_scale_override") is None
                else float(fg_raw.get("paper_scale_override"))
            ),
        )

        bg_raw = raw.get("background", {})
        crop_raw = bg_raw.get("bg_safe_crop", {})
        background = Background(
            safe_crop=SafeCrop(
                left=float(crop_raw.get("l", 0.10)),
                right=float(crop_raw.get("r", 0.10)),
                top=float(crop_raw.get("t", 0.10)),
                bottom=float(crop_raw.get("b", 0.22)),
            ),
            extra_scale=float(bg_raw.get("bg_extra_scale", 1.35)),
            brightness=float(bg_raw.get("brightness", 0.82)),
            saturation=float(bg_raw.get("saturation", 0.75)),
        )

        sharpen = Sharpen(
            enabled=bool(raw.get("sharpen_enabled", True)),
            target=str(raw.get("sharpen_target", "foreground")).lower(),
            radius=float(raw.get("sharpen_radius", 1.6)),
            percent=int(raw.get("sharpen_percent", 150)),
            threshold=int(raw.get("sharpen_threshold", 3)),
        )

        logo_raw = raw.get("logo", {})
        library_raw = logo_raw.get("library", {})
        if not isinstance(library_raw, dict):
            raise ValueError("logo.library 必须是对象映射")
        logo_library = {str(k).lower(): str(v) for k, v in library_raw.items()}

        custom_xy_raw = logo_raw.get("custom_xy_ratio", [0.90, 0.93])
        custom_xy_ratio = (float(custom_xy_raw[0]), float(custom_xy_raw[1]))

        band_raw = logo_raw.get("bottom_band", {})
        bottom_band = BottomBand(
            top_ratio=float(band_raw.get("top_ratio", 0.78)),
            bottom_ratio=float(band_raw.get("bottom_ratio", 0.98)),
            y_bias=float(band_raw.get("y_bias", 0.72)),
        )

        logo = LogoConfig(
            enabled=bool(logo_raw.get("enabled", False)),
            placement=str(logo_raw.get("placement", "bottom_right")).lower(),
            custom_xy_ratio=custom_xy_ratio,
            margin_ratio=float(logo_raw.get("margin_ratio", 0.035)),
            scale_ratio=float(logo_raw.get("scale_ratio", 0.060)),
            gap_ratio=float(logo_raw.get("gap_ratio", 0.012)),
            opacity=float(logo_raw.get("opacity", 0.90)),
            bottom_band=bottom_band,
            library=logo_library,
            brand_key=str(logo_raw.get("brand_key", "none")).lower(),
            model_key=str(logo_raw.get("model_key", "none")).lower(),
            brand_path=(str(logo_raw.get("brand_path")) if logo_raw.get("brand_path") is not None else None),
            model_path=(str(logo_raw.get("model_path")) if logo_raw.get("model_path") is not None else None),
        )

        config = Config(
            inbox_dir=Path(raw["inbox_dir"]),
            out_dir=Path(raw["out_dir"]),
            done_dir=Path(raw["done_dir"]),
            output_suffix=str(raw.get("output_suffix", "_fmt")),
            output_extension=str(raw.get("output_extension", "jpg")).lower().lstrip("."),
            canvas=canvas,
            foreground=foreground,
            background=background,
            sharpen=sharpen,
            logo=logo,
            jpeg_quality=int(raw.get("jpeg_quality", 92)),
            move_processed_to_done=bool(raw.get("move_processed_to_done", True)),
            supported_extensions=tuple(
                ext.lower() for ext in raw.get("supported_extensions", [".jpg", ".jpeg", ".png", ".webp"])
            ),
        )
    except (AttributeError, IndexError, KeyError, TypeError, ValueError) as exc:
        raise ValueError(f"配置文件格式错误: {exc}") from exc

    validate_config(config)
    return config


def validate_config(config: Config) -> None:
    if config.canvas.width <= 0 or config.canvas.height <= 0:
        raise ValueError("canvas.width 和 canvas.height 必须为正整数")
    if config.foreground.paper_scale_mode not in {"golden", "fit"}:
        raise ValueError("foreground.paper_scale_mode 仅支持 golden 或 fit")
    if config.foreground.paper_scale_override is not None and not (0 < config.foreground.paper_scale_override <= 1):
        raise ValueError("foreground.paper_scale_override 必须在 (0, 1] 范围")

    crop = config.background.safe_crop
    for name, value in {
        "background.bg_safe_crop.l": crop.left,
        "background.bg_safe_crop.r": crop.right,
        "background.bg_safe_crop.t": crop.top,
        "background.bg_safe_crop.b": crop.bottom,
    }.items():
        if value < 0:
            raise ValueError(f"{name} 不能为负数")

    if crop.left + crop.right >= (1 - MIN_SAFE_KEEP_RATIO):
        raise ValueError("background.bg_safe_crop 左右裁切总和过大")
    if crop.top + crop.bottom >= (1 - MIN_SAFE_KEEP_RATIO):
        raise ValueError("background.bg_safe_crop 上下裁切总和过大")

    if config.background.extra_scale < 1.0:
        raise ValueError("background.bg_extra_scale 不能小于 1.0")
    if config.jpeg_quality < 1 or config.jpeg_quality > 100:
        raise ValueError("jpeg_quality 必须在 1~100 范围内")
    if config.sharpen.target not in {"foreground", "all"}:
        raise ValueError("sharpen_target 仅支持 foreground 或 all")
    if config.sharpen.radius < 0 or config.sharpen.percent < 0 or config.sharpen.threshold < 0:
        raise ValueError("锐化参数不能为负数")

    if config.logo.placement not in {"bottom_right", "bottom_center", "custom", "frame_bottom_center"}:
        raise ValueError("logo.placement 仅支持 bottom_right、bottom_center、custom、frame_bottom_center")
    if any(v < 0 or v > 0.2 for v in (config.logo.margin_ratio, config.logo.scale_ratio, config.logo.gap_ratio)):
        raise ValueError("logo 比例参数需在 0~0.2 范围")
    if not (0 <= config.logo.opacity <= 1):
        raise ValueError("logo.opacity 必须在 0~1 范围")
    if len(config.logo.custom_xy_ratio) != 2 or any(v < 0 or v > 1 for v in config.logo.custom_xy_ratio):
        raise ValueError("logo.custom_xy_ratio 需要两个 0~1 范围的值")
    if not (0 <= config.logo.bottom_band.top_ratio < config.logo.bottom_band.bottom_ratio <= 1):
        raise ValueError("logo.bottom_band 的 top_ratio/bottom_ratio 需要满足 0<=top<bottom<=1")
    if not (0 <= config.logo.bottom_band.y_bias <= 1):
        raise ValueError("logo.bottom_band.y_bias 必须在 0~1 范围")
    if config.logo.brand_key == "" or config.logo.model_key == "":
        raise ValueError("logo.brand_key 与 logo.model_key 不能为空")
    if any(not key for key in config.logo.library):
        raise ValueError("logo.library 的 key 不能为空")


def iter_images(inbox: Path, exts: tuple[str, ...]) -> Iterable[Path]:
    if not inbox.exists():
        return []
    allowed = {ext.lower() for ext in exts}
    return sorted(p for p in inbox.iterdir() if p.is_file() and p.suffix.lower() in allowed)


def resize_cover(img: Image.Image, target_size: tuple[int, int]) -> Image.Image:
    tw, th = target_size
    scale = max(tw / img.width, th / img.height)
    new_size = (max(1, int(round(img.width * scale))), max(1, int(round(img.height * scale))))
    resized = img.resize(new_size, Image.Resampling.LANCZOS)
    left = (resized.width - tw) // 2
    top = (resized.height - th) // 2
    return resized.crop((left, top, left + tw, top + th))


def resize_contain(img: Image.Image, max_size: tuple[int, int]) -> Image.Image:
    return ImageOps.contain(img, max_size, method=Image.Resampling.LANCZOS)


def _clamp_non_symmetric_crop(crop: SafeCrop) -> SafeCrop:
    max_pair_crop = 1.0 - MIN_SAFE_KEEP_RATIO

    lr_total = crop.left + crop.right
    tb_total = crop.top + crop.bottom

    if lr_total > max_pair_crop and lr_total > 0:
        scale = max_pair_crop / lr_total
        left = crop.left * scale
        right = crop.right * scale
    else:
        left = crop.left
        right = crop.right

    if tb_total > max_pair_crop and tb_total > 0:
        scale = max_pair_crop / tb_total
        top = crop.top * scale
        bottom = crop.bottom * scale
    else:
        top = crop.top
        bottom = crop.bottom

    return SafeCrop(left=left, right=right, top=top, bottom=bottom)


def apply_safe_crop(img: Image.Image, crop: SafeCrop) -> Image.Image:
    """Apply non-symmetric crop; fallback to safe minimum keep ratio if too aggressive."""
    safe_crop = _clamp_non_symmetric_crop(crop)

    left = int(round(img.width * safe_crop.left))
    right = img.width - int(round(img.width * safe_crop.right))
    top = int(round(img.height * safe_crop.top))
    bottom = img.height - int(round(img.height * safe_crop.bottom))

    cropped_w = right - left
    cropped_h = bottom - top
    min_w = max(1, int(math.floor(img.width * MIN_SAFE_KEEP_RATIO)))
    min_h = max(1, int(math.floor(img.height * MIN_SAFE_KEEP_RATIO)))

    if cropped_w < min_w or cropped_h < min_h or cropped_w < 1 or cropped_h < 1:
        return img

    return img.crop((left, top, right, bottom))


def get_paper_scale_ratio(cfg: Config) -> float:
    if cfg.foreground.paper_scale_override is not None:
        return cfg.foreground.paper_scale_override
    if cfg.foreground.paper_scale_mode == "golden":
        return 1.0 / GOLDEN_RATIO
    return 0.78


def build_background(corrected: Image.Image, cfg: Config) -> Image.Image:
    canvas_size = (cfg.canvas.width, cfg.canvas.height)
    bg_src = apply_safe_crop(corrected, cfg.background.safe_crop)

    scaled_target = (
        int(round(cfg.canvas.width * cfg.background.extra_scale)),
        int(round(cfg.canvas.height * cfg.background.extra_scale)),
    )
    scaled_cover = resize_cover(bg_src, scaled_target)
    bg = resize_cover(scaled_cover, canvas_size)

    bg = ImageEnhance.Color(bg).enhance(cfg.background.saturation)
    bg = ImageEnhance.Brightness(bg).enhance(cfg.background.brightness)
    return bg


def apply_unsharp(img: Image.Image, sharpen: Sharpen) -> Image.Image:
    return img.filter(
        ImageFilter.UnsharpMask(
            radius=sharpen.radius,
            percent=sharpen.percent,
            threshold=sharpen.threshold,
        )
    )


def process_one(image_path: Path, cfg: Config, dry_run: bool = False) -> None:
    output_name = f"{image_path.stem}{cfg.output_suffix}.{cfg.output_extension}"
    output_path = cfg.out_dir / output_name
    done_path = cfg.done_dir / image_path.name

    print(f"[INFO] 处理: {image_path.name}")
    print(f"       输出: {output_path}")
    if cfg.move_processed_to_done:
        print(f"       移动原图: {done_path}")

    if dry_run:
        return

    with Image.open(image_path) as src:
        corrected = ImageOps.exif_transpose(src).convert("RGB")
        bg = build_background(corrected, cfg)

        paper_ratio = get_paper_scale_ratio(cfg)
        target_paper_w = max(1, int(round(cfg.canvas.width * paper_ratio)))
        target_paper_h = max(1, int(round(cfg.canvas.height * paper_ratio)))
        fg = resize_contain(corrected, (target_paper_w, target_paper_h))

        if cfg.sharpen.enabled and cfg.sharpen.target in {"foreground", "all"}:
            fg = apply_unsharp(fg, cfg.sharpen)

        composed = bg.copy()
        x = (cfg.canvas.width - fg.width) // 2
        y = (cfg.canvas.height - fg.height) // 2
        composed.paste(fg, (x, y))

        if cfg.sharpen.enabled and cfg.sharpen.target == "all":
            composed = apply_unsharp(composed, cfg.sharpen)

        selected_logo_path = resolve_logo_path(
            logo_id=LOGO_ID,
            logo_dir=LOGO_DIR,
            logo_list=LOGO_LIST,
            auto_scan=AUTO_SCAN,
        )
        if selected_logo_path:
            composed = apply_single_logo_bottom_center(
                composed=composed,
                logo_path=selected_logo_path,
                margin_ratio=MARGIN_RATIO,
                scale_ratio=SCALE_RATIO,
                opacity=OPACITY,
                bottom_band_cfg=BOTTOM_BAND,
            )

        composed = composed.convert("RGB")
        composed.save(
            output_path,
            format="JPEG",
            quality=cfg.jpeg_quality,
            optimize=True,
            progressive=True,
        )

    if cfg.move_processed_to_done:
        shutil.move(str(image_path), str(done_path))


def ensure_dirs(cfg: Config, dry_run: bool) -> None:
    dirs = [cfg.inbox_dir, cfg.out_dir]
    if cfg.move_processed_to_done:
        dirs.append(cfg.done_dir)

    for d in dirs:
        if dry_run:
            print(f"[DRY-RUN] 确保目录存在: {d}")
        else:
            d.mkdir(parents=True, exist_ok=True)


def main() -> int:
    args = parse_args()

    try:
        cfg = load_config(Path(args.config))
        ensure_dirs(cfg, dry_run=args.dry_run)

        images = list(iter_images(cfg.inbox_dir, cfg.supported_extensions))
        if not images:
            print("No images found in inbox/")
            return 0

        for img_path in images:
            try:
                process_one(img_path, cfg, dry_run=args.dry_run)
            except Exception as exc:  # noqa: BLE001
                print(f"[ERROR] 处理失败 {img_path.name}: {exc}", file=sys.stderr)

        if args.once:
            print("[INFO] 已完成单次处理（--once）。")

        print("[INFO] 处理完成。")
        return 0
    except Exception as exc:  # noqa: BLE001
        print(f"[FATAL] {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
