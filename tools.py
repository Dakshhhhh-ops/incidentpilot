# Synthetic demo data - not real production data.
import os
import sys
import json
import re
import subprocess
from pathlib import Path

DEFAULT_REPO_DIR = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "demo-repo")
)


def validate_path(relative_path: str, repo_dir: str = None, allow_write: bool = False) -> str:
    """
    Validates that relative_path resolves safely inside repo_dir.
    Blocks path traversal ('..') and enforces directory restrictions for write operations.
    """
    if repo_dir is None:
        repo_dir = DEFAULT_REPO_DIR
    repo_dir = os.path.abspath(repo_dir)

    if not relative_path or not isinstance(relative_path, str):
        raise ValueError("Invalid path parameter")

    # Check for explicit path traversal
    normalized_rel = relative_path.replace("\\", "/").strip()
    parts = normalized_rel.split("/")
    if ".." in parts:
        raise PermissionError(f"Security error: Path traversal attempt blocked: '{relative_path}'")

    abs_path = os.path.abspath(os.path.join(repo_dir, normalized_rel))

    # Commonpath check
    try:
        common = os.path.commonpath([repo_dir, abs_path])
    except ValueError:
        raise PermissionError(f"Security error: Path outside repository boundary: '{relative_path}'")

    if common != repo_dir:
        raise PermissionError(f"Security error: Path outside repository boundary: '{relative_path}'")

    if allow_write:
        # Restrict updates strictly to app/ and tests/
        clean_rel = os.path.relpath(abs_path, repo_dir).replace("\\", "/")
        if not (clean_rel.startswith("app/") or clean_rel.startswith("tests/") or clean_rel == "app" or clean_rel == "tests"):
            raise PermissionError(
                f"Security error: Write operation blocked. Modifications restricted strictly to 'app/' and 'tests/'. Provided: '{clean_rel}'"
            )

    return abs_path


# --- AGENT TOOLS ---

def read_incident_context(repo_dir: str = None) -> dict:
    """Reads incident/incident.json and logs/deployment.log from the repository."""
    if repo_dir is None:
        repo_dir = DEFAULT_REPO_DIR

    inc_path = validate_path("incident/incident.json", repo_dir=repo_dir)
    dep_path = validate_path("logs/deployment.log", repo_dir=repo_dir)

    incident_data = {}
    if os.path.exists(inc_path):
        with open(inc_path, "r", encoding="utf-8") as f:
            incident_data = json.load(f)

    deployment_log = ""
    if os.path.exists(dep_path):
        with open(dep_path, "r", encoding="utf-8") as f:
            deployment_log = f.read()

    return {
        "incident": incident_data,
        "deployment_log": deployment_log
    }


def search_logs(query: str, max_results: int = 50, repo_dir: str = None) -> list:
    """Performs a case-insensitive search across all log files in logs/."""
    if repo_dir is None:
        repo_dir = DEFAULT_REPO_DIR

    logs_dir = validate_path("logs", repo_dir=repo_dir)
    results = []
    if not os.path.exists(logs_dir):
        return results

    query_lower = query.lower()

    for root, _, files in os.walk(logs_dir):
        for file in files:
            if file.endswith(".log"):
                full_path = os.path.join(root, file)
                rel_path = os.path.relpath(full_path, repo_dir).replace("\\", "/")
                with open(full_path, "r", encoding="utf-8", errors="ignore") as f:
                    for line_num, line in enumerate(f, start=1):
                        if query_lower in line.lower():
                            results.append({
                                "file": rel_path,
                                "line_number": line_num,
                                "text": line.strip()
                            })
                            if len(results) >= max_results:
                                return results
    return results


def read_log(path: str, start: int = 1, limit: int = 100, repo_dir: str = None) -> dict:
    """Reads specific lines from a log file inside logs/."""
    if repo_dir is None:
        repo_dir = DEFAULT_REPO_DIR

    abs_path = validate_path(path, repo_dir=repo_dir)
    rel_path = os.path.relpath(abs_path, repo_dir).replace("\\", "/")

    if not rel_path.startswith("logs/"):
        raise PermissionError("read_log can only be used on files inside 'logs/'")

    if not os.path.exists(abs_path):
        return {"error": f"Log file not found: {path}", "lines": []}

    lines = []
    with open(abs_path, "r", encoding="utf-8", errors="ignore") as f:
        for idx, line in enumerate(f, start=1):
            if idx >= start and idx < start + limit:
                lines.append({"line_number": idx, "text": line.strip()})
            if idx >= start + limit:
                break

    return {"file": rel_path, "start": start, "count": len(lines), "lines": lines}


