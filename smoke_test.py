# Synthetic demo data - not real production data.
import os
import sys

# Ensure local imports work
sys.path.insert(0, os.path.dirname(__file__))

from tools import (
    validate_path,
    update_files,
    run_tests,
    reproduce_incident,
    git_diff,
    restore_agent_changes,
    DEFAULT_REPO_DIR
)


def run_smoke_tests():
    print("=== INCIDENTPILOT SMOKE TESTS ===")
    passed_tests = 0
    total_tests = 0

    # Test 1: Path Traversal Blocking (Reading outside repo)
    total_tests += 1
    try:
        validate_path("../app.py", repo_dir=DEFAULT_REPO_DIR)
        print("[FAIL] Test 1 FAILED: Path traversal '../app.py' was allowed!")
    except (PermissionError, ValueError) as e:
        print(f"[PASS] Test 1 PASSED: Path traversal blocked correctly -> {e}")
        passed_tests += 1

    # Test 2: Modification Restriction (Writing outside app/ or tests/)
    total_tests += 1
    res = update_files([{"path": "logs/malicious.log", "content": "hacked"}], repo_dir=DEFAULT_REPO_DIR)
    if not res["success"] and len(res["errors"]) > 0:
        print(f"[PASS] Test 2 PASSED: Write outside app/ or tests/ blocked correctly -> {res['errors'][0]['error']}")
        passed_tests += 1
    else:
        print("[FAIL] Test 2 FAILED: Write to 'logs/' was permitted!")

    # Test 3: Valid Write Permission (Writing to tests/ and app/)
    total_tests += 1
    res_valid = update_files([
        {"path": "tests/test_smoke_dummy.py", "content": "# dummy test file\ndef test_dummy(): pass\n"}
    ], repo_dir=DEFAULT_REPO_DIR)
    if res_valid["success"]:
        print("[PASS] Test 3 PASSED: Valid write to tests/ succeeded")
        passed_tests += 1
    else:
        print(f"[FAIL] Test 3 FAILED: Valid write failed -> {res_valid['errors']}")

    # Test 4: Pytest Output Parsing
    total_tests += 1
    pytest_res = run_tests(repo_dir=DEFAULT_REPO_DIR)
    if pytest_res["exit_code"] == 0 and pytest_res["passed"] >= 11:
        print(f"[PASS] Test 4 PASSED: Pytest parsed successfully -> passed={pytest_res['passed']}, total={pytest_res['total']}")
        passed_tests += 1
    else:
        print(f"[FAIL] Test 4 FAILED: Pytest execution unexpected -> {pytest_res}")

    # Test 5: Incident Reproduction
    total_tests += 1
    repro_res = reproduce_incident(repo_dir=DEFAULT_REPO_DIR)
    if repro_res["status_code_observed"] == 500:
        print(f"[PASS] Test 5 PASSED: Incident reproduced successfully (observed 500)")
        passed_tests += 1
    else:
        print(f"[FAIL] Test 5 FAILED: Incident reproduction failed -> {repro_res}")

    # Test 6: Git Restoration
    total_tests += 1
    restore_res = restore_agent_changes(repo_dir=DEFAULT_REPO_DIR)
    dummy_file = os.path.join(DEFAULT_REPO_DIR, "tests", "test_smoke_dummy.py")
    if os.path.exists(dummy_file):
        os.remove(dummy_file)
    diff_res = git_diff(repo_dir=DEFAULT_REPO_DIR)
    if diff_res["lines_added"] == 0 and diff_res["lines_removed"] == 0:
        print("[PASS] Test 6 PASSED: Git state restored clean")
        passed_tests += 1
    else:
        print(f"[FAIL] Test 6 FAILED: Git state not clean after restore -> {diff_res}")

    print(f"\nRESULTS: {passed_tests}/{total_tests} smoke tests passed.")
    if passed_tests == total_tests:
        print("SUCCESS: ALL SMOKE TESTS PASSED!")
        sys.exit(0)
    else:
        print("ERROR: SOME SMOKE TESTS FAILED!")
        sys.exit(1)


if __name__ == "__main__":
    run_smoke_tests()
