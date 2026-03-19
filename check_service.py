#!/usr/bin/env python
"""检测服务是否在运行"""

import requests
import sys
import time

def check_service():
    """检查服务状态"""
    ports = range(7000, 7020)
    
    for port in ports:
        try:
            url = f'http://127.0.0.1:{port}/health'
            response = requests.get(url, timeout=2)
            if response.status_code == 200:
                print(f"[OK] Service running on port {port}")
                print(f"[INFO] Response: {response.json()}")
                return port
        except Exception as e:
            continue
    
    print("[ERROR] Service not found on any port (7000-7020)")
    print("[INFO] Please run: python auto_start.py")
    return None

if __name__ == '__main__':
    time.sleep(2)  # 等待服务启动
    port = check_service()
    if port:
        print(f"\n[SUCCESS] Use http://127.0.0.1:{port} for memory service")
        sys.exit(0)
    else:
        sys.exit(1)
