# Synthetic demo data - not real production data.
"""
Evidence Graph Module for IncidentPilot.
Maps nodes and causal relationships across telemetry, logs, code, experiments, and patches.
"""

from typing import List, Dict, Any


def build_evidence_graph(incident_id: str = "INC-4821") -> Dict[str, Any]:
    nodes = [
        {
            "id": "node_deploy",
            "label": "Deployment v2.4.1",
            "type": "DEPLOYMENT",
            "source": "logs/deployment.log",
            "detail": "Commit 8f3b2a19c4e refactored coupon integration"
        },
        {
            "id": "node_log_trace",
            "label": "CouponExpiredError Trace",
            "type": "LOG",
            "source": "logs/checkout.log: L24",
            "detail": "req_err001: app.errors.CouponExpiredError ('Coupon EXPIRED_SAVE20 expired')"
        },
        {
            "id": "node_code_bug",
            "label": "Catch-all except Exception",
            "type": "CODE",
            "source": "app/checkout.py: L28",
            "detail": "except Exception as e: return {'status': 500} (swallows AppError 400)"
        },
        {
            "id": "node_repro",
            "label": "Reproduction Observed (500)",
            "type": "EXPERIMENT",
            "source": "reproduce_incident()",
            "detail": "Payload with EXPIRED_SAVE20 reproduced HTTP 500 Internal Error"
        },
        {
            "id": "node_patch",
            "label": "Targeted AppError Patch",
            "type": "PATCH",
            "source": "git diff app/checkout.py",
            "detail": "except AppError as e: return {'status': e.status_code, 'error': 'Bad Request'}"
        },
        {
            "id": "node_verification",
            "label": "Double-Check Verification Gate",
            "type": "TEST",
            "source": "pytest -q --tb=short",
            "detail": "12/12 tests passed cleanly (including tests/test_inc4821_regression.py)"
        }
    ]

    edges = [
        {"from": "node_deploy", "to": "node_code_bug", "label": "introduced"},
        {"from": "node_code_bug", "to": "node_log_trace", "label": "emitted error"},
        {"from": "node_log_trace", "to": "node_repro", "label": "correlated payload"},
        {"from": "node_repro", "to": "node_patch", "label": "isolated fix"},
        {"from": "node_patch", "to": "node_verification", "label": "verified by"}
    ]

    return {
        "incident_id": incident_id,
        "nodes": nodes,
        "edges": edges,
        "total_nodes": len(nodes),
        "total_edges": len(edges)
    }
