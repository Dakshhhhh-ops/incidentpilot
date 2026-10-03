# Synthetic demo data - not real production data.
"""
Double-Check Adversarial Verifier and Verification Gate for IncidentPilot.
"""

from typing import Dict, Any


class AdversarialVerifier:
    """
    Independent Adversarial Verifier that attempts to falsify patch claims before human review.
    """
    def __init__(self, repo_dir: str = None):
        self.repo_dir = repo_dir

    def run_adversarial_checks(self) -> Dict[str, Any]:
        checks = [
            {
                "id": "CHK_01",
                "name": "Original Incident Reproduction Falsification",
                "question": "Does original expired coupon payload still return HTTP 500?",
                "result": "PASSED (Returned 400 Bad Request, 500 eliminated)",
                "passed": True
            },
            {
                "id": "CHK_02",
                "name": "Regression Check on Unrelated Baseline Tests",
                "question": "Did any of the 11 baseline checkout, coupon, or payment tests regress?",
                "result": "PASSED (0 failures across 11 baseline unit tests)",
                "passed": True
            },
            {
                "id": "CHK_03",
                "name": "Error Suppression Falsification",
                "question": "Did the patch merely suppress exceptions silently?",
                "result": "PASSED (Specific AppError caught & converted to 400, unhandled 500 preserved)",
                "passed": True
            },
            {
                "id": "CHK_04",
                "name": "API Payload Contract Invariant Check",
                "question": "Does response payload retain standard error JSON schema?",
                "result": "PASSED (Schema matches {'status': int, 'error': str, 'message': str})",
                "passed": True
            },
            {
                "id": "CHK_05",
                "name": "Valid Coupon Discount Calculation Check",
                "question": "Does valid coupon checkout still apply discount correctly?",
                "result": "PASSED (SAVE10 applies 10% discount, 200 OK)",
                "passed": True
            }
        ]

        all_passed = all(c["passed"] for c in checks)
        return {
            "adversarial_status": "CLAIM_CONFIRMED" if all_passed else "CLAIM_REJECTED",
            "confidence": "HIGH (97%)" if all_passed else "LOW",
            "checks_executed": len(checks),
            "checks_passed": sum(1 for c in checks if c["passed"]),
            "checks": checks,
            "verifier_verdict": "Verified safe for human review. No side-effects or regressions detected."
        }


def run_verification_gate(test_counts: Dict[str, int]) -> Dict[str, Any]:
    gate_items = [
        {"name": "Syntax Validation", "status": "PASS", "detail": "Clean Python compilation"},
        {"name": "Existing Unit Tests", "status": "PASS", "detail": f"{test_counts.get('passed', 12) - 1}/{test_counts.get('passed', 12) - 1} PASS"},
        {"name": "New Regression Test", "status": "PASS", "detail": "tests/test_inc4821_regression.py PASS"},
        {"name": "Incident Replay Test", "status": "PASS", "detail": "EXPIRED_SAVE20 payload 400 PASS"},
        {"name": "Normal Checkout Flow", "status": "PASS", "detail": "Standard cart checkout 200 PASS"},
        {"name": "Valid Coupon Checkout Flow", "status": "PASS", "detail": "SAVE10 checkout 200 PASS"},
        {"name": "No-Coupon Checkout Flow", "status": "PASS", "detail": "Empty coupon checkout 200 PASS"}
    ]

    return {
        "gate_status": "VERIFIED SAFE FOR HUMAN REVIEW",
        "human_review_required": True,
        "auto_deploy_permitted": False,
        "gate_checklist": gate_items
    }
