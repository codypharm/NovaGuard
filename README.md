# Nova Clinical Guard

> **Mission**: Eliminate prescription errors and improve patient safety using the Amazon Nova 2026 AI suite and multi-layered clinical audit workflows.

## 🚀 Overview

Nova Clinical Guard is a professional-grade clinical safety platform designed for pharmacists and clinicians. It transforms "dirty" medical data (handwritten scripts, fragments) into structured clinical wisdom, performing real-time audits against a patient's unique history and the latest FDA consensus.

## ✨ Core Features

### 🏦 Safety HUD & Multimodal Ingestion
- **Intelligent Ingestion**: OCR handwritten prescriptions via Nova 2 Lite, typed data parsing, and high-fidelity extraction.
- **Agentic Orchestration**: LangGraph-powered state machines ensure no prescription is cleared without passing a multi-point safety check.
- **Human-in-the-Loop**: Seamless confirmation UI for AI extractions before they hit the patient record.

### 💊 Drug Operations Module (2026 Pro)
A specialized dashboard for rapid clinical decision support:
- **Regimen Safety Assessment**: Multi-drug analysis that considers cumulative risks, individual dosages, and durations for a complete patient profile.
- **Interaction Sandbox**: Detailed **CYP450 metabolism insights** and drug-drug interaction matrices formatted in high-fidelity Markdown.
- **Clinical Dose Calculator**: AI-enhanced Cockcroft-Gault calculations with automatic AdjBW/IBW selection and FDA-mapped renal adjustment recommendations.
- **Substitution Engine**: Rapid lookup of therapeutic equivalents and 2026 interchangeable biosimilars for formulary management.

### 🗄️ Clinical Context & Safety Matrix
- **Persistent Patient Profiles**: Secure PostgreSQL storage of allergies, adverse reactions, and medication history.
- **At-A-Glance Safety Matrix**: Visual consensus reports for Pregnancy, Lactation, Geriatric, and Pediatric populations.
- **Black Box Monitoring**: Real-time FDA status tracking and critical patient counseling generation.

## 🛠️ Technical Stack

### Backend (FastAPI & AI)
- **Engine**: Python 3.11+ / FastAPI
- **Orchestration**: LangGraph (Stateful Multi-Agent Workflows)
- **AI**: Amazon Nova (via Bedrock) & OpenAI
- **Database**: PostgreSQL with SQLAlchemy (Async)
- **Clinical Data**: OpenFDA API integration

### Frontend (React & UX)
- **Framework**: Vite / React 18+ / TypeScript
- **Styling**: Tailwind CSS (Shadcn UI)
- **Auth**: Clerk (Unified Clinical Identity)
- **Reports**: Markdown-based rendering with custom clinical typography

## 🚦 Quick Start

### Backend Setup
```bash
# Clone the repository
git clone <repo-url>
cd nova-guard

# Install dependencies
uv sync

# Setup environment
cp .env.example .env
# Edit .env with your keys (AWS_REGION, DATABASE_URL, VITE_CLERK_PUBLISHABLE_KEY)

# Initial DB migration
uv run alembic upgrade head

# Start API
uv run uvicorn src.nova_guard.main:app --reload
```

### Frontend Setup
```bash
cd frontend
bun install
bun dev
```

## 🗺️ Roadmap
- [x] **Phase 1**: Clinical Core (FastAPI + LangGraph + PostgreSQL)
- [x] **Phase 2**: Clinical Decision Support (Drug Ops Module, Markdown Reports)
- [x] **Phase 3**: Unified Identity (Clerk Integration, Sidebar Sync)
- [ ] **Phase 4**: Voice Integration (Nova 2 Sonic for hands-free consultations)

## ⚖️ License
MIT