def get_repo_overview(repo_dir: str = None) -> dict:
    """Returns directory tree, file list, and byte sizes without semantic summaries."""
    if repo_dir is None:
        repo_dir = DEFAULT_REPO_DIR

    repo_dir = os.path.abspath(repo_dir)
    files_list = []

    for root, dirs, files in os.walk(repo_dir):
        # Skip git internal metadata
        if ".git" in dirs:
            dirs.remove(".git")
        if "__pycache__" in dirs:
            dirs.remove("__pycache__")
        if ".pytest_cache" in dirs:
            dirs.remove(".pytest_cache")

        for file in files:
            full_path = os.path.join(root, file)
            rel_path = os.path.relpath(full_path, repo_dir).replace("\\", "/")
            size = os.path.getsize(full_path)
            files_list.append({
                "path": rel_path,
                "size_bytes": size
            })

    return {
        "repo_dir": os.path.basename(repo_dir),
        "total_files": len(files_list),
        "files": files_list
    }


def search_code(query: str, repo_dir: str = None) -> list:
    """Fast local search across app/ and tests/."""
    if repo_dir is None:
        repo_dir = DEFAULT_REPO_DIR

    results = []
    query_lower = query.lower()

    for folder in ["app", "tests"]:
        abs_folder = validate_path(folder, repo_dir=repo_dir)
        if os.path.exists(abs_folder):
            for root, _, files in os.walk(abs_folder):
                for file in files:
                    if file.endswith(".py"):
                        full_path = os.path.join(root, file)
                        rel_path = os.path.relpath(full_path, repo_dir).replace("\\", "/")
                        with open(full_path, "r", encoding="utf-8", errors="ignore") as f:
                            for line_num, line in enumerate(f, start=1):
                                if query_lower in line.lower():
                                    results.append({
                                        "file": rel_path,
                                        "line_number": line_num,
                                        "text": line.strip()
                                    })
    return results


def read_files(paths: list[str], repo_dir: str = None) -> dict:
    """Reads specified file contents relative to demo-repo/."""
    if repo_dir is None:
        repo_dir = DEFAULT_REPO_DIR

    contents = {}
    for p in paths:
        try:
            abs_p = validate_path(p, repo_dir=repo_dir)
            rel_p = os.path.relpath(abs_p, repo_dir).replace("\\", "/")
            if os.path.exists(abs_p):
                with open(abs_p, "r", encoding="utf-8") as f:
                    contents[rel_p] = f.read()
            else:
                contents[rel_p] = f"[ERROR: File not found: {p}]"
        except Exception as e:
            contents[p] = f"[SECURITY/READ ERROR: {str(e)}]"

    return contents


def update_files(updates: list[dict], repo_dir: str = None) -> dict:
    """
    Takes [{'path': relative_path, 'content': text_content}].
    Validates paths are inside app/ or tests/.
    Writes contents to disk.
    """
    if repo_dir is None:
        repo_dir = DEFAULT_REPO_DIR

    updated = []
    errors = []

    for item in updates:
        rel_p = item.get("path")
        content = item.get("content", "")
        try:
            abs_p = validate_path(rel_p, repo_dir=repo_dir, allow_write=True)
            os.makedirs(os.path.dirname(abs_p), exist_ok=True)
            with open(abs_p, "w", encoding="utf-8") as f:
                f.write(content)
            clean_rel = os.path.relpath(abs_p, repo_dir).replace("\\", "/")
            updated.append(clean_rel)
        except Exception as e:
            errors.append({"path": rel_p, "error": str(e)})

    return {
        "success": len(errors) == 0,
        "updated_files": updated,
        "errors": errors
    }


def run_tests(repo_dir: str = None) -> dict:
    """Executes pytest -q --tb=short in demo-repo/ via subprocess with a 30s timeout."""
    if repo_dir is None:
        repo_dir = DEFAULT_REPO_DIR

    repo_dir = os.path.abspath(repo_dir)

    cmd = [sys.executable, "-m", "pytest", "-q", "--tb=short"]
    try:
        proc = subprocess.run(
            cmd,
            cwd=repo_dir,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=30
        )
        stdout = proc.stdout or ""
        stderr = proc.stderr or ""
        exit_code = proc.returncode

        # Parse test counts from output
        # E.g. "11 passed in 0.05s" or "1 failed, 11 passed in 0.10s"
        passed = 0
        failed = 0

        passed_match = re.search(r"(\d+)\s+passed", stdout)
        if passed_match:
            passed = int(passed_match.group(1))

        failed_match = re.search(r"(\d+)\s+failed", stdout)
        if failed_match:
            failed = int(failed_match.group(1))

        total = passed + failed

        return {
            "passed": passed,
            "failed": failed,
            "total": total,
            "exit_code": exit_code,
            "stdout": stdout,
            "stderr": stderr
        }
    except subprocess.TimeoutExpired:
        return {
            "passed": 0,
            "failed": 1,
            "total": 1,
            "exit_code": -1,
            "stdout": "",
            "stderr": "Pytest execution timed out after 30 seconds"
        }
    except Exception as e:
        return {
            "passed": 0,
            "failed": 1,
            "total": 1,
            "exit_code": -1,
            "stdout": "",
            "stderr": f"Failed to execute pytest: {str(e)}"
        }


