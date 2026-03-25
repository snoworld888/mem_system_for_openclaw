#!/usr/bin/env python
"""诊断API集成测试错误"""
import subprocess, sys, os
os.chdir(r"c:\07code\mem_server")

cmd = [sys.executable, "-m", "pytest", "tests/test_api_integration.py::TestHealth",
       "-v", "--tb=long", "-p", "no:tmpdir", "-s"]
r = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8",
                   errors="replace", cwd=r"c:\07code\mem_server")
output = r.stdout + r.stderr
for line in output.splitlines():
    print(line)
