# Polaroid Formatter

一个基于 **Python 3 + Pillow** 的批处理工具，用于把宝丽来扫描照片统一成固定版式输出。
![87026a2ab20df417bc84f9526c7d3c91](https://github.com/user-attachments/assets/ac64a4f0-0a91-46e5-8c39-1debc303b1ea)
![87026a2ab20df417bc84f9526c7d3c91_fmt](https://github.com/user-attachments/assets/2368fdd7-7f11-4072-9175-cc167ccbc75f)

## 功能特性

- 固定画布尺寸输出（默认 `2160x2700`，可配置）。
- 前景图按 **contain** 缩放（不裁切）并居中。
- 前景相纸支持黄金分割默认比例：`paper_scale_mode="golden"` 时，前景尺寸约为画布的 `1/φ ≈ 0.618`。
- 可用 `paper_scale_override` 手动覆盖比例（如 `0.68`）实现“适当放大”。
- 背景层不做高斯模糊，使用同图“非对称安全裁切 + cover + extra scale”生成纯画面背景，重点避免底部白边露出。
- 默认背景安全裁切：`l=0.10, r=0.10, t=0.10, b=0.22`（底部裁更多）。
- 保留可配置 `UnsharpMask` 锐化，默认仅锐化前景（`sharpen_target="foreground"`）。
- 自动处理 EXIF 方向，输入来自 `inbox/`，输出到 `out/`，可选把原图移动到 `done/`。
- 支持在成片底部自动叠加 PNG logo（默认关闭，可通过 `logo_settings.py` 一键切换）。
- logo 选择支持显式列表或自动扫描模式，并且在文件名不完全一致时支持宽松匹配兜底。

---

## 目录结构

```text
polaroid_formatter/
├─ inbox/            # 输入图片
├─ out/              # 输出图片
├─ done/             # 已处理原图
├─ assets/
│  └─ logos/         # 可选 logo 素材（PNG）
├─ polaroid.py       # 主程序
├─ logo_settings.py  # Python 侧 logo 选择与参数
├─ logo_overlay.py   # logo 叠加与路径解析逻辑
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
  "supported_extensions": [".jpg", ".jpeg", ".png", ".webp"],
  "logo": {
    "enabled": true,
    "placement": "frame_bottom_center",
    "margin_ratio": 0.02,
    "scale_ratio": 0.055,
    "gap_ratio": 0.012,
    "opacity": 0.9,
    "library": {
      "brand_a": "assets/logos/brand_a.png",
      "brand_b": "assets/logos/brand_b.png",
      "now": "assets/logos/model_now.png"
    },
    "brand_key": "brand_a",
    "model_key": "now",
    "brand_path": null,
    "model_path": null,
    "bottom_band": {
      "top_ratio": 0.78,
      "bottom_ratio": 0.98,
      "y_bias": 0.72
    }
  }
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
- `logo.*`
  - 当前版本会校验 `logo` 配置结构，建议保持与示例一致，便于后续扩展

> 提示：logo 的实际开关与选择目前以 `logo_settings.py` 为准（`LOGO_ID=1` 表示不叠加，`2+` 对应 logo 列表中的第 N 个）。

---

## Logo 叠加（最新）

### 1) 通过 Python 配置快速切换

编辑 `logo_settings.py`：

```python
LOGO_DIR = "assets/logos"
LOGO_ID = 1  # 1=关闭, 2=第1个, 3=第2个...
LOGO_LIST = ["brand_a.png", "brand_b.png", "model_now.png"]
AUTO_SCAN = False
```

- `AUTO_SCAN=False`：按 `LOGO_LIST` 顺序选择（推荐，顺序稳定）。
- `AUTO_SCAN=True`：扫描 `assets/logos/*.png` 自动排序后选择。
- 若目标文件不存在，会尝试“宽松匹配”（如忽略下划线差异）。

### 2) 底部中线安全区域摆放

logo 默认采用底部中线区域放置（`frame_bottom_center` 语义）：

- `BOTTOM_BAND.top_ratio` / `bottom_ratio`：定义底部可放置带状区域。
- `BOTTOM_BAND.y_bias`：控制 logo 在带状区域内的垂直偏移。
- 同时受 `MARGIN_RATIO`、`SCALE_RATIO`、`OPACITY` 影响。

这套策略能让 logo 更稳定地落在“相纸白边区域”附近，减少压到主画面的概率。

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
