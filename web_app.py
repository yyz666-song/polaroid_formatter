#!/usr/bin/env python3
"""Streamlit frontend for Polaroid Formatter."""

from __future__ import annotations

import io
from pathlib import Path

import streamlit as st
from PIL import Image, ImageOps

from polaroid import load_config, render_polaroid

st.set_page_config(page_title="Polaroid Formatter", page_icon="📸", layout="wide")

st.title("📸 Polaroid Formatter")
st.caption("上传图片，一键生成统一宝丽来风格成片。")

with st.sidebar:
    st.header("设置")
    config_path = st.text_input("配置文件路径", value="config.json")
    quality = st.slider("导出 JPEG 质量", min_value=1, max_value=100, value=92)

try:
    cfg = load_config(Path(config_path))
except Exception as exc:  # noqa: BLE001
    st.error(f"配置加载失败：{exc}")
    st.stop()

uploaded = st.file_uploader("拖拽或选择图片", type=["jpg", "jpeg", "png", "webp"])

if uploaded is None:
    st.info("请先上传一张图片。")
    st.stop()

src = Image.open(uploaded)
corrected = ImageOps.exif_transpose(src).convert("RGB")
result = render_polaroid(corrected, cfg)

left, right = st.columns(2)
with left:
    st.subheader("原图")
    st.image(corrected, use_container_width=True)
with right:
    st.subheader("效果图")
    st.image(result, use_container_width=True)

buf = io.BytesIO()
result.save(buf, format="JPEG", quality=quality, optimize=True, progressive=True)

st.download_button(
    "下载成片（JPEG）",
    data=buf.getvalue(),
    file_name=f"{Path(uploaded.name).stem}_fmt.jpg",
    mime="image/jpeg",
)
