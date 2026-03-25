#!/usr/bin/env python
"""诊断失败的测试"""
import subprocess, sys, os
os.chdir(r"c:\07code\mem_server")

# 只跑失败的测试
failed_tests = [
    "tests/test_long_term.py",
    "tests/test_assembler.py::TestAssemblerWithSummary",
]

for t in failed_tests:
    cmd = [sys.executable, "-m", "pytest", t, "-v", "--tb=long", "-p", "no:tmpdir"]
    r = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8",
                       errors="replace", cwd=r"c:\07code\mem_server")
    output = r.stdout + r.stderr
    for line in output.splitlines():
        if any(kw in line for kw in ("FAILED","PASSED","ERROR","AssertionError","assert","FAILED",
                                     "short test summary", "E ")):
            print(line)
