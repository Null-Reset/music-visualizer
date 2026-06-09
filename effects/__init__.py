"""共用工具函数 — HSV 转 RGB、颜色插值等"""


def hsv_to_rgb(h: float, s: float, v: float):
    """HSV → RGB (0~255)"""
    h = h % 360
    c = v * s
    x = c * (1 - abs((h / 60) % 2 - 1))
    m = v - c
    if h < 60:
        r, g, b = c, x, 0
    elif h < 120:
        r, g, b = x, c, 0
    elif h < 180:
        r, g, b = 0, c, x
    elif h < 240:
        r, g, b = 0, x, c
    elif h < 300:
        r, g, b = x, 0, c
    else:
        r, g, b = c, x, 0
    return (min(255, int((r + m) * 255)), min(255, int((g + m) * 255)), min(255, int((b + m) * 255)))


def lerp_color(c1: tuple, c2: tuple, t: float):
    """线性插值两个 RGB 颜色"""
    t = max(0.0, min(1.0, t))
    return (
        int(c1[0] + (c2[0] - c1[0]) * t),
        int(c1[1] + (c2[1] - c1[1]) * t),
        int(c1[2] + (c2[2] - c1[2]) * t),
    )


def smoothstep(t: float) -> float:
    """平滑阶梯函数"""
    t = max(0.0, min(1.0, t))
    return t * t * (3 - 2 * t)
