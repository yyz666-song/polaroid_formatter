# Polaroid Formatter

一个基于 **Python 3 + Pillow** 的批处理工具，用于把宝丽来扫描照片统一成固定版式输出。

## 功能特性

- 固定画布尺寸输出（默认 `2160x2700`，可配置）。
- 前景图按 **contain** 缩放（不裁切）并居中。
- 前景相纸支持黄金分割默认比例：`paper_scale_mode="golden"` 时，前景尺寸约为画布的 `1/φ ≈ 0.618`。
- 可用 `paper_scale_override` 手动覆盖比例（如 `0.68`）实现“适当放大”。
- 背景层**不做高斯模糊**，使用同图“非对称安全裁切 + cover + extra scale”生成纯画面背景，重点避免底部白边露出。
- 默认背景安全裁切：`l=0.10, r=0.10, t=0.10, b=0.22`（底部裁更多）。
- 保留可配置 `UnsharpMask` 锐化，默认仅锐化前景（`sharpen_target="foreground"`）。
- 自动处理 EXIF 方向，输入来自 `inbox/`，输出到 `out/`，可选把原图移动到 `done/`。

---

## 目录结构

```text
polaroid_formatter/
├─ inbox/            # 输入图片
├─ out/              # 输出图片
├─ done/             # 已处理原图
├─ polaroid.py       # 主程序
├─ config.json       # 默认配置
├─ requirements.txt  # 依赖（Pillow）
└─ README.md
```

---

## 安装

### Windows（PowerShell）

```powershell
cd path\to\polaroid_formatter
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

### macOS / Linux（Terminal）

```bash
cd /path/to/polaroid_formatter
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

---

## 最小示例

1. 把待处理图片放入 `inbox/`
2. 运行：

```bash
python polaroid.py
```

Windows 也可直接：

```powershell
py .\polaroid.py
```

无图片时会打印：

```text
No images found in inbox/
```

---

## 使用方式

```bash
python polaroid.py [--config config.json] [--dry-run] [--once]
```

- `--config`：指定配置文件路径
- `--dry-run`：仅预览文件，不写出/移动
- `--once`：单次处理后退出

---

## 配置说明（config.json）

```json
{
  "inbox_dir": "inbox",
  "out_dir": "out",
  "done_dir": "done",
  "output_suffix": "_fmt",
  "output_extension": "jpg",
  "canvas": {
    "width": 2160,
    "height": 2700
  },
  "foreground": {
    "paper_scale_mode": "golden",
    "paper_scale_override": null
  },
  "background": {
    "bg_safe_crop": {
      "l": 0.10,
      "r": 0.10,
      "t": 0.10,
      "b": 0.22
    },
    "bg_extra_scale": 1.35,
    "brightness": 0.82,
    "saturation": 0.75
  },
  "sharpen_enabled": true,
  "sharpen_target": "foreground",
  "sharpen_radius": 1.6,
  "sharpen_percent": 150,
  "sharpen_threshold": 3,
  "jpeg_quality": 92,
  "move_processed_to_done": true,
  "supported_extensions": [".jpg", ".jpeg", ".png", ".webp"]
}
```

### 重点参数

- `foreground.paper_scale_mode`
  - `golden`：自动按黄金比例（约 0.618）缩放前景
  - `fit`：使用兼容默认值（约 0.78）
- `foreground.paper_scale_override`
  - 手动覆盖比例，优先级高于 `paper_scale_mode`，例如 `0.68`
- `background.bg_safe_crop.{l,r,t,b}`
  - 非对称安全裁切比例（0~1）
  - 默认底部 `b` 更大，专门压制底部相纸白边
- `background.bg_extra_scale`
  - 背景额外放大系数（>=1），越大越不容易露白边
- `sharpen_*`
  - UnsharpMask 参数；默认只对前景锐化

---

## 调参建议（解决底部白边最关键）

如果还看到背景底部白边/相框：

1. 先增大 `background.bg_safe_crop.b`（例如 `0.22 -> 0.26`）
2. 再增大 `background.bg_extra_scale`（例如 `1.35 -> 1.45`）
3. 必要时微调 `paper_scale_override`（如 `0.64~0.70`）让前景更合适

---

## 注意事项

- 仅依赖 **Pillow**，不使用 OpenCV。
- 背景流程为：**non-symmetric safe crop → cover + extra scale → 色彩/亮度调整**。
- 程序保留安全兜底，避免安全裁切过大导致可用区域过小。
- 输出统一为 JPEG（RGB/sRGB 语义）。

