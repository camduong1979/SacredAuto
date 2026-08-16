@echo off
title SACRED GOD BOT
color 0A

:: Di chuyen ve dung thu muc chua file .bat nay
cd /d "%~dp0"

echo [INFO] Dang khoi dong Sacred Bot...
echo [HINT] Thu muc hien tai: %cd%
echo.

python Sacred_Bot.py
pause