"""Logo selection settings (Python-side).

规则：
- 1 = 不使用 logo
- 2+ = 对应列表中的第 N 个文件（N = logo_id - 1）
"""

LOGO_DIR = "assets/logos"

# 1 = 无 logo, 2 = LOGO_LIST[0], 3 = LOGO_LIST[1], ...
LOGO_ID = 1

# 显式列表模式（推荐，顺序稳定）
LOGO_LIST = [
    "brand_a.png",
    "brand_b.png",
    "model_now.png",
]

# 自动扫描模式开关；False 时使用 LOGO_LIST，True 时扫描 LOGO_DIR 下所有 .png
AUTO_SCAN = False

# 默认参数
MARGIN_RATIO = 0.02
SCALE_RATIO = 0.055
OPACITY = 0.9
BOTTOM_BAND = {
    "top_ratio": 0.78,
    "bottom_ratio": 0.98,
    "y_bias": 0.72,
}
