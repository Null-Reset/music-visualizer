"""边缘光带效果 — numpy 全向量化，无逐行 for 循环"""
import math
import numpy as np
from . import hsv_to_rgb, smoothstep


def render(renderer, energy, peak, dominant_freq, cfg):
    """渲染边缘光带：从任务栏向上延伸，底部最亮，向上淡出"""
    if not cfg.get("glow_enabled", True):
        return

    w = renderer.w
    h = renderer.h
    pixels = renderer.pixels  # (h, w, 4)
    alpha_mul = cfg.get("global_alpha", 0.8)
    glow_intensity = cfg.get("glow_intensity", 1.0)

    # 光带深度
    base_depth = max(10, int(h * cfg.get("glow_depth_ratio", 0.15)))
    depth_boost = 1.0 + peak * 0.5
    ld = min(h, int(base_depth * depth_boost))

    if ld < 2:
        return

    music_intensity = 0.3 + energy * 0.7

    # 颜色
    color_mode = cfg.get("glow_color_mode", "freq")
    if color_mode == "freq" and dominant_freq > 0:
        freq_norm = min(1.0, max(0.0, (math.log10(max(dominant_freq, 20)) - 1.3) / 3.0))
        hue = 240 - freq_norm * 240
        r, g, b = hsv_to_rgb(hue, 0.85, 1.0)
    else:
        c = cfg.get("glow_color_fixed", [0, 180, 255])
        r, g, b = c[0], c[1], c[2]

    center_x = w / 2.0

    # ── y 方向 ──
    # glow_region 布局：index 0 = 窗口上方（远离任务栏），index ld-1 = 窗口底部（任务栏处）
    # y_ratio: 0 = 上方(远离任务栏), 1 = 底部(任务栏处)
    y_arr = np.arange(ld, dtype=np.float32)
    y_ratio = y_arr / (ld - 1)  # 0=上方, 1=底部(任务栏)

    # 亮度：底部(任务栏)最亮，向上衰减
    v_base = np.power(y_ratio, 1.6)

    # 淡出：靠近任务栏(底部) 10% 全亮，向上 smoothstep 淡出
    fade = np.where(y_ratio > 0.9, 1.0,
                    _smoothstep_vec(y_ratio / 0.9))
    v_base = v_base * fade

    # ── x 方向 ──
    x_arr = np.arange(w, dtype=np.float32)
    dx = np.abs(x_arr - center_x) / center_x
    h_fade = np.maximum(0.0, 1.0 - dx ** 2.5)

    # 中心提亮（屏幕中央更亮）
    dx_norm = np.clip(1.0 - dx / 0.25, 0.0, 1.0)
    center_boost = np.where(dx < 0.25,
                            dx_norm ** 1.5 * 0.3 * music_intensity * glow_intensity,
                            0.0)

    # 底部提亮（靠近任务栏更亮）
    yr_norm = np.clip(y_ratio / 0.15, 0.0, 1.0)
    bottom_boost = np.where(y_ratio > 0.85,
                            yr_norm ** 1.2 * 0.4 * music_intensity * glow_intensity,
                            0.0)

    # 组合 alpha — 2D 广播，一步到位
    alpha_2d = (v_base[:, None] * h_fade[None, :] * music_intensity * glow_intensity
                + center_boost[None, :] * v_base[:, None]
                + bottom_boost[:, None] * h_fade[None, :])
    alpha_2d = np.clip(alpha_2d, 0.0, 1.0)
    alpha_uint8 = (alpha_2d * 255 * alpha_mul).astype(np.uint8)

    # ═══ 向量化像素写入：切片 + 广播，无 Python 循环 ═══
    y_start = h - ld
    glow_region = pixels[y_start:h, :, :]  # (ld, w, 4)

    # 颜色通道：全部填同色
    glow_region[:, :, 0] = b  # B
    glow_region[:, :, 1] = g  # G
    glow_region[:, :, 2] = r  # R

    # Alpha：取较大值（叠加模式）
    existing_alpha = glow_region[:, :, 3]
    glow_region[:, :, 3] = np.maximum(existing_alpha, alpha_uint8)


def _smoothstep_vec(t):
    t = np.clip(t, 0.0, 1.0)
    return t * t * (3.0 - 2.0 * t)
