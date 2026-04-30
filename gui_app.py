#!/usr/bin/env python3
"""Desktop GUI for Polaroid Formatter (suitable for packaging into .exe)."""

from __future__ import annotations

import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

from PIL import Image, ImageOps, ImageTk

from polaroid import load_config, render_polaroid


class PolaroidGUI:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title("Polaroid Formatter")
        self.root.geometry("1200x760")

        self.config_path = tk.StringVar(value="config.json")
        self.logo_path = tk.StringVar(value="")
        self.output_format = tk.StringVar(value="JPEG")
        self.status = tk.StringVar(value="请选择一张图片开始处理。")

        self.source_image: Image.Image | None = None
        self.result_image: Image.Image | None = None
        self.source_path: Path | None = None
        self._left_preview = None
        self._right_preview = None

        self._build_ui()

    def _build_ui(self) -> None:
        top = ttk.Frame(self.root, padding=10)
        top.pack(fill=tk.X)

        ttk.Label(top, text="配置文件").grid(row=0, column=0, sticky=tk.W)
        ttk.Entry(top, textvariable=self.config_path, width=40).grid(row=0, column=1, padx=8)
        ttk.Button(top, text="选择图片", command=self.pick_source).grid(row=0, column=2, padx=4)
        ttk.Button(top, text="保存图片", command=self.save_output).grid(row=0, column=3, padx=4)

        controls = ttk.Frame(self.root, padding=(10, 0, 10, 8))
        controls.pack(fill=tk.X)
        ttk.Button(controls, text="选择 Icon", command=self.pick_logo).pack(side=tk.LEFT, padx=(0, 6))
        ttk.Button(controls, text="清除 Icon", command=self.clear_logo).pack(side=tk.LEFT, padx=(0, 12))
        ttk.Label(controls, text="当前 Icon:").pack(side=tk.LEFT)
        ttk.Label(controls, textvariable=self.logo_path, width=42).pack(side=tk.LEFT, padx=(4, 12))
        ttk.Label(controls, text="输出格式").pack(side=tk.LEFT, padx=(0, 4))
        ttk.Combobox(
            controls,
            textvariable=self.output_format,
            values=["PNG", "JPEG"],
            state="readonly",
            width=8,
        ).pack(side=tk.LEFT)
        ttk.Button(controls, text="生成预览", command=self.generate).pack(side=tk.RIGHT)

        views = ttk.Frame(self.root, padding=(10, 0, 10, 10))
        views.pack(fill=tk.BOTH, expand=True)
        views.columnconfigure(0, weight=1)
        views.columnconfigure(1, weight=1)
        views.rowconfigure(1, weight=1)

        ttk.Label(views, text="Input Image（左侧原图）", anchor=tk.CENTER).grid(row=0, column=0, sticky="ew")
        ttk.Label(views, text="Output Preview（右侧输出）", anchor=tk.CENTER).grid(row=0, column=1, sticky="ew")

        self.left_panel = ttk.Label(views, background="#f4f4f4", anchor=tk.CENTER)
        self.right_panel = ttk.Label(views, background="#f4f4f4", anchor=tk.CENTER)
        self.left_panel.grid(row=1, column=0, sticky="nsew", padx=(0, 8), pady=8)
        self.right_panel.grid(row=1, column=1, sticky="nsew", padx=(8, 0), pady=8)
        self.left_panel.bind("<Configure>", lambda _: self._refresh_previews())
        self.right_panel.bind("<Configure>", lambda _: self._refresh_previews())

        ttk.Label(self.root, textvariable=self.status, padding=(10, 0, 10, 10)).pack(fill=tk.X)

    def pick_source(self) -> None:
        path = filedialog.askopenfilename(
            title="选择原图",
            filetypes=[("Images", "*.jpg *.jpeg *.png")],
        )
        if not path:
            return

        try:
            self.source_path = Path(path)
            self.source_image = ImageOps.exif_transpose(Image.open(path)).convert("RGB")
        except Exception:  # noqa: BLE001
            messagebox.showerror("错误", "图片格式不支持或文件损坏")
            return
        self.result_image = None
        self._render_preview(self.left_panel, self.source_image, side="left")
        self.right_panel.configure(image="")
        self.status.set(f"已加载原图：{self.source_path.name}")

    def pick_logo(self) -> None:
        path = filedialog.askopenfilename(title="选择 Icon", filetypes=[("PNG", "*.png")])
        if path:
            try:
                with Image.open(path) as img:
                    img.verify()
            except Exception:  # noqa: BLE001
                messagebox.showerror("错误", "Icon 文件无效")
                return
            self.logo_path.set(path)
            self.status.set("已选择 Icon。")

    def clear_logo(self) -> None:
        self.logo_path.set("")
        self.status.set("已清除 Icon，生成时将使用默认 logo 逻辑。")

    def generate(self) -> None:
        if self.source_image is None:
            messagebox.showwarning("提示", "请先选择图片")
            return

        try:
            cfg = load_config(Path(self.config_path.get().strip()))
            logo_override = self.logo_path.get().strip() or None
            self.result_image = render_polaroid(self.source_image, cfg, selected_logo_path=logo_override)
            self._render_preview(self.right_panel, self.result_image, side="right")
            self.status.set("预览已生成，可点击“保存图片”。")
        except Exception as exc:  # noqa: BLE001
            messagebox.showerror("错误", f"处理失败：{exc}")

    def save_output(self) -> None:
        if self.result_image is None:
            messagebox.showwarning("提示", "请先生成预览")
            return

        is_png = self.output_format.get().upper() == "PNG"
        ext = ".png" if is_png else ".jpg"
        default_name = f"output_fmt{ext}" if self.source_path is None else f"{self.source_path.stem}_fmt{ext}"
        save_path = filedialog.asksaveasfilename(
            title="保存图片",
            defaultextension=ext,
            initialfile=default_name,
            filetypes=[("PNG", "*.png"), ("JPEG", "*.jpg *.jpeg")],
        )
        if not save_path:
            return

        try:
            if is_png:
                self.result_image.save(save_path, format="PNG", optimize=True)
            else:
                self.result_image.save(save_path, format="JPEG", quality=92, optimize=True, progressive=True)
            self.status.set(f"已保存：{save_path}")
        except Exception as exc:  # noqa: BLE001
            messagebox.showerror("错误", f"保存失败：{exc}")

    def _render_preview(self, panel: ttk.Label, img: Image.Image, side: str) -> None:
        preview = img.copy()
        panel.update_idletasks()
        pw = max(240, panel.winfo_width() - 16)
        ph = max(240, panel.winfo_height() - 16)
        preview.thumbnail((pw, ph), Image.Resampling.LANCZOS)
        tk_img = ImageTk.PhotoImage(preview)
        panel.configure(image=tk_img)
        if side == "left":
            self._left_preview = tk_img
        else:
            self._right_preview = tk_img

    def _refresh_previews(self) -> None:
        if self.source_image is not None:
            self._render_preview(self.left_panel, self.source_image, side="left")
        if self.result_image is not None:
            self._render_preview(self.right_panel, self.result_image, side="right")


def main() -> None:
    root = tk.Tk()
    PolaroidGUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()
