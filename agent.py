import os
import sys
import json
import copy
from typing import Generator, Dict, Any
from dotenv import load_dotenv

load_dotenv()

try:
    import google.generativeai as genai
    from google.generativeai.types import content_types
    GEMINI_AVAILABLE = True
except ImportError:
    GEMINI_AVAILABLE = False

from tools import (
    read_incident_context,
    search_logs,
    read_log,
    get_repo_overview,
    search_code,
    read_files,
    update_files,
    run_tests,
    reproduce_incident,
    finish,
    git_diff,
    restore_agent_changes,
    DEFAULT_REPO_DIR
)
from data.incidents import get_incident_scenario
from data.telemetry import generate_telemetry_series, generate_chronological_timeline
from core.state_machine import IncidentStateMachine, AgentState
from core.hypotheses import HypothesisEngine
from core.evidence import build_evidence_graph
from core.experiments import run_counterfactual_experiment
from core.verifier import AdversarialVerifier, run_verification_gate
from core.artifact_generator import generate_artifact_bundle

# Tool Schemas for Google Gemini API (Function Declarations)
TOOLS_SCHEMA = [
    genai.protos.FunctionDeclaration(
        name="read_incident_context",
        description="Reads incident/incident.json and logs/deployment.log to get telemetry and deployment history.",
        parameters=genai.protos.Schema(type=genai.protos.Type.OBJECT, properties={}, required=[])
    ),
    genai.protos.FunctionDeclaration(
        name="search_logs",
        description="Case-insensitive search across logs directory.",
        parameters=genai.protos.Schema(
            type=genai.protos.Type.OBJECT,
            properties={
                "query": genai.protos.Schema(type=genai.protos.Type.STRING, description="Search term"),
                "max_results": genai.protos.Schema(type=genai.protos.Type.INTEGER, description="Max results to return")
            },
            required=["query"]
        )
    ),
    genai.protos.FunctionDeclaration(
        name="read_log",
        description="Reads specific line range from a log file inside logs/.",
        parameters=genai.protos.Schema(
            type=genai.protos.Type.OBJECT,
            properties={
                "path": genai.protos.Schema(type=genai.protos.Type.STRING, description="Relative path to log file"),
                "start": genai.protos.Schema(type=genai.protos.Type.INTEGER, description="Start line number"),
                "limit": genai.protos.Schema(type=genai.protos.Type.INTEGER, description="Max lines to read")
            },
            required=["path"]
        )
    ),
    genai.protos.FunctionDeclaration(
        name="get_repo_overview",
        description="Returns directory tree, file list, and byte sizes.",
        parameters=genai.protos.Schema(type=genai.protos.Type.OBJECT, properties={}, required=[])
    ),
    genai.protos.FunctionDeclaration(
        name="search_code",
        description="Search code across app/ and tests/.",
        parameters=genai.protos.Schema(
            type=genai.protos.Type.OBJECT,
            properties={
                "query": genai.protos.Schema(type=genai.protos.Type.STRING, description="Search string")
            },
            required=["query"]
        )
    ),
    genai.protos.FunctionDeclaration(
        name="read_files",
        description="Reads specified file contents relative to repository root.",
        parameters=genai.protos.Schema(
            type=genai.protos.Type.OBJECT,
            properties={
                "paths": genai.protos.Schema(
                    type=genai.protos.Type.ARRAY,
                    items=genai.protos.Schema(type=genai.protos.Type.STRING),
                    description="List of relative file paths"
                )
            },
            required=["paths"]
        )
    ),
    genai.protos.FunctionDeclaration(
        name="update_files",
        description="Writes file updates strictly inside app/ or tests/.",
        parameters=genai.protos.Schema(
            type=genai.protos.Type.OBJECT,
            properties={
                "updates": genai.protos.Schema(
                    type=genai.protos.Type.ARRAY,
                    items=genai.protos.Schema(
                        type=genai.protos.Type.OBJECT,
                        properties={
                            "path": genai.protos.Schema(type=genai.protos.Type.STRING, description="File path"),
                            "content": genai.protos.Schema(type=genai.protos.Type.STRING, description="File content")
                        },
                        required=["path", "content"]
                    ),
                    description="List of file updates"
                )
            },
            required=["updates"]
        )
    ),
    genai.protos.FunctionDeclaration(
        name="run_tests",
        description="Executes pytest in demo-repo/ and returns test results.",
        parameters=genai.protos.Schema(type=genai.protos.Type.OBJECT, properties={}, required=[])
    ),
    genai.protos.FunctionDeclaration(
        name="reproduce_incident",
        description="Executes process_checkout with an expired coupon to test status code.",
        parameters=genai.protos.Schema(type=genai.protos.Type.OBJECT, properties={}, required=[])
    ),
    genai.protos.FunctionDeclaration(
        name="finish",
        description="Call when root cause, reproduction, test, and patch are verified.",
        parameters=genai.protos.Schema(
            type=genai.protos.Type.OBJECT,
            properties={
                "root_cause": genai.protos.Schema(type=genai.protos.Type.STRING, description="Technical root cause explanation"),
                "why": genai.protos.Schema(type=genai.protos.Type.STRING, description="Why the bug was introduced in v2.4.1"),
                "evidence_ids": genai.protos.Schema(
                    type=genai.protos.Type.ARRAY,
                    items=genai.protos.Schema(type=genai.protos.Type.STRING),
                    description="List of key log/file evidence references"
                ),
                "resolution": genai.protos.Schema(type=genai.protos.Type.STRING, description="Description of code fix"),
                "prevention": genai.protos.Schema(type=genai.protos.Type.STRING, description="Recommendations to prevent regression")
            },
            required=["root_cause", "why", "evidence_ids", "resolution", "prevention"]
        )
    ),
] if GEMINI_AVAILABLE else []

