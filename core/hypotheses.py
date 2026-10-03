# Synthetic demo data - not real production data.
"""
Multi-Hypothesis Engine for IncidentPilot.
Generates competing root cause hypotheses and tracks confidence evolution.
"""

from typing import List, Dict, Any


class HypothesisEngine:
    def __init__(self, incident_id: str = "INC-4821"):
        self.incident_id = incident_id
        self.hypotheses = {
            "H1": {
                "id": "H1",
                "title": "Coupon Validation Exception Handler Regression",
                "statement": "Deployment v2.4.1 introduced a generic 'except Exception:' block in app/checkout.py that catches CouponExpiredError (AppError with status 400) and converts it to HTTP 500.",
                "confidence_trajectory": [0.68, 0.82, 0.97],
                "current_confidence": 0.68,
                "status": "EVALUATING"
            },
            "H2": {
                "id": "H2",
                "title": "Database Connection Pool Exhaustion",
                "statement": "Primary Postgres database connection pool exhausted during peak checkout traffic causing unhandled DB timeout exceptions.",
                "confidence_trajectory": [0.21, 0.12, 0.02],
                "current_confidence": 0.21,
                "status": "EVALUATING"
            },
            "H3": {
                "id": "H3",
                "title": "External Payment Gateway Timeout",
                "statement": "Third-party payment provider API endpoint latency spike causing checkout request handler timeouts.",
                "confidence_trajectory": [0.11, 0.06, 0.01],
                "current_confidence": 0.11,
                "status": "EVALUATING"
            }
        }
        self.experiments = []

    def run_experiment_step(self, step_index: int) -> Dict[str, Any]:
        """
        Executes a deterministic experiment step and updates hypothesis confidence scores.
        step_index: 0 (Initial), 1 (After No-Coupon vs Coupon replay), 2 (After Code Inspection & Error Trace)
        """
        if step_index == 0:
            exp = {
                "step": 1,
                "name": "Log Correlation Signal Analysis",
                "finding": "93% of failing HTTP 500 requests contain a 'coupon' payload parameter.",
                "confidence_snapshot": {"H1": 0.68, "H2": 0.21, "H3": 0.11}
            }
        elif step_index == 1:
            self.hypotheses["H1"]["current_confidence"] = 0.82
            self.hypotheses["H2"]["current_confidence"] = 0.12
            self.hypotheses["H3"]["current_confidence"] = 0.06
            exp = {
                "step": 2,
                "name": "Targeted Payload Differential Replay",
                "finding": "Replay WITHOUT coupon -> PASS (200 OK). Replay WITH expired coupon ('EXPIRED_SAVE20') -> FAIL (500 Internal Error). DB latency normal (2ms). Payment gateway responsive.",
                "confidence_snapshot": {"H1": 0.82, "H2": 0.12, "H3": 0.06}
            }
        else:
            self.hypotheses["H1"]["current_confidence"] = 0.97
            self.hypotheses["H1"]["status"] = "CONFIRMED"
            self.hypotheses["H2"]["current_confidence"] = 0.02
            self.hypotheses["H2"]["status"] = "REJECTED"
            self.hypotheses["H3"]["current_confidence"] = 0.01
            self.hypotheses["H3"]["status"] = "REJECTED"
            exp = {
                "step": 3,
                "name": "Source Code Exception Handler Inspection",
                "finding": "Confirmed: app/checkout.py line 28 catches Exception generally. Swallows CouponExpiredError status_code=400 and returns status=500.",
                "confidence_snapshot": {"H1": 0.97, "H2": 0.02, "H3": 0.01}
            }
        
        self.experiments.append(exp)
        return exp

    def get_summary(self) -> Dict[str, Any]:
        return {
            "hypotheses": list(self.hypotheses.values()),
            "experiments": self.experiments,
            "winning_hypothesis": self.hypotheses["H1"]
        }
