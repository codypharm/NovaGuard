# Nova Clinical Guard

> **Mission**: Eliminate transcription errors and improve patient safety using Amazon Nova 2026 AI suite.

## Overview

Nova Clinical Guard is a failsafe clinical layer that digitizes "dirty" medical data (handwritten scripts) and performs intelligent safety audits against a patient's unique medical history.

## Features

### 🔍 Multimodal Ingestion
- **Image**: OCR handwritten prescriptions with Nova 2 Lite
- **Text**: Parse typed prescription data
- **Voice**: Speech-to-text with Nova 2 Sonic

### 🗄️ Persistent Patient Context
- Secure PostgreSQL database of patient records
- Drug history timeline
- Allergy registry (drug/environmental/contact)
- Adverse reaction tracking

### 🛡️ Comprehensive Safety Checks (16+ via OpenFDA)
- ⚠️ Boxed warnings (Black Box)
- ⛔ Contraindications
- 💊 Drug interactions
- 🤰 Pregnancy & nursing safety
- 👶 Pediatric dosing
- 👴 Geriatric considerations
- 🧪 Renal/hepatic adjustments
- And more...

### 🤖 Agentic Orchestration
- LangGraph state machine ensures no prescription is cleared without database check
- Human-in-the-Loop confirmation for all extractions
- Color-coded safety verdicts (Green/Yellow/Red)

## Quick Start

### Prerequisites
- Python 3.11+
- PostgreSQL 14+
- [uv](https://github.com/astral-sh/uv) package manager

### Installation

```bash
# Clone the repository
git clone <repo-url>
cd nova-guard

# Install dependencies
uv sync

# Setup environment
cp .env.example .env
# Edit .env with your PostgreSQL credentials

# Run database migrations
uv run alembic upgrade head

# Start the API server
uv run uvicorn src.nova_guard.main:app --reload
```

## Project Structure

```
nova-guard/
├── src/nova_guard/
│   ├── api/              # FastAPI endpoints
│   ├── models/           # SQLAlchemy models
│   ├── schemas/          # Pydantic schemas
│   ├── services/         # Business logic (OpenFDA, etc.)
│   ├── graph/            # LangGraph nodes & workflows
│   └── main.py           # FastAPI app
├── tests/                # Pytest test suite
├── alembic/              # Database migrations
└── pyproject.toml        # Project config
```

## Development Roadmap

- [x] Phase 1: The Local Core (FastAPI + LangGraph + PostgreSQL)
- [ ] Phase 2: The AWS Leap (Bedrock, Aurora, Fargate)
- [ ] Phase 3: The Superpowers (Sonic Voice, Act Automation)

## License

MIT
