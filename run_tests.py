#!/usr/bin/env python
"""运行测试并输出结果，绕过 pytest session-finish 的 Windows 路径 bug"""
import subprocess
import sys
import os

os.chdir(r"c:\07code\mem_server")

test_suites = [
    ("Compressor & TokenCounter",  ["tests/test_compressor.py"],        "--tb=short"),
    ("Short Term Memory (STM)",    ["tests/test_short_term.py"],        "--tb=short"),
    ("Long Term Memory (LTM)",     ["tests/test_long_term.py"],         "--tb=short"),
    ("Context Assembler",          ["tests/test_assembler.py"],         "--tb=short"),
    ("HTTP API Integration",       ["tests/test_api_integration.py"],   "--tb=short"),
]

total_passed = 0
total_failed = 0
total_error  = 0
summary_lines = []

for name, files, tb in test_suites:
    print(f"\n{'='*60}")
    print(f"  Running: {name}")
    print(f"{'='*60}")
    cmd = [sys.executable, "-m", "pytest", "-p", "no:tmpdir",
           "-v", tb] + files
    result = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8",
                            errors="replace", cwd=r"c:\07code\mem_server")

    # 输出结果
    output = result.stdout + result.stderr
    for line in output.splitlines():
        print(line)

    # 解析统计
    for line in output.splitlines():
        if " passed" in line and ("======" in line or "short" in line):
            parts = line.split()
            for i, p in enumerate(parts):
                if p == "passed":
                    try:
                        total_passed += int(parts[i-1])
                    except Exception:
                        pass
                if p == "failed":
                    try:
                        total_failed += int(parts[i-1])
                    except Exception:
                        pass
                if p == "error":
                    try:
                        total_error += int(parts[i-1])
                    except Exception:
                        pass

    # 最后一行摘要
    lines = [l for l in output.splitlines() if "passed" in l or "failed" in l or "error" in l]
    if lines:
        summary_lines.append(f"  [{name}] {lines[-1].strip()}")

print("\n" + "="*60)
print("  TOTAL SUMMARY")
print("="*60)
for s in summary_lines:
    print(s)
print(f"\n  Total passed: {total_passed}")
print(f"  Total failed: {total_failed}")
print(f"  Total errors: {total_error}")
