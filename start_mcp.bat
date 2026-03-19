@echo off
chcp 65001 > nul
echo [MEM SERVER] Starting MCP stdio mode...
cd /d %~dp0
python main.py --mcp
