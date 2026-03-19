@echo off
setlocal enabledelayedexpansion

REM 检查是否提供了端口参数
if "%1"=="" (
    set PORT=7000
) else (
    set PORT=%1
)

echo [%date% %time%] Starting memory service on port %PORT%...

cd /d c:\07code\mem_server

REM 使用不同的端口
python main.py --port %PORT%

pause
