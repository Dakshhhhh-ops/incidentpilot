# Synthetic demo data - not real production data.
import os
import sys
import json
import asyncio
from dotenv import load_dotenv

load_dotenv()
from fastapi import FastAPI, Query, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, JSONResponse, PlainTextResponse, FileResponse
from fastapi.staticfiles import StaticFiles

# Ensure local imports work
sys.path.insert(0, os.path.dirname(__file__))

from agent import run_incident_agent
from tools import (
    git_diff,
    restore_agent_changes,
    search_logs,
    read_log,
    read_incident_context,
    run_tests,
    reproduce_incident,
    DEFAULT_REPO_DIR
)
from data.incidents import get_incident_scenario, INCIDENTS_CATALOG
from data.telemetry import generate_telemetry_series, generate_chronological_timeline
from core.state_machine import AgentState
from core.evidence import build_evidence_graph
from core.experiments import run_counterfactual_experiment
from core.verifier import AdversarialVerifier, run_verification_gate
from core.artifact_generator import generate_artifact_bundle
from run_cli import reset_environment

app = FastAPI(title="IncidentPilot SRE Command Center", version="2.0.0")

# Enable CORS for React Frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

repo_dir = DEFAULT_REPO_DIR
server_state = {
    "human_approved": False,
    "last_investigation_state": None
}


@app.get("/api/health")
def health_check():
    return {"status": "OK", "service": "IncidentPilot Backend API", "version": "2.0.0"}


@app.post("/api/config")
async def update_config(request: Request):
    data = await request.json()
    api_key = data.get("api_key", "").strip()
    model = data.get("model", "").strip()
    base_url = data.get("base_url", "").strip()
    
    if api_key:
        os.environ["LLM_API_KEY"] = api_key
        os.environ["OPENAI_API_KEY"] = api_key
    if model:
        os.environ["LLM_MODEL"] = model
    if base_url:
        os.environ["LLM_BASE_URL"] = base_url
        os.environ["OPENAI_BASE_URL"] = base_url
        
    return {
        "status": "SUCCESS",
        "llm_mode": "Live OpenAI/LLM Model" if (os.environ.get("LLM_API_KEY") or os.environ.get("OPENAI_API_KEY")) else "Autonomous Harness Engine",
        "model": os.environ.get("LLM_MODEL", "gpt-4o"),
        "has_key": bool(os.environ.get("LLM_API_KEY") or os.environ.get("OPENAI_API_KEY"))
    }


@app.get("/api/scenarios")
def get_scenarios():
    return {"scenarios": list(INCIDENTS_CATALOG.values())}


@app.get("/api/status")
def get_status(incident_id: str = "INC-4821"):
    scenario = get_incident_scenario(incident_id)
    diff_data = git_diff(repo_dir=repo_dir)
    api_key_env = os.environ.get("LLM_API_KEY") or os.environ.get("OPENAI_API_KEY")
    
    return {
        "incident_id": incident_id,
        "scenario": scenario,
        "diff_stats": {"lines_added": diff_data["lines_added"], "lines_removed": diff_data["lines_removed"]},
        "llm_mode": "OpenAI API Model" if api_key_env else "Autonomous Harness Engine",
        "human_approved": server_state["human_approved"],
        "last_state": server_state["last_investigation_state"]
    }


@app.get("/api/telemetry")
def get_telemetry(incident_id: str = "INC-4821", query: str = "CouponExpired"):
    series = generate_telemetry_series(incident_id)
    timeline = generate_chronological_timeline(incident_id)
    log_results = search_logs(query=query, repo_dir=repo_dir)
    inc_context = read_incident_context(repo_dir=repo_dir)
    
    return {
        "series": series,
        "timeline": timeline,
        "log_search": log_results[:15],
        "incident_context": inc_context
    }


@app.get("/api/diff")
def get_diff():
    diff_data = git_diff(repo_dir=repo_dir)
    return diff_data


