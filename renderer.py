"""Win32 透明窗口渲染引擎 — numpy 加速版"""
import ctypes, time
import numpy as np
from ctypes import wintypes, Structure, sizeof, byref, c_void_p, c_int

user32 = ctypes.windll.user32
kernel32 = ctypes.windll.kernel32
gdi32 = ctypes.windll.gdi32

# Win32 常量
WS_POPUP = 0x80000000
WS_EX_LAYERED = 0x00080000
WS_EX_TRANSPARENT = 0x00000020
WS_EX_TOPMOST = 0x00000008
WS_EX_TOOLWINDOW = 0x00000080
WS_EX_NOACTIVATE = 0x08000000
GWL_EXSTYLE = -20
ULW_ALPHA = 0x00000002
AC_SRC_ALPHA = 0x01
BI_RGB = 0
DIB_RGB_COLORS = 0
SW_SHOWNA = 8
SWP_NOMOVE = 0x0002
SWP_NOZORDER = 0x0004


class BITMAPINFOHEADER(Structure):
    _fields_ = [
        ("biSize", wintypes.UINT), ("biWidth", wintypes.LONG),
        ("biHeight", wintypes.LONG), ("biPlanes", wintypes.WORD),
        ("biBitCount", wintypes.WORD), ("biCompression", wintypes.UINT),
        ("biSizeImage", wintypes.UINT), ("biXPelsPerMeter", wintypes.LONG),
        ("biYPelsPerMeter", wintypes.LONG), ("biClrUsed", wintypes.UINT),
        ("biClrImportant", wintypes.UINT),
    ]


class BITMAPINFO(Structure):
    _fields_ = [("bmiHeader", BITMAPINFOHEADER), ("bmiColors", wintypes.DWORD * 3)]


class BLENDFUNCTION(Structure):
    _fields_ = [
        ("BlendOp", ctypes.c_byte), ("BlendFlags", ctypes.c_byte),
        ("SourceConstantAlpha", ctypes.c_byte), ("AlphaFormat", ctypes.c_byte),
    ]


class POINT(Structure):
    _fields_ = [("x", wintypes.LONG), ("y", wintypes.LONG)]


class SIZE(Structure):
    _fields_ = [("cx", wintypes.LONG), ("cy", wintypes.LONG)]


WNDPROC = ctypes.WINFUNCTYPE(
    ctypes.c_long,
    ctypes.c_void_p,   # HWND
    ctypes.c_uint,     # UINT
    ctypes.c_size_t,   # WPARAM
    ctypes.c_ssize_t,  # LPARAM
)


