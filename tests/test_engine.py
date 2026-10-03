# Synthetic demo data - not real production data.
"""
Engine Unit Tests for IncidentPilot Core Modules.
"""

import os
import sys
import pytest

# Ensure incidentpilot root is on sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from data.incidents import get_incident_scenario, INCIDENTS_CATALOG
from data.telemetry import generate_telemetry_series, generate_chronological_timeline
from core.state_machine import IncidentStateMachine, AgentState
from core.hypotheses import HypothesisEngine
from core.evidence import build_evidence_graph
from core.experiments import run_counterfactual_experiment
from core.verifier import AdversarialVerifier, run_verification_gate
from core.artifact_generator import generate_artifact_bundle
from tools import run_tests, reproduce_incident, DEFAULT_REPO_DIR


def test_incident_loading():
    sc = get_incident_scenario("INC-4821")
    assert sc["incident_id"] == "INC-4821"
    assert sc["service"] == "checkout"
    assert len(sc["hypotheses"]) == 3
    assert len(INCIDENTS_CATALOG) >= 3


def test_hypothesis_generation():
    engine = HypothesisEngine("INC-4821")
    summary = engine.get_summary()
    assert len(summary["hypotheses"]) == 3
    assert summary["winning_hypothesis"]["id"] == "H1"
    
    # Step experiments
    exp1 = engine.run_experiment_step(0)
    exp2 = engine.run_experiment_step(1)
    exp3 = engine.run_experiment_step(2)
    assert engine.hypotheses["H1"]["status"] == "CONFIRMED"
    assert engine.hypotheses["H1"]["current_confidence"] == 0.97


def test_reproduction():
    res = reproduce_incident(repo_dir=DEFAULT_REPO_DIR)
    assert "status_code_observed" in res
    assert res["status_code_observed"] in [400, 500]


def test_root_cause_confirmation():
    graph = build_evidence_graph("INC-4821")
    assert graph["total_nodes"] >= 5
    assert any(n["type"] == "CODE" for n in graph["nodes"])


def test_patch_generation():
    exp = run_counterfactual_experiment()
    assert exp["counterfactual_proven"] is True
    assert exp["before_patch"]["status_code"] == 500
    assert exp["after_patch"]["status_code"] == 400


def test_regression_verification():
    v = AdversarialVerifier(repo_dir=DEFAULT_REPO_DIR)
    res = v.run_adversarial_checks()
    assert res["adversarial_status"] == "CLAIM_CONFIRMED"
    assert res["checks_passed"] == 5


def test_incident_replay():
    gate = run_verification_gate({"passed": 12, "failed": 0})
    assert gate["gate_status"] == "VERIFIED SAFE FOR HUMAN REVIEW"
    assert gate["human_review_required"] is True
    assert gate["auto_deploy_permitted"] is False


def test_artifact_generation():
    artifacts = generate_artifact_bundle(
        incident_id="INC-4821",
        finish_data={"root_cause": "Test root cause", "why": "Test why", "evidence_ids": ["test.log:1"], "resolution": "Fix", "prevention": "Rule"},
        diff_info={"diff_text": "diff --git", "lines_added": 2, "lines_removed": 1},
        test_data={"passed": 12, "failed": 0, "total": 12},
        timeline=[{"time": "21:30:00Z", "event": "Deploy"}],
        evidence_graph={"nodes": [], "edges": []},
        verifier_data={"status": "CONFIRMED"}
    )
    assert "incident_INC-4821.md" in artifacts
    assert "evidence_INC-4821.json" in artifacts
    assert "patch_INC-4821.diff" in artifacts
    assert "verification_INC-4821.json" in artifacts
    assert "timeline_INC-4821.json" in artifacts
