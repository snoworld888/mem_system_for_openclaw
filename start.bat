@echo off
chcp 65001 > nul
echo [MEM SERVER] Starting...
cd /d %~dp0
python main.py %*