class Win32Renderer:
    """Win32 透明分层窗口 + numpy 像素缓冲"""

    def __init__(self, width: int, height: int, class_name: str = "MusicVisualizer"):
        self.w = width
        self.h = height
        self._class_name = class_name
        self._closed = False
        self._work_bottom = self._get_work_area_bottom()

        # 注册窗口类
        self._wndproc = WNDPROC(self._wnd_proc)
        h_inst = kernel32.GetModuleHandleW(None)

        class WC(Structure):
            _fields_ = [
                ("cbSize", wintypes.UINT), ("style", wintypes.UINT),
                ("lpfnWndProc", c_void_p), ("cbClsExtra", c_int),
                ("cbWndExtra", c_int), ("hInstance", wintypes.HANDLE),
                ("hIcon", wintypes.HANDLE), ("hCursor", wintypes.HANDLE),
                ("hbrBackground", wintypes.HANDLE), ("lpszMenuName", wintypes.LPCWSTR),
                ("lpszClassName", wintypes.LPCWSTR), ("hIconSm", wintypes.HANDLE),
            ]

        wc = WC()
        wc.cbSize = sizeof(WC)
        wc.lpfnWndProc = ctypes.cast(self._wndproc, c_void_p)
        wc.hInstance = h_inst
        wc.lpszClassName = class_name
        wc.hCursor = user32.LoadCursorW(0, 32512)
        user32.RegisterClassExW(byref(wc))

        # 创建窗口（任务栏上方）
        ex = (WS_EX_LAYERED | WS_EX_TOPMOST | WS_EX_TOOLWINDOW |
              WS_EX_NOACTIVATE | WS_EX_TRANSPARENT)
        pos_y = self._work_bottom - height
        self.hwnd = user32.CreateWindowExW(
            ex, class_name, class_name, WS_POPUP,
            0, pos_y, width, height, None, None, h_inst, None,
        )

        user32.ShowWindow(self.hwnd, SW_SHOWNA)

        # DIB section
        self.hdc_screen = user32.GetDC(0)
        self.hdc_mem = gdi32.CreateCompatibleDC(self.hdc_screen)
        self.bmp = None
        self.pv_bits = None
        self._alloc_bitmap()

        # numpy 像素缓冲区 (h, w, 4) BGRA
        self.pixels = np.zeros((height, width, 4), dtype=np.uint8)

    def _alloc_bitmap(self):
        bmi = BITMAPINFO()
        bmi.bmiHeader.biSize = sizeof(BITMAPINFOHEADER)
        bmi.bmiHeader.biWidth = self.w
        bmi.bmiHeader.biHeight = -self.h  # 从上到下
        bmi.bmiHeader.biPlanes = 1
        bmi.bmiHeader.biBitCount = 32
        bmi.bmiHeader.biCompression = BI_RGB
        self.pv_bits = c_void_p()
        self.bmp = gdi32.CreateDIBSection(
            self.hdc_mem, byref(bmi), DIB_RGB_COLORS,
            byref(self.pv_bits), None, 0,
        )
        gdi32.SelectObject(self.hdc_mem, self.bmp)

    def _wnd_proc(self, hwnd, msg, wparam, lparam):
        if msg == 0x0010:  # WM_CLOSE
            return 0
        return user32.DefWindowProcW(
            ctypes.c_void_p(hwnd),
            ctypes.c_uint(msg),
            ctypes.c_size_t(wparam),
            ctypes.c_ssize_t(lparam),
        )

    def clear(self):
        """清空像素缓冲"""
        self.pixels.fill(0)

    def present(self):
        """将 numpy 缓冲提交到屏幕"""
        # numpy array 连续内存直接 memmove
        ctypes.memmove(self.pv_bits, self.pixels.ctypes.data, self.pixels.nbytes)
        pos_y = self._work_bottom - self.h
        pt = POINT(0, pos_y)
        sz = SIZE(self.w, self.h)
        pt_src = POINT(0, 0)
        blend = BLENDFUNCTION(0, 0, 255, AC_SRC_ALPHA)
        user32.UpdateLayeredWindow(
            self.hwnd, self.hdc_screen, byref(pt), byref(sz),
            self.hdc_mem, byref(pt_src), 0, byref(blend), ULW_ALPHA,
        )

    def resize(self, new_w: int, new_h: int):
        """调整窗口和缓冲区大小"""
        if new_w == self.w and new_h == self.h:
            return
        if self.bmp:
            gdi32.DeleteObject(self.bmp)
        self.w = new_w
        self.h = new_h
        self._alloc_bitmap()
        self.pixels = np.zeros((new_h, new_w, 4), dtype=np.uint8)
        pos_y = self._work_bottom - new_h
        user32.SetWindowPos(self.hwnd, 0, 0, pos_y, new_w, new_h,
                            SWP_NOZORDER)

    def close(self):
        if self._closed:
            return
        self._closed = True
        if self.bmp:
            gdi32.DeleteObject(self.bmp)
        gdi32.DeleteDC(self.hdc_mem)
        user32.ReleaseDC(0, self.hdc_screen)
        user32.DestroyWindow(self.hwnd)

    @staticmethod
    def _get_work_area_bottom():
        """获取工作区底部坐标（排除任务栏）"""
        class RECT(Structure):
            _fields_ = [("left", wintypes.LONG), ("top", wintypes.LONG),
                        ("right", wintypes.LONG), ("bottom", wintypes.LONG)]
        rc = RECT()
        user32.SystemParametersInfoW(0x0030, 0, byref(rc), 0)
        return rc.bottom

    def __del__(self):
        self.close()