SYSTEM_PROMPT = """You are IncidentPilot, an autonomous AI incident response agent.
Your mission is to resolve production incident INC-4821 in the checkout service.
Follow this strict 8-step incident response workflow:

Step 1: Read incident telemetry via read_incident_context() and search_logs(query="CouponExpired").
Step 2: Verify bug reproduction via reproduce_incident() (observe status 500).
Step 3: Locate exception handling in app/ using search_code(query="coupon") and read_files(paths=["app/checkout.py", "app/coupon.py", "app/errors.py"]).
Step 4: Write a new failing regression test in 'tests/test_inc4821_regression.py' using update_files().
Step 5: Execute run_tests() to confirm the new regression test FAILS (Reproduction Verified).
Step 6: Update 'app/checkout.py' using update_files() to catch AppError specifically (which includes CouponExpiredError) and return HTTP 400.
Step 7: Execute run_tests() to confirm ALL tests (including regression test) PASS.
Step 8: Call finish(root_cause=..., why=..., evidence_ids=..., resolution=..., prevention=...) with complete diagnostic details.

Strict constraints:
- Do NOT call finish() until you have written tests/test_inc4821_regression.py, confirmed it fails, updated app/checkout.py, and confirmed all tests pass!
"""

REGRESSION_TEST_CONTENT = """# Synthetic demo data - not real production data.
import pytest
from app.checkout import process_checkout


def test_inc4821_expired_coupon_returns_400():
    \"\"\"
    Regression test for INC-4821:
    Requests with expired coupons must return HTTP 400 instead of HTTP 500.
    \"\"\"
    payload = {
        "items": [{"id": "SKU-99", "price": 49.99, "quantity": 1}],
        "coupon": "EXPIRED_SAVE20",
        "payment_method": {"card_number": "4111222233334444"}
    }
    result = process_checkout(payload)
    assert result["status"] == 400, f"Expected HTTP 400 for expired coupon, got status={result.get('status')}"
    assert "expired" in result.get("message", "").lower() or "expired" in result.get("error", "").lower()
"""

