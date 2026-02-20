#!/usr/bin/env python3
"""Batch formatter for polaroid scanned photos."""

from __future__ import annotations

import argparse
import json
import shutil
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from PIL import Image, ImageEnhance, ImageFilter, ImageOps

MIN_SAFE_KEEP_RATIO = 0.60


@dataclass
class Canvas:
    width: int
    height: int


@dataclass
class Foreground:
    width_ratio: float


@dataclass
class Background:
    safe_crop_pct: float
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
        foreground = Foreground(width_ratio=float(raw["foreground"]["width_ratio"]))

        bg_raw = raw.get("background", {})
        background = Background(
            safe_crop_pct=float(bg_raw.get("bg_safe_crop_pct", 0.14)),
            extra_scale=float(bg_raw.get("bg_extra_scale", 1.25)),
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
            jpeg_quality=int(raw.get("jpeg_quality", 92)),
            move_processed_to_done=bool(raw.get("move_processed_to_done", True)),
            supported_extensions=tuple(
                ext.lower() for ext in raw.get("supported_extensions", [".jpg", ".jpeg", ".png", ".webp"])
            ),
        )
    except (KeyError, TypeError, ValueError) as exc:
        raise ValueError(f"配置文件格式错误: {exc}") from exc

    validate_config(config)
    return config


def validate_config(config: Config) -> None:
    if config.canvas.width <= 0 or config.canvas.height <= 0:
        raise ValueError("canvas.width 和 canvas.height 必须为正整数")
    if not (0 < config.foreground.width_ratio <= 1):
        raise ValueError("foreground.width_ratio 必须在 (0, 1] 范围内")
    if not (0 <= config.background.safe_crop_pct < 0.5):
        raise ValueError("background.bg_safe_crop_pct 必须在 [0, 0.5) 范围内")
    if config.background.extra_scale < 1.0:
        raise ValueError("background.bg_extra_scale 不能小于 1.0")
    if config.jpeg_quality < 1 or config.jpeg_quality > 100:
        raise ValueError("jpeg_quality 必须在 1~100 范围内")
    if config.sharpen.target not in {"foreground", "all"}:
        raise ValueError("sharpen_target 仅支持 foreground 或 all")
    if config.sharpen.radius < 0:
        raise ValueError("sharpen_radius 不能为负数")
    if config.sharpen.percent < 0:
        raise ValueError("sharpen_percent 不能为负数")
    if config.sharpen.threshold < 0:
        raise ValueError("sharpen_threshold 不能为负数")


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


def apply_safe_crop(img: Image.Image, crop_pct: float) -> Image.Image:
    """Crop same percent from all sides with safety fallback.

    If requested crop is too aggressive, clamp to keep at least 60% width/height.
    """
    if crop_pct <= 0:
        return img

    max_crop_by_keep = (1.0 - MIN_SAFE_KEEP_RATIO) / 2.0
    effective_crop = min(crop_pct, max_crop_by_keep)

    left = int(round(img.width * effective_crop))
    top = int(round(img.height * effective_crop))
    right = img.width - left
    bottom = img.height - top

    cropped_w = right - left
    cropped_h = bottom - top
    if cropped_w < 1 or cropped_h < 1:
        return img

    return img.crop((left, top, right, bottom))


def build_background(corrected: Image.Image, cfg: Config) -> Image.Image:
    canvas_size = (cfg.canvas.width, cfg.canvas.height)
    bg_src = apply_safe_crop(corrected, cfg.background.safe_crop_pct)

    # 先按更大目标做 cover，再中心裁回画布，实现“额外放大”且不露边。
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
    canvas_size = (cfg.canvas.width, cfg.canvas.height)
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

        target_fg_w = int(cfg.canvas.width * cfg.foreground.width_ratio)
        fg = resize_contain(corrected, (target_fg_w, cfg.canvas.height))

        if cfg.sharpen.enabled and cfg.sharpen.target in {"foreground", "all"}:
            fg = apply_unsharp(fg, cfg.sharpen)

        composed = bg.copy()
        x = (cfg.canvas.width - fg.width) // 2
        y = (cfg.canvas.height - fg.height) // 2
        composed.paste(fg, (x, y))

        if cfg.sharpen.enabled and cfg.sharpen.target == "all":
            composed = apply_unsharp(composed, cfg.sharpen)

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
            print(f"[INFO] 未在 {cfg.inbox_dir} 找到可处理图片。")
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
