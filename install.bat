@echo off
chcp 65001 >nul
echo ========================================
echo   音乐可视化器 - 安装依赖
echo ========================================
echo.
echo 正在安装...
pip install pyaudiowpatch numpy pystray Pillow
echo.
echo ✅ 安装完成！
echo 双击 start.bat 启动
pause