def reproduce_incident(repo_dir: str = None) -> dict:
    """
    Runs an isolated Python subprocess executing process_checkout({"coupon": "EXPIRED_SAVE20", "items": [{"id": "ITEM-1", "price": 50.0}]}).
    Returns {status_code_observed: int, status: str, stdout: str, stderr: str}.
    """
    if repo_dir is None:
        repo_dir = DEFAULT_REPO_DIR

    repo_dir = os.path.abspath(repo_dir)

    code = (
        "import sys, json; "
        "sys.path.insert(0, '.'); "
        "from app.checkout import process_checkout; "
        "payload = {'items': [{'id': 'ITEM-1', 'price': 50.0}], 'coupon': 'EXPIRED_SAVE20'}; "
        "res = process_checkout(payload); "
        "print(json.dumps(res))"
    )

    cmd = [sys.executable, "-c", code]
    try:
        proc = subprocess.run(
            cmd,
            cwd=repo_dir,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=10
        )
        stdout = proc.stdout.strip()
        stderr = proc.stderr.strip()

        status_code_observed = 500
        status_text = "UNKNOWN"

        if proc.returncode == 0 and stdout:
            try:
                res_dict = json.loads(stdout)
                status_code_observed = res_dict.get("status", 500)
                status_text = res_dict.get("error", "OK" if status_code_observed == 200 else "ERROR")
            except Exception:
                pass

        return {
            "status_code_observed": status_code_observed,
            "status": status_text,
            "stdout": stdout,
            "stderr": stderr
        }
    except Exception as e:
        return {
            "status_code_observed": 500,
            "status": "SUBPROCESS_ERROR",
            "stdout": "",
            "stderr": str(e)
        }


def finish(root_cause: str, why: str, evidence_ids: list, resolution: str, prevention: str) -> dict:
    """Delivers the agent's final diagnosis and resolution report."""
    return {
        "status": "COMPLETED",
        "root_cause": root_cause,
        "why": why,
        "evidence_ids": evidence_ids if isinstance(evidence_ids, list) else [str(evidence_ids)],
        "resolution": resolution,
        "prevention": prevention
    }


# --- HARNESS HELPERS (NOT EXPOSED TO LLM) ---

def git_diff(repo_dir: str = None) -> dict:
    """Executes git diff inside demo-repo/ and returns raw diff string + numstat counts."""
    if repo_dir is None:
        repo_dir = DEFAULT_REPO_DIR

    repo_dir = os.path.abspath(repo_dir)

    try:
        diff_proc = subprocess.run(
            ["git", "diff"],
            cwd=repo_dir,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        raw_diff = diff_proc.stdout or ""

        stat_proc = subprocess.run(
            ["git", "diff", "--numstat"],
            cwd=repo_dir,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        stat_out = stat_proc.stdout or ""

        added = 0
        removed = 0
        for line in stat_out.strip().split("\n"):
            if line:
                parts = line.split()
                if len(parts) >= 2:
                    if parts[0] != "-":
                        added += int(parts[0])
                    if parts[1] != "-":
                        removed += int(parts[1])

        return {
            "diff_text": raw_diff,
            "lines_added": added,
            "lines_removed": removed
        }
    except Exception as e:
        return {
            "diff_text": f"git diff failed: {str(e)}",
            "lines_added": 0,
            "lines_removed": 0
        }


def restore_agent_changes(repo_dir: str = None) -> dict:
    """
    Executes git checkout -- app/ to revert application fixes while PRESERVING new test files in tests/.
    """
    if repo_dir is None:
        repo_dir = DEFAULT_REPO_DIR

    repo_dir = os.path.abspath(repo_dir)

    try:
        proc = subprocess.run(
            ["git", "checkout", "--", "app/"],
            cwd=repo_dir,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        return {
            "success": proc.returncode == 0,
            "stdout": proc.stdout,
            "stderr": proc.stderr
        }
    except Exception as e:
        return {
            "success": False,
            "stdout": "",
            "stderr": str(e)
        }
