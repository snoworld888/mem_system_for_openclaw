#!/usr/bin/env python
"""快速启动脚本 - 在可用端口上启动记忆服务"""

import subprocess
import sys
import time
import socket
import os

def find_available_port(start_port=7000, max_attempts=20):
    """找到一个可用的端口"""
    for port in range(start_port, start_port + max_attempts):
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.bind(('127.0.0.1', port))
            sock.close()
            return port
        except OSError:
            continue
    return None

def main():
    # 找到可用端口
    port = find_available_port(7000)
    
    if port is None:
        print("[ERROR] No available port found! Please check system resources.")
        sys.exit(1)
    
    print(f"[OK] Using port: {port}")
    print(f"[INFO] Starting memory service...")
    print(f"[INFO] Access at: http://127.0.0.1:{port}")
    print(f"[INFO] API docs at: http://127.0.0.1:{port}/docs")
    
    os.chdir('c:/07code/mem_server')
    
    try:
        subprocess.run([
            sys.executable, 'main.py',
            '--port', str(port),
            '--host', '127.0.0.1'
        ])
    except KeyboardInterrupt:
        print("\n[INFO] Service stopped")
        sys.exit(0)

if __name__ == '__main__':
    main()
