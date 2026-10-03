# IncidentPilot

> **"An autonomous SRE agent that turns production telemetry into a verified, evidence-backed code fix."**

IncidentPilot is an autonomous SRE & Engineering Ops agent that reacts to production incidents end-to-end:
`Telemetry Ingestion ➔ Evidence Correlation ➔ Multi-Hypothesis Evaluation ➔ Failure Reproduction ➔ Root Cause Proof ➔ Minimal Patch ➔ Double-Check Verification ➔ Auditable Incident Report`

---

## 💥 The Problem

Traditional monitoring tools tell engineers:
> *"Something is broken (Checkout API HTTP 500 error rate spiked to 31.4%)."*

Generative AI coding assistants tell engineers:
> *"Here is some generated code snippet that might fix it."*

**The missing link**: Neither system proves *why* the incident occurred, evaluates competing explanations, reproduces the actual failure, or independently verifies that the fix resolves the incident without causing regressions.

---

## 🚀 The Solution: IncidentPilot

IncidentPilot connects the missing operational chain:

```text
Production Incident ➔ Observe ➔ Correlate Evidence ➔ Generate Hypotheses ➔ Reproduce Failure ➔ Confirm Root Cause ➔ Generate Minimal Patch ➔ Execute Verification Gate ➔ Produce Auditable Report
```

The core demo moment is **NOT** "AI generated a patch."  
It is: **"The agent proved why the incident happened, produced a minimal fix, and independently verified that the same failure no longer occurs."**

---

## 🏗️ Architecture & Core Modules

IncidentPilot is built on a modern **React + Vite** frontend UI and **FastAPI** backend with deterministic harness guardrails:

```text
                                 Incident / Telemetry Context
                                              │
                                              ▼
                             ┌─────────────────────────────────┐
                             │    13-Stage State Machine       │
                             └─────────────────────────────────┘
                                              │
                     ┌────────────────────────┼────────────────────────┐
                     ▼                        ▼                        ▼
        ┌─────────────────────────┐ ┌───────────────────┐ ┌────────────────────────┐
        │ Multi-Hypothesis Engine │ │ Evidence Graph    │ │ Failure Reproduction   │
        │ (H1, H2, H3 Evaluator)  │ │ (Causal Mapper)   │ │ Counterfactual Proof   │
        └─────────────────────────┘ └───────────────────┘ └────────────────────────┘
                     │                        │                        │
                     └────────────────────────┼────────────────────────┘
                                              ▼
                             ┌─────────────────────────────────┐
                             │       Minimal Patch Engine      │
                             └─────────────────────────────────┘
                                              │
                                              ▼
                             ┌─────────────────────────────────┐
                             │   Adversarial Double-Check Gate │
                             └─────────────────────────────────┘
                                              │
                                              ▼
                             ┌─────────────────────────────────┐
                             │ Auditable Artifacts & Review    │
                             └─────────────────────────────────┘
```

### Core Stack

- **React + Vite Frontend (`frontend/`)**: Modern SRE command center dashboard (HTML5, Vanilla CSS glassmorphic dark theme, React hooks, Lucide icons, SSE live event streaming).
- **FastAPI Backend Server (`server.py`)**: High-performance REST & Server-Sent Events (SSE) server serving API routes and static production build.
- **Engine Modules (`core/`)**:
  - `core/state_machine.py`: 13-stage explicit state machine.
  - `core/hypotheses.py`: Multi-hypothesis evaluator (`H1`, `H2`, `H3`).
  - `core/evidence.py`: Causal evidence map builder.
  - `core/experiments.py`: Counterfactual proof & failure reproduction.
  - `core/verifier.py`: Adversarial double-check verifier & gate.
  - `core/artifact_generator.py`: Auditable post-mortem bundle generator.

---

## 📦 Project Structure

```text
incidentpilot/
├── server.py                   # FastAPI Server (API & React Static Server)
├── run_cli.py                  # CLI runner with live event streaming & --reset flag
├── agent.py                    # LLM agent loop & state machine generator
├── tools.py                    # Security sandbox, file tools, pytest runner, git diff
├── smoke_test.py               # Security & sandbox unit test runner
├── frontend/                   # React + Vite Web Application UI
│   ├── src/
│   │   ├── App.jsx             # React SRE Dashboard Component
│   │   ├── index.css           # Glassmorphic Dark Theme CSS
│   │   └── main.jsx
│   ├── dist/                   # Production React build assets
│   └── package.json
├── core/                       # Core Autonomous Engine Modules
│   ├── state_machine.py        # 13-stage explicit state machine
│   ├── hypotheses.py           # Multi-hypothesis evaluator & confidence tracker
│   ├── evidence.py             # Causal evidence graph generator
│   ├── experiments.py          # Counterfactual proof & failure reproduction
│   ├── verifier.py             # Adversarial double-check verifier & gate
│   └── artifact_generator.py   # Multi-artifact exporter
├── data/                       # Telemetry & Incident Catalog
│   ├── incidents.py            # INC-4821, INC-7392, INC-9104 catalog
│   └── telemetry.py            # Telemetry metric series & timeline generator
├── tests/                      # Core engine unit tests
│   └── test_engine.py          # Pytest suite for engine modules
├── demo-repo/                  # Isolated Git repository
├── requirements.txt
├── README.md
└── .gitignore
```

---

## ⚡ Quick Start Guide

### 1. Run Unified Web App (React UI + FastAPI)

```bash
cd incidentpilot
python server.py
```
Open your browser at **[http://localhost:8000](http://localhost:8000)**!

---

### 2. Run CLI Runner

```bash
python run_cli.py

# Reset environment back to v2.4.1 buggy state
python run_cli.py --reset
```

---

### 3. Run Core Engine Pytest Suite

```bash
python -m pytest tests/test_engine.py -v
```

---

*Synthetic demo data - not real production data.*