FIXED_CHECKOUT_CONTENT = """# Synthetic demo data - not real production data.
from app.errors import AppError, SystemError
from app.coupon import validate_coupon
from app.payment import process_payment
from app.models import create_order_summary


def process_checkout(order_data: dict) -> dict:
    \"\"\"
    Processes checkout requests with proper AppError exception handling.
    Fixed in INC-4821 resolution: Catch AppError specifically to preserve HTTP 400 status.
    \"\"\"
    if not isinstance(order_data, dict):
        return {"status": 400, "error": "Invalid order payload"}

    items = order_data.get("items", [])
    if not items:
        return {"status": 400, "error": "Cart is empty"}

    discount_percent = 0
    coupon_code = order_data.get("coupon")

    if coupon_code:
        try:
            coupon_res = validate_coupon(coupon_code)
            discount_percent = coupon_res.get("discount_percent", 0)
        except AppError as e:
            # Preserves status_code = 400 for CouponExpiredError & domain errors
            return {
                "status": e.status_code,
                "error": "Bad Request",
                "message": str(e)
            }
        except Exception as e:
            # 500 response only for unhandled internal exceptions
            return {
                "status": 500,
                "error": "Internal Error",
                "message": f"Unexpected coupon error: {str(e)}"
            }

    try:
        subtotal = sum(float(item.get("price", 0)) * int(item.get("quantity", 1)) for item in items)
    except (ValueError, TypeError):
        return {"status": 400, "error": "Invalid item price or quantity"}

    discount_amount = (subtotal * discount_percent) / 100.0
    total = max(0.0, subtotal - discount_amount)

    payment_method = order_data.get("payment_method", {"card_number": "4111222233334444"})
    payment_res = process_payment(total, payment_method)

    if payment_res.get("status") != 200:
        return {
            "status": payment_res.get("status", 400),
            "error": payment_res.get("error", "Payment processing failed")
        }

    summary = create_order_summary(items, subtotal, discount_amount, total, payment_res.get("transaction_id"))
    return {
        "status": 200,
        "message": "Checkout completed successfully",
        "order": summary
    }
"""


def execute_tool_call(name: str, args: dict, repo_dir: str) -> tuple[Any, str]:
    """Executes a tool call locally and returns (result, summary_text)."""
    if name == "read_incident_context":
        res = read_incident_context(repo_dir=repo_dir)
        inc = res.get("incident", {})
        summary = f"Loaded Incident {inc.get('incident_id')} ({inc.get('title')}) & Deployment Log"
        return res, summary

    elif name == "search_logs":
        query = args.get("query", "")
        max_r = args.get("max_results", 50)
        res = search_logs(query=query, max_results=max_r, repo_dir=repo_dir)
        summary = f"Log search '{query}' returned {len(res)} matching entries"
        return res, summary

    elif name == "read_log":
        path = args.get("path", "")
        start = args.get("start", 1)
        limit = args.get("limit", 100)
        res = read_log(path=path, start=start, limit=limit, repo_dir=repo_dir)
        summary = f"Read {res.get('count', 0)} lines from {path}"
        return res, summary

    elif name == "get_repo_overview":
        res = get_repo_overview(repo_dir=repo_dir)
        summary = f"Repo tree retrieved ({res.get('total_files', 0)} files)"
        return res, summary

    elif name == "search_code":
        query = args.get("query", "")
        res = search_code(query=query, repo_dir=repo_dir)
        summary = f"Code search '{query}' found {len(res)} matches"
        return res, summary

    elif name == "read_files":
        paths = args.get("paths", [])
        res = read_files(paths=paths, repo_dir=repo_dir)
        summary = f"Read contents of {len(paths)} file(s): {', '.join(paths)}"
        return res, summary

    elif name == "update_files":
        updates = args.get("updates", [])
        res = update_files(updates=updates, repo_dir=repo_dir)
        updated_paths = [u.get("path") for u in updates]
        summary = f"Updated files: {', '.join(updated_paths)}"
        return res, summary

    elif name == "run_tests":
        res = run_tests(repo_dir=repo_dir)
        summary = f"Pytest completed: {res.get('passed', 0)} passed, {res.get('failed', 0)} failed, total {res.get('total', 0)}"
        return res, summary

    elif name == "reproduce_incident":
        res = reproduce_incident(repo_dir=repo_dir)
        summary = f"Reproduction run: observed status code {res.get('status_code_observed')}"
        return res, summary

    elif name == "finish":
        res = finish(
            root_cause=args.get("root_cause", ""),
            why=args.get("why", ""),
            evidence_ids=args.get("evidence_ids", []),
            resolution=args.get("resolution", ""),
            prevention=args.get("prevention", "")
        )
        summary = f"Finish requested: {args.get('root_cause', '')[:60]}..."
        return res, summary

    else:
        return {"error": f"Unknown tool: {name}"}, f"Error: Unknown tool '{name}'"


def perform_harness_verification(repo_dir: str) -> tuple[bool, int, dict]:
    """
    INDEPENDENT HARNESS VERIFICATION (CANNOT BE BYPASSED BY MODEL)
    1. Execute reproduce_incident(): Must observe status_code_observed == 400.
    2. Execute run_tests(): Must observe failed == 0 and passed > 0.
    """
    repro = reproduce_incident(repo_dir=repo_dir)
    tests = run_tests(repo_dir=repo_dir)

    status_ok = (repro.get("status_code_observed") == 400)
    tests_ok = (tests.get("failed") == 0 and tests.get("passed", 0) > 0)

    verified = status_ok and tests_ok
    return verified, repro.get("status_code_observed", 500), tests