@app.post("/api/run-tests")
def run_pytest():
    res = run_tests(repo_dir=repo_dir)
    return res


@app.post("/api/reset")
def reset_repo():
    reset_environment(repo_dir=repo_dir)
    server_state["human_approved"] = False
    server_state["last_investigation_state"] = None
    return {"status": "SUCCESS", "message": "Demo repository reset to v2.4.1 baseline"}


@app.post("/api/approve")
def approve_patch():
    server_state["human_approved"] = True
    return {"status": "SUCCESS", "message": "Patch approved by engineer for peer review"}


@app.get("/api/artifacts")
def get_artifacts(incident_id: str = "INC-4821"):
    diff_info = git_diff(repo_dir=repo_dir)
    tests_res = run_tests(repo_dir=repo_dir)
    verifier = AdversarialVerifier(repo_dir=repo_dir)
    adv_res = verifier.run_adversarial_checks()
    
    finish_data = {
        "root_cause": "Generic 'except Exception:' block in app/checkout.py swallowed CouponExpiredError (subclass of AppError with status_code=400) and returned a 500 Internal Error.",
        "why": "Deployment v2.4.1 refactored coupon validation error handling into a catch-all try/except block, masking specific AppError domain exceptions.",
        "evidence_ids": [
            "checkout.log: line 24 (CouponExpiredError trace)",
            "deployment.log: v2.4.1 release (Commit 8f3b2a19c4e)",
            "app/checkout.py: line 28 (except Exception block)"
        ],
        "resolution": "Updated app/checkout.py to catch AppError explicitly before generic Exception, preserving status_code = 400 for CouponExpiredError.",
        "prevention": "Enforce strict linter rule prohibiting generic 'except Exception:' in API pipeline handlers and add automated regression test suite to CI."
    }

    bundle = generate_artifact_bundle(
        incident_id=incident_id,
        finish_data=finish_data,
        diff_info=diff_info,
        test_data=tests_res,
        timeline=generate_chronological_timeline(incident_id),
        evidence_graph=build_evidence_graph(incident_id),
        verifier_data=adv_res
    )
    return {"incident_id": incident_id, "artifacts": bundle}


@app.get("/api/investigate/stream")
async def stream_investigation(incident_id: str = "INC-4821", delay: float = 0.2):
    """
    Streams investigation events as Server-Sent Events (SSE).
    """
    async def event_generator():
        gen = run_incident_agent(repo_dir=repo_dir, incident_id=incident_id)
        for event_data in gen:
            server_state["last_investigation_state"] = event_data.get("current_state")
            json_str = json.dumps(event_data)
            yield f"data: {json_str}\n\n"
            if delay > 0:
                await asyncio.sleep(delay)
        yield "data: [DONE]\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")


# Mount React Production Build Static Files
frontend_dist = os.path.abspath(os.path.join(os.path.dirname(__file__), "frontend", "dist"))

if os.path.exists(frontend_dist):
    assets_dir = os.path.join(frontend_dist, "assets")
    if os.path.exists(assets_dir):
        app.mount("/assets", StaticFiles(directory=assets_dir), name="assets")

    @app.get("/")
    async def serve_index():
        index_file = os.path.join(frontend_dist, "index.html")
        return FileResponse(index_file)

    @app.get("/{full_path:path}")
    async def serve_fallback(full_path: str):
        if full_path.startswith("api") or full_path.startswith("assets"):
            raise HTTPException(status_code=404, detail="Not found")
        index_file = os.path.join(frontend_dist, "index.html")
        if os.path.exists(index_file):
            return FileResponse(index_file)
        raise HTTPException(status_code=404, detail="Index file not found")


if __name__ == "__main__":
    import uvicorn
    print("\n" + "=" * 70)
    print(" INCIDENTPILOT SRE COMMAND CENTER READY!")
    print(" Open in Browser: http://localhost:8000")
    print("=" * 70 + "\n")
    uvicorn.run(app, host="127.0.0.1", port=8000)
