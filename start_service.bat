@echo off
cd /d c:\07code\mem_server
echo 启动记忆服务...
python main.py --host 127.0.0.1 --port 9000
pause