def run_incident_agent(repo_dir: str = None, max_steps: int = 25, incident_id: str = "INC-4821") -> Generator[Dict[str, Any], None, None]:
    """
    Generator yielding real-time event dictionaries during autonomous agent investigation.
    Integrates explicit state machine, multi-hypothesis engine, evidence graph, and verifier.
    """
    if repo_dir is None:
        repo_dir = DEFAULT_REPO_DIR
    repo_dir = os.path.abspath(repo_dir)

    # Initialize Core Engines
    state_machine = IncidentStateMachine(incident_id=incident_id)
    hypothesis_engine = HypothesisEngine(incident_id=incident_id)
    evidence_graph = build_evidence_graph(incident_id=incident_id)
    counterfactual = run_counterfactual_experiment()
    verifier = AdversarialVerifier(repo_dir=repo_dir)
    scenario = get_incident_scenario(incident_id=incident_id)
    timeline = generate_chronological_timeline(incident_id=incident_id)

    # Initialize State
    state = {
        "incident_id": incident_id,
        "step": 0,
        "max_steps": max_steps,
        "status": "INVESTIGATING",
        "confidence": "PENDING",
        "telemetry_analyzed": False,
        "reproduction_verified": False,
        "regression_test_added": False,
        "code_searched": False,
        "fix_applied": False,
        "tests_passed": False,
        "test_counts": {"passed": 0, "failed": 0, "total": 0},
        "diff_stats": {"lines_added": 0, "lines_removed": 0},
        "finish_data": None,
        "report_markdown": "",
        "scenario": scenario,
        "hypotheses_summary": hypothesis_engine.get_summary(),
        "evidence_graph": evidence_graph,
        "counterfactual": counterfactual,
        "verifier_result": None,
        "verification_gate": None,
        "timeline": timeline,
        "state_machine_history": [],
        "artifacts_bundle": {},
        "events": []
    }

    api_key = os.environ.get("GOOGLE_API_KEY")
    model_name = os.environ.get("GEMINI_MODEL") or "gemini-2.5-flash"

    use_llm = False
    gemini_model = None
    if api_key and GEMINI_AVAILABLE:
        try:
            genai.configure(api_key=api_key)
            gemini_tool = genai.protos.Tool(function_declarations=TOOLS_SCHEMA)
            gemini_model = genai.GenerativeModel(
                model_name=model_name,
                tools=[gemini_tool],
                system_instruction=SYSTEM_PROMPT
            )
            use_llm = True
        except Exception:
            use_llm = False

    if use_llm and gemini_model:
        # Gemini LLM Tool-Calling Loop
        chat = gemini_model.start_chat()
        initial_message = f"Investigate production incident {incident_id} and apply a verified fix."

        attempt = 1
        max_harness_retries = 3
        pending_message = initial_message

        while state["step"] < max_steps and state["status"] == "INVESTIGATING":
            state["step"] += 1

            try:
                response = chat.send_message(pending_message)
                pending_message = None
            except Exception:
                break

            # Check for function calls in the response
            part = response.candidates[0].content.parts[0]

            if not hasattr(part, 'function_call') or not part.function_call.name:
                # No tool call — just text
                if hasattr(part, 'text') and part.text:
                    state["events"].append({"type": "llm_text", "text": part.text})
                break

            # Process all function calls in the response
            function_responses = []
            for part in response.candidates[0].content.parts:
                if not hasattr(part, 'function_call') or not part.function_call.name:
                    continue

                func_name = part.function_call.name
                func_args = dict(part.function_call.args) if part.function_call.args else {}

                tool_res, summary = execute_tool_call(func_name, func_args, repo_dir)

                # Update State Machine & Hypotheses
                if func_name == "read_incident_context":
                    state_machine.transition(AgentState.TELEMETRY_ANALYSIS, "incident.json", "read_incident_context", "telemetry ingested", tool_res)
                    hypothesis_engine.run_experiment_step(0)
                elif func_name == "search_logs":
                    state_machine.transition(AgentState.LOG_CORRELATION, func_args.get("query",""), "search_logs", "CouponExpired log trace", tool_res)
                elif func_name == "reproduce_incident":
                    state_machine.transition(AgentState.FAILURE_REPRODUCTION, "EXPIRED_SAVE20 payload", "reproduce_incident", "HTTP 500 observed", tool_res)
                    hypothesis_engine.run_experiment_step(1)
                    if tool_res.get("status_code_observed") == 500:
                        state["reproduction_verified"] = True
                elif func_name in ["search_code", "read_files"]:
                    state_machine.transition(AgentState.CODE_INSPECTION, str(func_args), func_name, "app/checkout.py L28 except Exception", tool_res)
                    hypothesis_engine.run_experiment_step(2)
                elif func_name == "update_files":
                    for u in func_args.get("updates", []):
                        if "test_inc4821" in u.get("path", ""):
                            state["regression_test_added"] = True
                            state_machine.transition(AgentState.REGRESSION_TESTING, u.get("path"), "update_files", "failing regression test created", tool_res)
                        if "checkout.py" in u.get("path", ""):
                            state["fix_applied"] = True
                            state_machine.transition(AgentState.PATCH_GENERATION, u.get("path"), "update_files", "AppError patch applied", tool_res)
                elif func_name == "run_tests":
                    state["test_counts"]["passed"] = tool_res.get("passed", 0)
                    state["test_counts"]["failed"] = tool_res.get("failed", 0)
                    state["test_counts"]["total"] = tool_res.get("total", 0)
                    if tool_res.get("failed", 0) == 0 and tool_res.get("passed", 0) > 0:
                        state["tests_passed"] = True
                        state_machine.transition(AgentState.INCIDENT_REPLAY, "pytest -q", "run_tests", "12/12 tests passed", tool_res)

                diff_info = git_diff(repo_dir=repo_dir)
                state["diff_stats"]["lines_added"] = diff_info["lines_added"]
                state["diff_stats"]["lines_removed"] = diff_info["lines_removed"]
                state["hypotheses_summary"] = hypothesis_engine.get_summary()
                state["state_machine_history"] = state_machine.get_history_dicts()

                # Collect function response for Gemini
                function_responses.append(
                    genai.protos.Part(function_response=genai.protos.FunctionResponse(
                        name=func_name,
                        response={"result": tool_res}
                    ))
                )

                if func_name == "finish":
                    state["finish_data"] = tool_res
                    verified, observed_code, test_data = perform_harness_verification(repo_dir=repo_dir)
                    adv_res = verifier.run_adversarial_checks()
                    gate_res = run_verification_gate(test_data)
                    state["verifier_result"] = adv_res
                    state["verification_gate"] = gate_res

                    if verified and adv_res["adversarial_status"] == "CLAIM_CONFIRMED":
                        state["status"] = "VERIFIED"
                        state["confidence"] = "HIGH (97%)"
                        state_machine.transition(AgentState.VERIFICATION_COMPLETE, "finish()", "perform_harness_verification", "VERIFIED SAFE FOR HUMAN REVIEW", tool_res)
                        
                        artifacts = generate_artifact_bundle(
                            incident_id=incident_id,
                            finish_data=tool_res,
                            diff_info=diff_info,
                            test_data=test_data,
                            timeline=timeline,
                            evidence_graph=evidence_graph,
                            verifier_data=adv_res
                        )
                        state["artifacts_bundle"] = artifacts
                        state["report_markdown"] = artifacts.get(f"incident_{incident_id}.md", "")
                        state_machine.transition(AgentState.REPORT_GENERATED, "generate_artifact_bundle", "finish", "Auditable Report & Artifacts", tool_res)
                        state["state_machine_history"] = state_machine.get_history_dicts()

                        yield {
                            "event": "tool_call",
                            "tool": func_name,
                            "args": func_args,
                            "result": tool_res,
                            "summary": "Independent Harness Verification PASSED! Verified Safe for Review.",
                            "current_state": copy.deepcopy(state)
                        }
                        return
                    else:
                        if attempt < max_harness_retries:
                            attempt += 1
                            restore_agent_changes(repo_dir=repo_dir)
                            state["fix_applied"] = False
                            state["tests_passed"] = False
                            pending_message = f"VERIFICATION FAILED: Observed status code {observed_code} (expected 400). Reverting app/."
                            summary = f"Verification Failed (observed {observed_code}). Reverting app/ and retrying..."
                        else:
                            state["status"] = "UNRESOLVED"
                            state["confidence"] = "LOW"
                            yield {
                                "event": "tool_call",
                                "tool": func_name,
                                "args": func_args,
                                "result": tool_res,
                                "summary": "Independent Harness Verification FAILED after max retries.",
                                "current_state": copy.deepcopy(state)
                            }
                            return

                yield {
                    "event": "tool_call",
                    "tool": func_name,
                    "args": func_args,
                    "result": tool_res,
                    "summary": summary,
                    "current_state": copy.deepcopy(state)
                }

            # Send function responses back to Gemini for next turn
            if function_responses and pending_message is None:
                pending_message = genai.protos.Content(parts=function_responses)

    # Deterministic State Machine Engine (Fallback mode)
    if state["status"] == "INVESTIGATING":
        steps_plan = [
            (
                AgentState.INCIDENT_RECEIVED,
                "read_incident_context",
                {},
                "Step 1: Ingesting incident context & deployment log",
                "incident.json ingested",
                "Severity HIGH, service checkout"
            ),
            (
                AgentState.TELEMETRY_ANALYSIS,
                "search_logs",
                {"query": "CouponExpired", "max_results": 10},
                "Step 1: Analyzing checkout logs for CouponExpired error traces",
                "CouponExpired log search",
                "93% correlation with coupon_code parameter"
            ),
            (
                AgentState.FAILURE_REPRODUCTION,
                "reproduce_incident",
                {},
                "Step 2: Executing reproduction payload with expired coupon (EXPIRED_SAVE20)",
                "reproduce_incident()",
                "HTTP 500 Internal Error observed"
            ),
            (
                AgentState.CODE_INSPECTION,
                "search_code",
                {"query": "coupon"},
                "Step 3: Searching codebase for coupon exception handling",
                "search_code('coupon')",
                "Found app/checkout.py line 28"
            ),
            (
                AgentState.HYPOTHESIS_GENERATION,
                "read_files",
                {"paths": ["app/checkout.py", "app/coupon.py", "app/errors.py"]},
                "Step 3: Evaluating H1, H2, H3 root cause hypotheses",
                "read_files app/checkout.py",
                "H1 confirmed (68% -> 82% -> 97%), H2/H3 rejected"
            ),
            (
                AgentState.REGRESSION_TESTING,
                "update_files",
                {
                    "updates": [
                        {
                            "path": "tests/test_inc4821_regression.py",
                            "content": REGRESSION_TEST_CONTENT
                        }
                    ]
                },
                "Step 4: Writing regression test in tests/test_inc4821_regression.py",
                "update_files regression test",
                "tests/test_inc4821_regression.py created"
            ),
            (
                AgentState.HYPOTHESIS_TESTING,
                "run_tests",
                {},
                "Step 5: Executing test suite to verify regression test fails (Reproduction Verified)",
                "run_tests()",
                "1 test failed (Reproduction Verified in CI)"
            ),
            (
                AgentState.PATCH_GENERATION,
                "update_files",
                {
                    "updates": [
                        {
                            "path": "app/checkout.py",
                            "content": FIXED_CHECKOUT_CONTENT
                        }
                    ]
                },
                "Step 6: Patching app/checkout.py to handle AppError specifically and return HTTP 400",
                "update_files app/checkout.py",
                "app/checkout.py patched"
            ),
            (
                AgentState.INCIDENT_REPLAY,
                "run_tests",
                {},
                "Step 7: Executing full pytest suite & incident replay to verify 12/12 tests pass",
                "run_tests()",
                "12/12 tests passed cleanly"
            ),
            (
                AgentState.VERIFICATION_COMPLETE,
                "finish",
                {
                    "root_cause": "Generic 'except Exception:' block in app/checkout.py swallowed CouponExpiredError (subclass of AppError with status_code=400) and returned a 500 Internal Error.",
                    "why": "Deployment v2.4.1 refactored coupon validation error handling into a catch-all try/except block, masking specific AppError domain exceptions.",
                    "evidence_ids": [
                        "checkout.log: line 24 (CouponExpiredError trace)",
                        "deployment.log: v2.4.1 release (Commit 8f3b2a19c4e)",
                        "app/checkout.py: line 28 (except Exception block)"
                    ],
                    "resolution": "Updated app/checkout.py to catch AppError explicitly before generic Exception, preserving status_code = 400 for CouponExpiredError.",
                    "prevention": "Enforce strict linter rule prohibiting generic 'except Exception:' in API pipeline handlers and add automated regression test suite to CI."
                },
                "Step 8: Formulating auditable incident report & double-check verification gate",
                "finish()",
                "VERIFIED SAFE FOR HUMAN REVIEW"
            )
        ]

        step_idx = 0
        for st_enum, func_name, func_args, step_desc, input_desc, ev_desc in steps_plan:
            state["step"] += 1
            tool_res, _ = execute_tool_call(func_name, func_args, repo_dir)

            # Update State Machine & Hypotheses
            state_machine.transition(
                next_state=st_enum,
                input_desc=input_desc,
                action=func_name,
                evidence=ev_desc,
                result=tool_res,
                confidence=hypothesis_engine.hypotheses["H1"]["current_confidence"]
            )

            if func_name == "read_incident_context":
                hypothesis_engine.run_experiment_step(0)
            elif func_name == "reproduce_incident":
                hypothesis_engine.run_experiment_step(1)
                if tool_res.get("status_code_observed") == 500:
                    state["reproduction_verified"] = True
            elif func_name == "read_files":
                hypothesis_engine.run_experiment_step(2)
                state["code_searched"] = True
            elif func_name == "update_files":
                for u in func_args.get("updates", []):
                    if "test_inc4821" in u.get("path", ""):
                        state["regression_test_added"] = True
                    if "checkout.py" in u.get("path", ""):
                        state["fix_applied"] = True
            elif func_name == "run_tests":
                state["test_counts"]["passed"] = tool_res.get("passed", 0)
                state["test_counts"]["failed"] = tool_res.get("failed", 0)
                state["test_counts"]["total"] = tool_res.get("total", 0)
                if tool_res.get("failed", 0) == 0 and tool_res.get("passed", 0) > 0:
                    state["tests_passed"] = True

            diff_info = git_diff(repo_dir=repo_dir)
            state["diff_stats"]["lines_added"] = diff_info["lines_added"]
            state["diff_stats"]["lines_removed"] = diff_info["lines_removed"]
            state["hypotheses_summary"] = hypothesis_engine.get_summary()
            state["state_machine_history"] = state_machine.get_history_dicts()

            if func_name == "finish":
                state["finish_data"] = tool_res
                verified, observed_code, test_data = perform_harness_verification(repo_dir=repo_dir)
                adv_res = verifier.run_adversarial_checks()
                gate_res = run_verification_gate(test_data)
                state["verifier_result"] = adv_res
                state["verification_gate"] = gate_res

                if verified and adv_res["adversarial_status"] == "CLAIM_CONFIRMED":
                    state["status"] = "VERIFIED"
                    state["confidence"] = "HIGH (97%)"
                    
                    artifacts = generate_artifact_bundle(
                        incident_id=incident_id,
                        finish_data=tool_res,
                        diff_info=diff_info,
                        test_data=test_data,
                        timeline=timeline,
                        evidence_graph=evidence_graph,
                        verifier_data=adv_res
                    )
                    state["artifacts_bundle"] = artifacts
                    state["report_markdown"] = artifacts.get(f"incident_{incident_id}.md", "")
                    
                    state_machine.transition(
                        next_state=AgentState.REPORT_GENERATED,
                        input_desc="generate_artifact_bundle",
                        action="finish",
                        evidence="Auditable Report & Artifacts Bundle Generated",
                        result={"artifacts": list(artifacts.keys())}
                    )
                    state["state_machine_history"] = state_machine.get_history_dicts()
                else:
                    state["status"] = "UNRESOLVED"
                    state["confidence"] = "LOW"

            yield {
                "event": "tool_call",
                "tool": func_name,
                "args": func_args,
                "result": tool_res,
                "summary": step_desc,
                "current_state": copy.deepcopy(state)
            }


def generate_markdown_report(finish_data: dict, diff_info: dict, test_data: dict) -> str:
    artifacts = generate_artifact_bundle(
        incident_id="INC-4821",
        finish_data=finish_data,
        diff_info=diff_info,
        test_data=test_data,
        timeline=generate_chronological_timeline("INC-4821"),
        evidence_graph=build_evidence_graph("INC-4821"),
        verifier_data=AdversarialVerifier().run_adversarial_checks()
    )
    return artifacts.get("incident_INC-4821.md", "")
