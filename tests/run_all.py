"""Run all test suites against production."""
import subprocess
import sys

BASE = sys.argv[1] if len(sys.argv) > 1 else "https://thisminute.org"

print("=" * 60)
print("RUNNING ALL TEST SUITES")
print("=" * 60)

smoke = subprocess.run(
    [sys.executable, "tests/smoke_test.py", "--base-url", BASE],
    capture_output=False,
)

deep = subprocess.run(
    [sys.executable, "tests/deep_test.py", "--base-url", BASE],
    capture_output=False,
)

if smoke.returncode == 0 and deep.returncode == 0:
    print("\nALL SUITES PASSED")
else:
    print(f"\nSUITE RESULTS: smoke={'PASS' if smoke.returncode == 0 else 'FAIL'}, deep={'PASS' if deep.returncode == 0 else 'FAIL'}")
    sys.exit(1)
