#!/usr/bin/env python
import subprocess, sys, os
os.chdir(r"c:\07code\mem_server")
cmd = [sys.executable, "-m", "pytest", "tests/test_assembler.py",
       "-v", "--tb=long", "-p", "no:tmpdir"]
r = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8",
                   errors="replace", cwd=r"c:\07code\mem_server")
output = r.stdout + r.stderr
# Write to file to avoid console encoding issues
with open("diagnose_assembler_output.txt", "w", encoding="utf-8") as f:
    f.write(output)
print("Done. See diagnose_assembler_output.txt for results.")
print("Return code:", r.returncode)
