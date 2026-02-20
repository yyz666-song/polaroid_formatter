# Polaroid Formatter

一个基于 **Python 3 + Pillow** 的批处理工具，用于把宝丽来扫描照片统一成固定版式输出。

## 功能特性

- 固定画布尺寸输出（默认 `2160x2700`，可配置）。
- 前景图使用 **contain** 缩放（不裁切），居中放置，默认占画布宽度 `78%`。
- 背景图使用同一原图，先执行**安全裁切**（默认四周各裁 14%）去掉相框/白边风险，再做 **cover** 填满画布，并支持额外放大系数（默认 `1.25`）确保不露边。
- 背景不再使用任何高斯模糊，保持纯画面质感。
- 支持 `Unsharp Mask` 锐化：默认开启、默认仅锐化前景（可切换为全图锐化）。
- 自动读取 `inbox/` 下的 `jpg/jpeg/png/webp`。
- 输出到 `out/`，文件名默认为 `原文件名 + _fmt.jpg`。
- 可选将处理后的原图移动到 `done/`（默认开启）。
- 自动处理 EXIF 方向，避免旋转错位。

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

## 最小示例（你要的流程）

1. 把待处理图片放进 `inbox/`。
2. 执行：

```bash
python polaroid.py
```

Windows 也可直接：

```powershell
py .\polaroid.py
```

程序会自动：
- 扫描 `inbox/`
- 生成版式图到 `out/`
- 将原图移动到 `done/`（默认开启）

---

## 使用方式

```bash
python polaroid.py [--config config.json] [--dry-run] [--once]
```

### 参数说明

- `--config`：指定配置文件路径（默认 `config.json`）
- `--dry-run`：仅预览将处理哪些文件，不实际写出或移动
- `--once`：单次处理后退出（当前脚本默认本就是单次批处理，该参数用于流程兼容）

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
    "width_ratio": 0.78
  },
  "background": {
    "bg_safe_crop_pct": 0.14,
    "bg_extra_scale": 1.25,
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

### 常用可调项

- `canvas.width / canvas.height`：目标画布大小
- `foreground.width_ratio`：前景占画布宽度比例
- `background.bg_safe_crop_pct`：背景安全裁切比例（按四周等比裁切）
- `background.bg_extra_scale`：背景额外放大系数（>=1，越大越不易露边）
- `background.brightness`：背景亮度（<1 更暗）
- `background.saturation`：背景饱和度（<1 更灰）
- `sharpen_enabled`：是否启用锐化
- `sharpen_target`：锐化目标，`foreground` 或 `all`
- `sharpen_radius / sharpen_percent / sharpen_threshold`：Unsharp Mask 参数
- `jpeg_quality`：JPEG 导出质量（1~100）
- `move_processed_to_done`：是否移动原图到 `done/`

---

## 注意事项

- 仅依赖 **Pillow**，不使用 OpenCV。
- 背景处理顺序是：**safe crop → cover（含 extra scale）→ 色彩/亮度调整**。
- 若安全裁切设置过大，程序会自动兜底，至少保留原图 60% 宽高，避免过度裁切。
- 输出统一为 JPEG（RGB/sRGB 语义）。
- 如果目标文件名重复会被覆盖，建议先备份。
- 若某张图处理失败，程序会打印错误并继续处理下一张。

