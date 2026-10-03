# Synthetic demo data - not real production data.
import os
import sys
import argparse
import subprocess

# Ensure local imports work
sys.path.insert(0, os.path.dirname(__file__))

from agent import run_incident_agent
from tools import restore_agent_changes, git_diff, DEFAULT_REPO_DIR


def reset_environment(repo_dir: str = None):
    if repo_dir is None:
        repo_dir = DEFAULT_REPO_DIR
    repo_dir = os.path.abspath(repo_dir)

    print("=== RESETTING INCIDENTPILOT ENVIRONMENT ===")
    res = restore_agent_changes(repo_dir=repo_dir)
    
    # Remove added regression test if present
    reg_test = os.path.join(repo_dir, "tests", "test_inc4821_regression.py")
    if os.path.exists(reg_test):
        try:
            os.remove(reg_test)
            print("Removed regression test: tests/test_inc4821_regression.py")
        except Exception as e:
            print(f"Failed to remove regression test file: {e}")

    # Reset git status
    try:
        subprocess.run(["git", "checkout", "--", "."], cwd=repo_dir, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        subprocess.run(["git", "clean", "-fd"], cwd=repo_dir, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    except Exception as e:
        print(f"Git clean failed: {e}")

    print("Environment reset complete. Demo repository restored to buggy v2.4.1 state.")


def main():
    parser = argparse.ArgumentParser(description="IncidentPilot CLI Runner")
    parser.add_argument("--reset", action="store_true", help="Reset demo repository to initial baseline state")
    parser.add_argument("--repo-dir", type=str, default=DEFAULT_REPO_DIR, help="Path to demo repository")
    args = parser.parse_args()

    repo_dir = os.path.abspath(args.repo_dir)

    if args.reset:
        reset_environment(repo_dir=repo_dir)
        sys.exit(0)

    print("\n" + "=" * 80)
    print(" INCIDENTPILOT — AUTONOMOUS INCIDENT RESPONSE AGENT")
    print(" Tagline: 'From production incident to verified fix'")
    print(" Target Repository:", repo_dir)
    print("=" * 80 + "\n")

    api_key = os.environ.get("LLM_API_KEY") or os.environ.get("OPENAI_API_KEY")
    base_url = os.environ.get("LLM_BASE_URL") or os.environ.get("OPENAI_BASE_URL")
    model = os.environ.get("LLM_MODEL") or "gpt-4o"

    if api_key:
        print(f"LLM Configuration: Model={model} | BaseURL={base_url or 'Default OpenAI API'}")
    else:
        print("LLM Configuration: LLM_API_KEY not set -> Running in Autonomous Deterministic Harness Mode.")

    print("\n[STARTING INVESTIGATION LOOP...]\n")

    final_state = None

    for event_data in run_incident_agent(repo_dir=repo_dir):
        tool = event_data.get("tool")
        summary = event_data.get("summary")
        state = event_data.get("current_state", {})
        final_state = state

        step_num = state.get("step", 0)
        print(f" Step {step_num:02d} | Tool: {tool:<22} | {summary}")

    print("\n" + "=" * 80)
    print(" INVESTIGATION COMPLETED")
    print("=" * 80)

    if final_state:
        status = final_state.get("status")
        confidence = final_state.get("confidence")
        finish_data = final_state.get("finish_data") or {}

        print(f"\nFinal Incident Status  : {status}")
        print(f"Verification Confidence: {confidence}")
        print(f"Tests Passed           : {final_state.get('test_counts', {}).get('passed', 0)}/{final_state.get('test_counts', {}).get('total', 0)}")
        print(f"Patch Lines            : +{final_state.get('diff_stats', {}).get('lines_added', 0)} / -{final_state.get('diff_stats', {}).get('lines_removed', 0)}")

        if finish_data and isinstance(finish_data, dict):
            print("\n--- ROOT CAUSE DIAGNOSIS ---")
            print(f"Root Cause : {finish_data.get('root_cause')}")
            print(f"Why Introduced: {finish_data.get('why')}")
            print(f"Resolution : {finish_data.get('resolution')}")
            print(f"Prevention : {finish_data.get('prevention')}")

            print("\n--- EVIDENCE LIST ---")
            for ev in finish_data.get("evidence_ids", []):
                print(f" • {ev}")

        diff_data = git_diff(repo_dir=repo_dir)
        print("\n--- VERIFIED GIT PATCH ---")
        print(diff_data.get("diff_text", "No git diff available"))

        print("\n" + "=" * 80)
        print(" INCIDENT RESOLUTION REPORT SUMMARY")
        print("=" * 80)
        print(final_state.get("report_markdown", "No report generated"))

    if final_state and final_state.get("status") == "VERIFIED":
        sys.exit(0)
    else:
        sys.exit(1)


if __name__ == "__main__":
    main()
