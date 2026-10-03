# Synthetic demo data - not real production data.
"""
Telemetry and Log Analysis Module for IncidentPilot.
Provides metric series, log event extraction, and timeline generation.
"""

def generate_telemetry_series(incident_id: str = "INC-4821") -> dict:
    """Generates time-series metric data points showing error rate spike."""
    timestamps = [
        "21:30:00", "21:32:00", "21:34:00", "21:36:00", "21:38:00",
        "21:40:00", "21:41:00", "21:42:00", "21:44:00", "21:46:00",
        "21:48:00", "21:50:00", "21:52:00", "21:54:00", "21:56:00"
    ]
    
    # Error rate baseline ~0.8%, spikes to ~31.4% at 21:41 deployment window
    error_rates = [0.8, 0.7, 0.8, 0.9, 0.8, 1.0, 14.2, 28.5, 31.4, 30.8, 31.2, 31.4, 30.9, 31.5, 31.4]
    latency_p95_ms = [35, 38, 34, 36, 37, 40, 68, 110, 125, 118, 122, 124, 120, 126, 125]
    
    return {
        "incident_id": incident_id,
        "timestamps": timestamps,
        "error_rates_pct": error_rates,
        "latency_p95_ms": latency_p95_ms,
        "baseline_error_rate": 0.8,
        "peak_error_rate": 31.4
    }


def generate_chronological_timeline(incident_id: str = "INC-4821") -> list:
    """Returns chronological incident event timeline."""
    return [
        {"time": "21:30:00Z", "event": "Deployment v2.4.1 initialized", "type": "DEPLOYMENT", "details": "Commit 8f3b2a19c4e deployed by release-bot"},
        {"time": "21:30:10Z", "event": "Rolling restart complete (Node us-east-1a)", "type": "SYSTEM", "details": "All pods updated to v2.4.1"},
        {"time": "21:40:00Z", "event": "First traffic routed to v2.4.1 pipeline", "type": "TRAFFIC", "details": "HTTP 200 OK baseline checkouts passing"},
        {"time": "21:41:02Z", "event": "First HTTP 500 error burst detected", "type": "ALERT", "details": "Request req_err001 failed with CouponExpiredError trace"},
        {"time": "21:45:00Z", "event": "Alert Manager triggered: Elevated 500 threshold exceeded", "type": "ALERT", "details": "Error rate reached 31.4% on /v1/checkout"},
        {"time": "21:46:00Z", "event": "Incident INC-4821 created & assigned to IncidentPilot", "type": "INCIDENT", "details": "IncidentPilot autonomous agent initialized"},
        {"time": "21:46:02Z", "event": "Telemetry analysis & Log correlation completed", "type": "AGENT", "details": "Isolated 93% correlation with coupon_code parameter"},
        {"time": "21:46:05Z", "event": "Failure reproduction confirmed (HTTP 500 observed)", "type": "AGENT", "details": "Payload EXPIRED_SAVE20 reproduced 500 Internal Error"},
        {"time": "21:46:10Z", "event": "Root cause confirmed in app/checkout.py", "type": "AGENT", "details": "Generic except block caught CouponExpiredError (AppError)"},
        {"time": "21:46:15Z", "event": "Regression test created & minimal patch applied", "type": "AGENT", "details": "Updated app/checkout.py to catch AppError specifically"},
        {"time": "21:46:20Z", "event": "Double-verification gate completed (12/12 Tests Pass)", "type": "AGENT", "details": "Incident replay HTTP 400 Bad Request verified"},
        {"time": "21:46:25Z", "event": "Auditable incident report & patch recommended for review", "type": "COMPLETE", "details": "Status: VERIFIED SAFE FOR HUMAN REVIEW"}
    ]
