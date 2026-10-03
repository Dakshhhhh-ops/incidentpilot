# Synthetic demo data - not real production data.
"""
Incident Catalog defining deterministic incident scenarios for IncidentPilot.
"""

INCIDENTS_CATALOG = {
    "INC-4821": {
        "incident_id": "INC-4821",
        "title": "Checkout API elevated 500 errors",
        "service": "checkout",
        "severity": "HIGH",
        "deployment": "v2.4.1",
        "started_at": "2026-10-03T21:41:00Z",
        "description": "Checkout API error rate increased from 0.8% to 31.4% following deployment v2.4.1. Requests with expired coupons return HTTP 500 instead of a controlled 400 response.",
        "affected_endpoint": "/v1/checkout",
        "error_rate_before": "0.8%",
        "error_rate_after": "31.4%",
        "failing_correlation": "93% of failing requests contain coupon_code",
        "primary_file": "app/checkout.py",
        "buggy_line_num": 28,
        "buggy_code_snippet": "except Exception as e:\n    return {\"status\": 500, \"error\": \"Internal Error\", \"message\": f\"Coupon validation failed: {str(e)}\"}",
        "why_tests_missed": "Existing unit tests covered valid coupons and missing fields, but omitted testing expired coupons against the process_checkout endpoint after exception handling refactoring in v2.4.1.",
        "hypotheses": [
            {
                "id": "H1",
                "name": "Coupon Validation Exception Handler Bug",
                "description": "Deployment v2.4.1 introduced a generic 'except Exception:' block in app/checkout.py that catches CouponExpiredError (AppError with status 400) and converts it to HTTP 500.",
                "initial_confidence": 0.68,
                "final_confidence": 0.97,
                "status": "CONFIRMED"
            },
            {
                "id": "H2",
                "name": "Database Connection Pool Exhaustion",
                "description": "Postgres primary database connection pool exhausted during peak checkout traffic causing unhandled DB timeout exceptions.",
                "initial_confidence": 0.21,
                "final_confidence": 0.02,
                "status": "REJECTED"
            },
            {
                "id": "H3",
                "name": "External Payment Gateway Timeout",
                "description": "Third-party payment provider API latency spike causing checkout request handler timeouts.",
                "initial_confidence": 0.11,
                "final_confidence": 0.01,
                "status": "REJECTED"
            }
        ]
    },
    "INC-7392": {
        "incident_id": "INC-7392",
        "title": "Search API latency degradation (p99 > 4.2s)",
        "service": "search",
        "severity": "MEDIUM",
        "deployment": "v1.8.2",
        "started_at": "2026-10-03T19:15:00Z",
        "description": "Search p99 latency spiked from 120ms to 4200ms following deployment v1.8.2. Cache miss path triggers unindexed database scans.",
        "affected_endpoint": "/v1/search",
        "error_rate_before": "0.1%",
        "error_rate_after": "4.2%",
        "failing_correlation": "100% of high latency queries lack cache-control header",
        "primary_file": "app/search.py",
        "buggy_line_num": 42,
        "buggy_code_snippet": "results = db.query(f'SELECT * FROM products WHERE description LIKE %{query}%')",
        "why_tests_missed": "Staging test environment had a small product dataset (500 items) where full table scan executed in <5ms.",
        "hypotheses": [
            {
                "id": "H1",
                "name": "Unindexed Fallback Query on Cache Miss",
                "description": "v1.8.2 cache miss fallback executes unindexed LIKE wildcard search on 1M row product table.",
                "initial_confidence": 0.72,
                "final_confidence": 0.96,
                "status": "CONFIRMED"
            },
            {
                "id": "H2",
                "name": "Redis Cache Cluster Memory Pressure",
                "description": "Redis evicted search keys due to maxmemory limit reached.",
                "initial_confidence": 0.18,
                "final_confidence": 0.03,
                "status": "REJECTED"
            },
            {
                "id": "H3",
                "name": "ElasticSearch Cluster Shard Rebalancing",
                "description": "Background reindexing during peak traffic causing queue delay.",
                "initial_confidence": 0.10,
                "final_confidence": 0.01,
                "status": "REJECTED"
            }
        ]
    },
    "INC-9104": {
        "incident_id": "INC-9104",
        "title": "Auth Service elevated HTTP 401 token rejection",
        "service": "auth",
        "severity": "HIGH",
        "deployment": "v3.1.0",
        "started_at": "2026-10-03T20:05:00Z",
        "description": "Valid session tokens issued within 60 seconds are rejected with 401 Unauthorized due to clock drift boundary calculation error.",
        "affected_endpoint": "/v1/auth/verify",
        "error_rate_before": "0.05%",
        "error_rate_after": "18.2%",
        "failing_correlation": "100% of failing tokens issued within last 60 seconds",
        "primary_file": "app/auth.py",
        "buggy_line_num": 19,
        "buggy_code_snippet": "if token.issued_at > current_time:\n    raise TokenInvalidError('Token issued in future')",
        "why_tests_missed": "Unit tests executed with mock fixed system time without simulating 1-second clock skew between server nodes.",
        "hypotheses": [
            {
                "id": "H1",
                "name": "Clock Skew Boundary Exception",
                "description": "Strict token timestamp validation fails when token issued_at is 1-2 seconds ahead due to NTP clock drift.",
                "initial_confidence": 0.75,
                "final_confidence": 0.98,
                "status": "CONFIRMED"
            },
            {
                "id": "H2",
                "name": "JWT Secret Key Mismatch",
                "description": "Rolling deployment nodes loaded different JWT signing secret keys.",
                "initial_confidence": 0.15,
                "final_confidence": 0.01,
                "status": "REJECTED"
            },
            {
                "id": "H3",
                "name": "Token Revocation DB Timeout",
                "description": "Blacklist database query timing out on token verification.",
                "initial_confidence": 0.10,
                "final_confidence": 0.01,
                "status": "REJECTED"
            }
        ]
    }
}


def get_incident_scenario(incident_id: str = "INC-4821") -> dict:
    return INCIDENTS_CATALOG.get(incident_id, INCIDENTS_CATALOG["INC-4821"])
