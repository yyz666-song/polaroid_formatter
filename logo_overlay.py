"""Logo overlay helpers for composed images."""

from __future__ import annotations

from pathlib import Path

from PIL import Image


def _normalize_name(name: str) -> str:
    stem = Path(name).stem
    return "".join(ch for ch in stem.lower() if ch != "_")


def _available_png_names(logo_dir: str) -> list[str]:
    root = Path(logo_dir)
    return sorted(p.name for p in root.glob("*.png") if p.is_file())


def _resolve_with_fuzzy_match(logo_dir: str, expected_name: str) -> str | None:
    available = _available_png_names(logo_dir)
    expected_key = _normalize_name(expected_name)
    matched = [name for name in available if _normalize_name(name) == expected_key]

    if len(matched) == 1:
        resolved = str((Path(logo_dir) / matched[0]).resolve())
        print(f"[WARN] logo '{expected_name}' 未找到，自动匹配为 '{matched[0]}'")
        print(f"[INFO] 最终选用 logo: {resolved}")
        return str(Path(logo_dir) / matched[0])

    available_txt = ", ".join(available) or "(empty)"
    print(f"[WARN] assets/logos 可用 PNG: {available_txt}")

    if len(matched) > 1:
        print(f"[WARN] logo '{expected_name}' 匹配到多个候选: {', '.join(matched)}，已跳过")
    else:
        print(f"[WARN] logo '{expected_name}' 未找到且无宽松匹配，已跳过")

    return None


def resolve_logo_path(
    logo_id: int,
    logo_dir: str,
    logo_list: list[str] | None = None,
    auto_scan: bool = False,
) -> str | None:
    if logo_id == 1:
        return None

    idx = logo_id - 2
    root = Path(logo_dir)

    if auto_scan:
        candidates = _available_png_names(logo_dir)
    else:
        candidates = list(logo_list or [])

    if idx < 0 or idx >= len(candidates):
        available = ", ".join(candidates) or "(empty)"
        print(f"[WARN] LOGO_ID={logo_id} 越界，可用 logo 列表: {available}")
        return None

    selected_name = candidates[idx]
    selected_path = root / selected_name

    if selected_path.exists():
        print(f"[INFO] 最终选用 logo: {selected_path.resolve()}")
        return str(selected_path)

    return _resolve_with_fuzzy_match(logo_dir, selected_name)


def _load_png_rgba(path: str | None) -> Image.Image | None:
    if not path:
        return None

    p = Path(path)
    if not p.exists():
        print(f"[WARN] logo 文件不存在: {path}")
        return None

    with Image.open(p) as img:
        return img.convert("RGBA")


def _resize_to_height(img: Image.Image, target_h: int) -> Image.Image:
    target_h = max(1, target_h)
    scale = target_h / img.height
    target_w = max(1, int(round(img.width * scale)))
    return img.resize((target_w, target_h), Image.Resampling.LANCZOS)


def apply_single_logo_bottom_center(
    composed: Image.Image,
    logo_path: str,
    margin_ratio: float,
    scale_ratio: float,
    opacity: float,
    bottom_band_cfg: dict[str, float],
) -> Image.Image:
    logo = _load_png_rgba(logo_path)
    if logo is None:
        return composed.convert("RGBA")

    w, h = composed.size
    short = min(w, h)
    margin = int(round(short * margin_ratio))
    target_h = max(1, int(round(short * scale_ratio)))

    logo = _resize_to_height(logo, target_h)
    logo_w, logo_h = logo.size

    top_ratio = float(bottom_band_cfg.get("top_ratio", 0.78))
    bottom_ratio = float(bottom_band_cfg.get("bottom_ratio", 0.98))
    y_bias = float(bottom_band_cfg.get("y_bias", 0.72))

    band_top = int(round(h * top_ratio))
    band_bottom = int(round(h * bottom_ratio))
    band_top = max(0, min(band_top, h - 1))
    band_bottom = max(band_top + 1, min(band_bottom, h))
    band_h = max(1, band_bottom - band_top)

    x = (w - logo_w) // 2
    y = band_top + int(round((band_h - logo_h) * y_bias))

    y = min(max(y, band_top), band_bottom - logo_h)
    y = min(y, h - margin - logo_h)
    x = max(margin, min(x, w - margin - logo_w))

    logo_alpha = logo.split()[-1].point(lambda a: int(a * opacity))
    logo.putalpha(logo_alpha)

    composed_rgba = composed.convert("RGBA")
    composed_rgba.alpha_composite(logo, (x, y))
    return composed_rgba
