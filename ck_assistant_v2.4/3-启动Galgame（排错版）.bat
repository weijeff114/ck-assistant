@echo off
chcp 65001 >nul
title Cf Galgame v2.4 - 运行状态与排错
color 0B
cd /d "%~dp0"

echo ====================================
echo   Cf Galgame v2.4 启动中...
echo ====================================
echo.
echo 提示：如果窗口没有弹出，请查看下方是否有红色报错。
echo 关闭此黑框，Galgame 窗口也会随之退出。
echo.

python main_galgame.py

echo.
echo Galgame 已退出。
pause