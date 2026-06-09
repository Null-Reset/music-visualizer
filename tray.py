"""pystray 托盘图标"""
import pystray
from PIL import Image, ImageDraw


def create_tray_icon(on_settings=None, on_toggle=None, on_quit=None):
    """创建托盘图标和菜单"""

    # 生成一个简单的音符图标
    def make_icon_image():
        img = Image.new("RGBA", (64, 64), (0, 0, 0, 0))
        d = ImageDraw.Draw(img)
        # 背景圆
        d.ellipse([4, 4, 60, 60], fill=(0, 120, 255, 200))
        # 音符 ♪
        d.text((18, 12), "♪", fill=(255, 255, 255, 255))
        return img

    img = make_icon_image()

    def _settings(icon, item):
        if on_settings:
            on_settings()

    def _quit(icon, item):
        icon.stop()
        if on_quit:
            on_quit()

    icon = pystray.Icon(
        "MusicVisualizer",
        img,
        "Music Visualizer",
        menu=pystray.Menu(
            pystray.MenuItem("⚙️ 设置", _settings),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("❌ 退出", _quit),
        ),
    )
    return icon
