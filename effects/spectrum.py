"""频谱条效果 — numpy 批量渲染"""
import numpy as np
from . import hsv_to_rgb, lerp_color


def render(renderer, fft_bands, cfg):
    """
    渲染频谱条到 renderer.pixels（numpy 数组）

    Args:
        renderer: Win32Renderer 实例
        fft_bands: numpy array, 0~1 归一化频带能量
        cfg: 配置字典
    """
    w = renderer.w
    h = renderer.h
    pixels = renderer.pixels  # (h, w, 4) numpy array
    num_bars = len(fft_bands)

    bar_zone_h = h
    bar_zone_y = 0

    # 频谱条参数
    bar_w = w / num_bars
    gap = max(1, int(bar_w * cfg.get("bar_gap_ratio", 0.15)))
    ew = bar_w - gap
    brightness = cfg.get("bar_brightness", 1.0)
    color_mode = cfg.get("bar_color_mode", "rainbow")
    alpha_mul = cfg.get("global_alpha", 0.8)

    # 预计算颜色
    if color_mode == "gradient":
        c_top = tuple(cfg.get("bar_color_top", [255, 0, 120]))
        c_bot = tuple(cfg.get("bar_color_bot", [0, 200, 255]))
    elif color_mode == "fixed":
        c_fixed = tuple(cfg.get("bar_color_fixed", [0, 200, 255]))

    for i in range(num_bars):
        bv = float(fft_bands[i])
        if bv < 0.01:
            continue

        # 颜色
        if color_mode == "rainbow":
            # 全彩虹：蓝(240) → 青(180) → 绿(120) → 黄(60) → 红(0)
            hue = 240 - (i / max(1, num_bars - 1)) * 240
            v = min(1.0, brightness)  # 亮度不超过1.0
            r, g, b = hsv_to_rgb(hue, 1.0, v)
        elif color_mode == "gradient":
            t = i / max(1, num_bars - 1)
            r, g, b = lerp_color(c_bot, c_top, t)
        else:
            r, g, b = c_fixed[0], c_fixed[1], c_fixed[2]

        # clamp
        r, g, b = min(255, max(0, r)), min(255, max(0, g)), min(255, max(0, b))

        bh = int(bv * (h - 2))
        if bh < 1:
            continue

        xs = int(i * bar_w + gap / 2)
        xe = min(int(xs + ew), w)
        ys = h - bh

        # numpy 批量填充
        bar_region = pixels[ys:h, xs:xe]

        # 垂直渐变因子：底部亮，顶部淡
        bar_height = h - ys
        if bar_height > 0:
            v_fade = np.linspace(1.0, 0.6, bar_height).reshape(-1, 1)
            alpha = (v_fade * min(1.0, brightness) * 255).astype(np.uint8)
            alpha = np.clip(alpha, 0, 255)

            bar_region[:, :, 0] = min(255, b)
            bar_region[:, :, 1] = min(255, g)
            bar_region[:, :, 2] = min(255, r)
            bar_region[:, :, 3] = alpha

