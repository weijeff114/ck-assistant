@echo off
chcp 65001 >nul
title Cf 助手 - 首次运行配置
color 0B
cd /d "%~dp0"

echo ====================================
echo   Cf 助手 - 首次运行环境检查与配置
echo ====================================
echo.
echo [1/3] 正在检查 Python 环境...
python --version >nul 2>nul
if %errorlevel% neq 0 (
    echo [错误] 未检测到 Python！
    echo 请先前往 https://www.python.org/downloads/ 下载并安装。
    echo 安装时务必勾选 "Add Python to PATH" ！
    echo.
    pause
    exit /b
)

echo [2/3] 正在安装依赖（如果已安装会自动跳过）...
python -m pip install openai pyperclip keyboard PyQt5 -i https://pypi.tuna.tsinghua.edu.cn/simple

echo.
echo [3/3] 正在启动 Cf 助手（此时会显示所有日志，方便排查错误）...
echo 请观察下方是否有红色报错。如果没有，程序会正常运行。
echo 注意：关闭此黑框，程序也会退出。
echo.

python main.py

echo.
echo Cf 助手已退出。
echo 如果本次运行正常，以后请双击 "2-日常启动（静默版）.bat" 启动！
pause