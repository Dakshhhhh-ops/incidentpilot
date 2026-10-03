# Synthetic demo data - not real production data.
import time
from enum import Enum
from typing import List, Dict, Any


class AgentState(str, Enum):
    INCIDENT_RECEIVED = "INCIDENT_RECEIVED"
    TELEMETRY_ANALYSIS = "TELEMETRY_ANALYSIS"
    LOG_CORRELATION = "LOG_CORRELATION"
    CODE_INSPECTION = "CODE_INSPECTION"
    HYPOTHESIS_GENERATION = "HYPOTHESIS_GENERATION"
    HYPOTHESIS_TESTING = "HYPOTHESIS_TESTING"
    FAILURE_REPRODUCTION = "FAILURE_REPRODUCTION"
    ROOT_CAUSE_CONFIRMED = "ROOT_CAUSE_CONFIRMED"
    PATCH_GENERATION = "PATCH_GENERATION"
    REGRESSION_TESTING = "REGRESSION_TESTING"
    INCIDENT_REPLAY = "INCIDENT_REPLAY"
    VERIFICATION_COMPLETE = "VERIFICATION_COMPLETE"
    REPORT_GENERATED = "REPORT_GENERATED"


STATE_DESCRIPTIONS = {
    AgentState.INCIDENT_RECEIVED: "Ingesting incident notification & telemetry context",
    AgentState.TELEMETRY_ANALYSIS: "Analyzing error rate trends and latency metrics",
    AgentState.LOG_CORRELATION: "Correlating log error patterns and request parameters",
    AgentState.CODE_INSPECTION: "Inspecting modified source files from deployment v2.4.1",
    AgentState.HYPOTHESIS_GENERATION: "Formulating multi-hypothesis root cause candidates (H1, H2, H3)",
    AgentState.HYPOTHESIS_TESTING: "Executing targeted isolation experiments to evaluate hypotheses",
    AgentState.FAILURE_REPRODUCTION: "Reproducing original production failure payload in sandbox",
    AgentState.ROOT_CAUSE_CONFIRMED: "Confirming root cause with empirical trace & error evidence",
    AgentState.PATCH_GENERATION: "Generating minimal targeted code patch with risk analysis",
    AgentState.REGRESSION_TESTING: "Executing new regression test and existing test suite",
    AgentState.INCIDENT_REPLAY: "Replaying failing request against patched code",
    AgentState.VERIFICATION_COMPLETE: "Double-check verification & adversarial verifier gate PASSED",
    AgentState.REPORT_GENERATED: "Generating auditable markdown report & JSON post-mortem brief"
}


class StateTransition:
    def __init__(self, state: AgentState, input_desc: str, action: str, evidence: str, result: Dict[str, Any], confidence: Dict[str, float] = None):
        self.state = state.value
        self.description = STATE_DESCRIPTIONS.get(state, "")
        self.input = input_desc
        self.action = action
        self.evidence = evidence
        self.result = result
        self.timestamp = time.strftime("%H:%M:%S")
        self.confidence = confidence or {"H1": 0.0, "H2": 0.0, "H3": 0.0}
        self.status = "SUCCESS"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "state": self.state,
            "description": self.description,
            "input": self.input,
            "action": self.action,
            "evidence": self.evidence,
            "result": self.result,
            "timestamp": self.timestamp,
            "confidence": self.confidence,
            "status": self.status
        }


class IncidentStateMachine:
    def __init__(self, incident_id: str = "INC-4821"):
        self.incident_id = incident_id
        self.current_state = AgentState.INCIDENT_RECEIVED
        self.history: List[StateTransition] = []

    def transition(self, next_state: AgentState, input_desc: str, action: str, evidence: str, result: Dict[str, Any], confidence: Dict[str, float] = None) -> StateTransition:
        self.current_state = next_state
        trans = StateTransition(
            state=next_state,
            input_desc=input_desc,
            action=action,
            evidence=evidence,
            result=result,
            confidence=confidence
        )
        self.history.append(trans)
        return trans

    def get_history_dicts(self) -> List[Dict[str, Any]]:
        return [t.to_dict() for t in self.history]
