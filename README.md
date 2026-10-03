# IncidentPilot

An autonomous SRE agent that converts production incidents into a verified, evidence-backed recovery workflow.

IncidentPilot ingests telemetry, correlates logs and traces, evaluates competing hypotheses, reproduces the bug in a controlled environment, confirms the root cause, generates a minimal fix, and verifies the result before it is considered safe for human review.

This project is designed as a demo-ready incident response system for modern engineering teams, combining:

- Python backend logic
- FastAPI API layer
- React + Vite frontend dashboard
- Isolated demo repository for incident reproduction
- Deterministic verification and artifact generation

## Why this project exists

The typical incident workflow is fragmented:

- monitoring tells you something is failing
- logs show partial context
- engineers guess at the cause
- patches are proposed without proof
- verification is inconsistent

IncidentPilot closes that gap by building an operational chain of evidence:

Telemetry -> Evidence Correlation -> Hypothesis Testing -> Failure Reproduction -> Root Cause Proof -> Patch -> Verification -> Incident Report

## Live demo

Local app URL:

- http://localhost:8000

## Architecture

```text
IncidentPilot
├── backend (FastAPI server)
│   ├── API routes for telemetry, artifact generation, status, and review
│   └── orchestrates the investigation workflow
├── frontend (React + Vite dashboard)
│   ├── incident timeline
│   ├── live investigation stream
│   ├── status indicators
│   └── artifact export views
├── core engine
│   ├── state_machine.py
│   ├── hypotheses.py
│   ├── evidence.py
│   ├── experiments.py
│   ├── verifier.py
│   └── artifact_generator.py
├── demo-repo
│   └── isolated app used to simulate and test real incident behavior
├── data
│   ├── __init__.py
│   ├── incidents.py
│   └── telemetry.py
├── tests
│   └── engine and regression checks
└── tools.py
```

## Key features

- Multi-hypothesis investigation
- Evidence graph mapping
- Counterfactual failure reproduction
- Root cause confirmation workflow
- Minimal patch generation
- Adversarial verification gate
- Artifact generation for audit trail
- Synthetic incident scenarios for demos

## Current demo incident

The default scenario is `INC-4821`, a checkout incident caused by expired coupon handling.

The system demonstrates how:

- expired coupon payloads return HTTP 500 unexpectedly
- generic exception handling masks a domain-specific `AppError`
- reproduction confirms the root cause
- a minimal fix restores expected 400 error semantics
- regression validation confirms the fix is safe

## Tech stack

- Python 3.10+
- FastAPI
- React 19
- Vite
- Pytest
- Python-dotenv

## Project structure

```text
incidentpilot/
├── .env.example
├── .gitignore
├── README.md
├── agent.py
├── requirements.txt
├── run_cli.py
├── server.py
├── smoke_test.py
├── tools.py
├── core/
│   ├── __init__.py
│   ├── artifact_generator.py
│   ├── evidence.py
│   ├── experiments.py
│   ├── hypotheses.py
│   ├── state_machine.py
│   └── verifier.py
├── data/
│   ├── __init__.py
│   ├── incidents.py
│   └── telemetry.py
├── demo-repo/
│   ├── app/
│   ├── incident/
│   ├── logs/
│   └── tests/
├── frontend/
│   ├── package.json
│   ├── vite.config.js
│   ├── index.html
│   └── src/
├── tests/
│   ├── __init__.py
│   └── test_engine.py
└── .env
```

## Setup

1. Clone the repo

```bash
git clone https://github.com/Dakshhhhh-ops/incidentpilot.git
cd incidentpilot
```

2. Create a virtual environment

```bash
python -m venv .venv
```

On Windows:

```bash
.venv\Scripts\activate
```

On macOS/Linux:

```bash
source .venv/bin/activate
```

3. Install dependencies

```bash
pip install -r requirements.txt
```

4. Optional environment configuration

Copy the example config and fill in LLM keys if you want to use live-model-backed investigation.

```bash
copy .env.example .env
```

Then edit `.env`:

```env
LLM_API_KEY=
OPENAI_API_KEY=
LLM_MODEL=gpt-4o
LLM_BASE_URL=
```

5. Install frontend dependencies

```bash
cd frontend
npm install
npm run build
cd ..
```

## Run the app locally

From the project root:

```bash
python server.py
```

Then open:

```text
http://localhost:8000
```

## Run the backend API directly

```bash
uvicorn server:app --reload --host 127.0.0.1 --port 8000
```

## Run the tests

```bash
python -m pytest -q
```

The project includes a demo repository test suite of the simulated incident scenario.

## CLI mode

You can also run the analysis loop without the frontend:

```bash
python run_cli.py
```

Use reset mode to restore the demo repo to the original buggy baseline:

```bash
python run_cli.py --reset
```

## API overview

The backend exposes endpoints such as:

- `GET /api/health`
- `GET /api/scenarios`
- `GET /api/status`
- `GET /api/telemetry`
- `POST /api/run-tests`
- `POST /api/reset`
- `GET /api/artifacts`
- `GET /api/investigate/stream`

## Deployment

### Local deployment

This project is ready to run locally with:

```bash
python server.py
```

### Render / Railway / similar host

Use the project root as the app root and set the start command to:

```bash
python server.py
```

If using a frontend build deployment, ensure the React app is built first:

```bash
cd frontend
npm install
npm run build
```

The backend serves the built frontend if `frontend/dist` exists.

## Demo workflow

1. Select an incident scenario
2. View generated telemetry and timeline
3. Review evidence graph
4. Observe hypothesis confidence updates
5. Reproduce the bug through a controlled request
6. Confirm root cause using code inspection and logs
7. Apply minimal fix
8. Run regression and adversarial verification
9. Export artifacts and report

## Security notes

The project includes a constrained file-access utility to prevent path traversal and unsafe repo writes. This is designed for the demo environment and helps keep the incident workflow contained to the dedicated demo repository.

## License

This project is intended for educational and demo purposes.

## Contributing

Contributions are welcome. Suggestions for better incidents, tighter verification logic, and stronger automation flows are encouraged.

## Contact

Project repo:

- https://github.com/Dakshhhhh-ops/incidentpilot.git

## Acknowledgements

This project was built as a demo SRE tooling concept for autonomous incident analysis and recovery.
