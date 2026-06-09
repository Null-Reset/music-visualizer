"""配置持久化 — JSON 文件读写"""
import json, os

CONFIG_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.json")

DEFAULTS = {
    # 频谱条
    "num_bars": 80,
    "bar_min_height": 4,
    "bar_color_mode": "rainbow",   # rainbow | gradient | fixed
    "bar_color_fixed": [0, 200, 255],
    "bar_color_top": [255, 0, 120],
    "bar_color_bot": [0, 200, 255],
    "bar_gap_ratio": 0.15,
    "bar_brightness": 1.0,

    # 边缘光带
    "glow_enabled": True,
    "glow_depth_ratio": 0.04,
    "glow_color_mode": "freq",     # freq | fixed
    "glow_color_fixed": [0, 180, 255],
    "glow_intensity": 1.0,

    # 音频
    "sensitivity": 1.0,            # 灵敏度倍数 0.1~3.0
    "smoothing": 0.3,              # 平滑系数 0.0~1.0（越大越平滑）
    "fft_size": 2048,

    # 全局
    "global_alpha": 0.80,
    "fps": 30,
    "autostart": True,
}


def load() -> dict:
    cfg = dict(DEFAULTS)
    if os.path.exists(CONFIG_PATH):
        try:
            with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                saved = json.load(f)
            cfg.update(saved)
        except Exception:
            pass
    # 确保整数字段是 int
    for k in ("num_bars", "bar_min_height", "fft_size", "fps"):
        if k in cfg:
            cfg[k] = int(cfg[k])
    return cfg


def save(cfg: dict):
    try:
        with open(CONFIG_PATH, "w", encoding="utf-8") as f:
            json.dump(cfg, f, indent=2, ensure_ascii=False)
    except Exception:
        pass


def reset():
    save(DEFAULTS)
    return dict(DEFAULTS)
