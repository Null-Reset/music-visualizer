"""设置面板 — tkinter GUI"""
import tkinter as tk
from tkinter import ttk, colorchooser
import config


class SettingsPanel:
    """设置面板窗口"""

    def __init__(self, on_apply=None):
        self.on_apply = on_apply  # 回调：应用新配置
        self.cfg = config.load()
        self.win = None

    def show(self):
        if self.win and self.win.winfo_exists():
            self.win.lift()
            return

        self.win = tk.Tk()
        self.win.title("🎵 Music Visualizer 设置")
        self.win.geometry("420x680")
        self.win.resizable(False, False)
        self.win.attributes("-topmost", True)

        # 重新加载配置
        self.cfg = config.load()
        self._vars = {}

        self._build_ui()
        self.win.mainloop()

    def _build_ui(self):
        notebook = ttk.Notebook(self.win)
        notebook.pack(fill="both", expand=True, padx=8, pady=8)

        # ── 频谱条 ──
        tab1 = ttk.Frame(notebook)
        notebook.add(tab1, text="  频谱条  ")
        self._build_spectrum_tab(tab1)

        # ── 光带 ──
        tab2 = ttk.Frame(notebook)
        notebook.add(tab2, text="  光带  ")
        self._build_glow_tab(tab2)

        # ── 音频 ──
        tab3 = ttk.Frame(notebook)
        notebook.add(tab3, text="  音频  ")
        self._build_audio_tab(tab3)

        # ── 全局 ──
        tab4 = ttk.Frame(notebook)
        notebook.add(tab4, text="  全局  ")
        self._build_global_tab(tab4)

        # 底部按钮
        btn_frame = ttk.Frame(self.win)
        btn_frame.pack(fill="x", padx=8, pady=(0, 8))
        ttk.Button(btn_frame, text="应用", command=self._apply).pack(side="right", padx=4)
        ttk.Button(btn_frame, text="重置默认", command=self._reset).pack(side="right", padx=4)
        ttk.Button(btn_frame, text="关闭", command=self.win.destroy).pack(side="right", padx=4)

    def _build_spectrum_tab(self, parent):
        frame = ttk.LabelFrame(parent, text="频谱条样式", padding=10)
        frame.pack(fill="x", padx=8, pady=8)

        # 条数
        self._add_slider(frame, "频谱条数", "num_bars", 20, 200, 1)

        # 颜色模式
        ttk.Label(frame, text="颜色模式:").pack(anchor="w")
        var_cm = tk.StringVar(value=self.cfg["bar_color_mode"])
        self._vars["bar_color_mode"] = var_cm
        for val, label in [("rainbow", "彩虹渐变"), ("gradient", "双色渐变"), ("fixed", "固定色")]:
            ttk.Radiobutton(frame, text=label, variable=var_cm, value=val).pack(anchor="w", padx=20)

        # 亮度
        self._add_slider(frame, "亮度", "bar_brightness", 0.1, 2.0, 0.1)

        # 间隙
        self._add_slider(frame, "条间距比", "bar_gap_ratio", 0.0, 0.4, 0.01)

        # 渐变色选择
        grad_frame = ttk.LabelFrame(parent, text="渐变色", padding=10)
        grad_frame.pack(fill="x", padx=8, pady=8)
        self._color_btn(grad_frame, "顶部色", "bar_color_top")
        self._color_btn(grad_frame, "底部色", "bar_color_bot")
        self._color_btn(grad_frame, "固定色", "bar_color_fixed")

    def _build_glow_tab(self, parent):
        frame = ttk.LabelFrame(parent, text="边缘光带", padding=10)
        frame.pack(fill="x", padx=8, pady=8)

        # 启用
        var_en = tk.BooleanVar(value=self.cfg["glow_enabled"])
        self._vars["glow_enabled"] = var_en
        ttk.Checkbutton(frame, text="启用光带", variable=var_en).pack(anchor="w")

        # 深度
        self._add_slider(frame, "光带深度比", "glow_depth_ratio", 0.01, 0.15, 0.005)

        # 强度
        self._add_slider(frame, "光带强度", "glow_intensity", 0.1, 2.0, 0.1)

        # 颜色模式
        ttk.Label(frame, text="颜色模式:").pack(anchor="w", pady=(8, 0))
        var_gcm = tk.StringVar(value=self.cfg["glow_color_mode"])
        self._vars["glow_color_mode"] = var_gcm
        ttk.Radiobutton(frame, text="跟随主频", variable=var_gcm, value="freq").pack(anchor="w", padx=20)
        ttk.Radiobutton(frame, text="固定色", variable=var_gcm, value="fixed").pack(anchor="w", padx=20)

        self._color_btn(frame, "固定色", "glow_color_fixed")

    def _build_audio_tab(self, parent):
        frame = ttk.LabelFrame(parent, text="音频设置", padding=10)
        frame.pack(fill="x", padx=8, pady=8)

        self._add_slider(frame, "灵敏度", "sensitivity", 0.1, 3.0, 0.1)
        self._add_slider(frame, "平滑度", "smoothing", 0.0, 0.9, 0.05)

        ttk.Label(frame, text="FFT 大小:").pack(anchor="w", pady=(8, 0))
        var_fft = tk.StringVar(value=str(self.cfg["fft_size"]))
        self._vars["fft_size"] = var_fft
        for val in ["1024", "2048", "4096"]:
            ttk.Radiobutton(frame, text=val, variable=var_fft, value=val).pack(anchor="w", padx=20)

    def _build_global_tab(self, parent):
        frame = ttk.LabelFrame(parent, text="全局设置", padding=10)
        frame.pack(fill="x", padx=8, pady=8)

        self._add_slider(frame, "全局透明度", "global_alpha", 0.1, 1.0, 0.05)
        self._add_slider(frame, "帧率", "fps", 15, 60, 5)

        var_as = tk.BooleanVar(value=self.cfg["autostart"])
        self._vars["autostart"] = var_as
        ttk.Checkbutton(frame, text="开机自启", variable=var_as).pack(anchor="w", pady=(8, 0))

    def _add_slider(self, parent, label, key, from_, to, resolution):
        ttk.Label(parent, text=f"{label}:").pack(anchor="w", pady=(8, 0))
        var = tk.DoubleVar(value=self.cfg[key])
        self._vars[key] = var
        scale = ttk.Scale(parent, from_=from_, to=to, variable=var, orient="horizontal")
        scale.pack(fill="x", padx=4)
        # 数值标签
        lbl = ttk.Label(parent, text=f"{self.cfg[key]:.2f}")
        lbl.pack(anchor="e", padx=4)
        var.trace_add("write", lambda *a, v=var, l=lbl: l.config(text=f"{v.get():.2f}"))

    def _color_btn(self, parent, label, key):
        frame = ttk.Frame(parent)
        frame.pack(fill="x", pady=2)
        ttk.Label(frame, text=f"{label}:").pack(side="left")

        color = self.cfg[key]
        color_hex = f"#{color[0]:02x}{color[1]:02x}{color[2]:02x}"

        preview = tk.Canvas(frame, width=24, height=24, bg=color_hex, relief="raised", bd=1)
        preview.pack(side="left", padx=8)

        var = tk.StringVar(value=color_hex)
        self._vars[key] = var

        def pick_color(p=preview, k=key, v=var):
            c = colorchooser.askcolor(initialcolor=v.get())
            if c[1]:
                v.set(c[1])
                p.config(bg=c[1])

        ttk.Button(frame, text="选择", command=pick_color).pack(side="left")

    def _apply(self):
        """收集所有变量，更新配置"""
        cfg = dict(self.cfg)
        for key, var in self._vars.items():
            if isinstance(var, tk.BooleanVar):
                cfg[key] = var.get()
            elif isinstance(var, tk.StringVar):
                val = var.get()
                if key in ("bar_color_mode", "glow_color_mode"):
                    cfg[key] = val
                elif key == "fft_size":
                    cfg[key] = int(val)
                elif key.startswith("bar_color") or key.startswith("glow_color"):
                    # hex → RGB list
                    hex_val = val.lstrip("#")
                    cfg[key] = [int(hex_val[i:i+2], 16) for i in (0, 2, 4)]
            elif isinstance(var, tk.DoubleVar):
                cfg[key] = var.get()

        config.save(cfg)
        self.cfg = cfg
        if self.on_apply:
            self.on_apply(cfg)

    def _reset(self):
        cfg = config.reset()
        self.cfg = cfg
        if self.on_apply:
            self.on_apply(cfg)
        # 刷新 UI
        self.win.destroy()
        self.show()
