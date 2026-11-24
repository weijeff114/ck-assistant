@echo off
chcp 65001 >nul
title Cf 助手 v3.1 - 首次运行配置
color 0B
cd /d "%~dp0"

echo ====================================
echo   Cf 助手 v3.1 - 首次运行环境检查
echo ====================================
echo.

echo [1/3] 正在检查 Python 环境...
python --version >nul 2>nul
if %errorlevel% neq 0 (
    echo.
    echo [错误] 未检测到 Python！
    echo 请先前往 https://www.python.org/downloads/ 下载并安装。
    echo 安装时务必勾选 "Add Python to PATH" ！
    echo.
    pause
    exit /b
)
echo Python 环境正常。
echo.

echo [2/3] 正在安装依赖（首次运行可能需要1-2分钟，请耐心等待）...
python -m pip install openai pyperclip keyboard PyQt5 Pillow fastapi uvicorn -i https://pypi.tuna.tsinghua.edu.cn/simple
if %errorlevel% neq 0 (
    echo.
    echo [警告] 依赖安装过程中出现错误，请检查网络连接！
    echo.
    pause
)
echo.
echo [3/3] 正在启动 Cf 助手 v3.1...
echo 如果弹出悬浮窗，说明配置成功！
echo 注意：关闭此黑框或按 Ctrl+C，程序就会退出。
echo.

python main.py

echo.
echo Cf 助手已退出。
echo 如果本次运行正常，以后请双击 2-日常启动（静默版）.bat 启动！
pause