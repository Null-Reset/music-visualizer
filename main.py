"""
Music Visualizer — 屏幕底部频谱条 + 边缘光带
Win32 透明窗口 + WASAPI loopback + FFT 频率分析 + pystray 托盘
"""
import sys, os, time, threading, subprocess
import ctypes
from ctypes import wintypes

# 确保能找到同级模块
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import config
from audio import AudioCapture
from renderer import Win32Renderer
from effects import spectrum, edge_glow
from tray import create_tray_icon

user32 = ctypes.windll.user32


def main():
    cfg = config.load()
    screen_w = user32.GetSystemMetrics(0)
    screen_h = user32.GetSystemMetrics(1)

    window_h = 100

    # 创建渲染器
    renderer = Win32Renderer(screen_w, window_h)

    # 创建音频捕获
    audio = AudioCapture(
        num_bands=cfg["num_bars"],
        fft_size=cfg["fft_size"],
        sensitivity=cfg["sensitivity"],
        smoothing=cfg["smoothing"],
    )
    audio.start()
    print("[Main] 音频捕获已启动")

    # 状态
    state = {"running": True, "cfg": cfg}
    _pending_cfg = [None]  # 用列表避免闭包问题

    def on_apply(new_cfg):
        """设置面板回调 — 只存配置，不操作渲染器"""
        _pending_cfg[0] = new_cfg

    def open_settings():
        """用 subprocess 打开设置面板，避免 tkinter 和主循环抢 GIL"""
        try:
            subprocess.Popen(
                [sys.executable, os.path.join(os.path.dirname(__file__), "settings_standalone.py")],
                cwd=os.path.dirname(__file__),
            )
        except Exception as e:
            print(f"[Settings] 启动失败: {e}")

    def on_quit():
        state["running"] = False
        audio.stop()
        renderer.close()
        # 优雅退出
        os._exit(0)

    # 托盘图标（独立线程）
    tray_icon = create_tray_icon(
        on_settings=open_settings,
        on_quit=on_quit,
    )
    threading.Thread(target=tray_icon.run, daemon=True).start()

    # 开机自启
    if cfg.get("autostart", True):
        _setup_autostart()

    # ═══ 主循环 ═══
    frame_interval = 1.0 / cfg["fps"]
    last_frame = time.time()

    try:
        while state["running"]:
            now = time.time()
            if now - last_frame >= frame_interval:
                last_frame = now

                # 检测配置变更（来自设置面板）
                if _pending_cfg[0] is not None:
                    new_cfg = _pending_cfg[0]
                    _pending_cfg[0] = None
                    state["cfg"] = new_cfg
                    audio.update_params(
                        num_bands=new_cfg["num_bars"],
                        sensitivity=new_cfg["sensitivity"],
                        smoothing=new_cfg["smoothing"],
                        fft_size=new_cfg["fft_size"],
                    )

                # 获取音频数据
                fft_bands, energy, peak, dominant_freq = audio.get_data()

                cfg_current = state["cfg"]

                # 清空
                renderer.clear()

                # 渲染边缘光带（底层）
                edge_glow.render(renderer, energy, peak, dominant_freq, cfg_current)

                # 渲染频谱条（上层）
                spectrum.render(renderer, fft_bands, cfg_current)

                # 提交到屏幕
                renderer.present()

            # 让出 CPU 时间片，避免占满 GIL
            time.sleep(0.001)

    except KeyboardInterrupt:
        pass
    finally:
        audio.stop()
        renderer.close()
        tray_icon.stop()


def _setup_autostart():
    """注册开机自启"""
    import winreg
    try:
        key = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            r"Software\Microsoft\Windows\CurrentVersion\Run",
            0, winreg.KEY_SET_VALUE,
        )
        exe = os.path.abspath(sys.argv[0])
        winreg.SetValueEx(key, "MusicVisualizer", 0, winreg.REG_SZ,
                          f'"{sys.executable}" "{exe}"')
        winreg.CloseKey(key)
    except Exception as e:
        print(f"[AutoStart] 注册失败: {e}")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        import traceback
        print(f"[Fatal] {e}")
        traceback.print_exc()
