# 🎵 Music Visualizer

一款基于 Python 的实时桌面音频可视化工具，为你的电脑屏幕注入音乐的律动。

## ✨ 核心特性

- 🎨 **彩虹频谱条**：屏幕底部 80 根动态条，高度随音乐跳动，色彩渐变。
- 🌈 **边缘光带**：从底部向上延展的光带，颜色随频率实时变化。
- 🖥️ **系统托盘**：静默运行，右键菜单可快速设置或退出。
- ⚙️ **自定义设置**：支持调整条数、颜色、灵敏度等参数。
- 🔄 **开机自启**：默认开启，享受随系统启动的视觉体验。

## 📦 环境要求

- **Operating System**: Windows 10 / 11
- **Python version**: 3.11 or higher (make sure to check **Add to PATH** during installation)
- **音频设备**：声卡（支持环回捕获，无需外设）

## 🚀 快速开始

1. **Install Python**: Go to [python.org](https://www.python.org/downloads/) and download and install Python 3.11.
2. **一键安装**：双击项目根目录下的 `install.bat` 自动安装依赖。
3. **启动应用**：双击 `start.bat` 启动可视化器。

> **提示**：启动后，应用会自动最小化到系统托盘，屏幕底部会开始显示动态频谱。

## ⚙️ 设置说明

- 右键点击系统托盘图标，选择 **“设置”** 可调参数。
- 右键点击系统托盘图标，选择 **“退出”** 可关闭应用。

## 🛠️ 开发说明

- 项目依赖主要包含：`pyaudio`、`numpy`、`tkinter` 等。
- 如需手动安装依赖，可运行：`pip install -r requirements.txt`

## 📄 许可证

MIT License
