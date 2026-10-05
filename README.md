# Murder Wizard — Multi-Stage LLM Agent Workflow for Creative Content Generation

[![Python](https://img.shields.io/badge/Python-3.9%2B-blue.svg)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![PyPI](https://img.shields.io/pypi/v/murder-wizard.svg)](https://pypi.org/project/murder-wizard/)

English | [中文](./README_CN.md)

---

## Overview

Murder Wizard is a production-grade **multi-stage LLM agent system** that automates the end-to-end creative workflow for narrative game design — from initial concept to production-ready assets. It implements an 8-phase pipeline orchestrating multiple LLM calls with state management, context tracking, and consistency auditing.

Built as both a CLI tool and a full-stack web application, it demonstrates practical engineering patterns for building reliable LLM-powered applications.

---

## Technical Highlights

### Multi-Stage Agent Orchestration
- **8-phase stateful workflow** with explicit phase boundaries, each phase producing structured output artifacts
- **Checkpoint / resume support** — interrupt at any phase and resume from the exact state
- **Immutability** — historical state snapshots are automatically backed up and never overwritten
- **Consistency auditing** — cross-phase fact checking to detect plot holes and narrative contradictions

### LLM Abstraction Layer
- **Multi-provider support**: Anthropic Claude, OpenAI GPT, local Ollama, and MiniMax through a unified interface
- **Prompt engineering library** — domain-specific prompt templates for each creative phase
- **Token cost tracking** — per-phase, per-project API usage logging and cost analytics
- **Response caching** — deduplication of identical LLM calls to reduce costs

### Full-Stack Architecture
- **CLI**: Python package installable via `pip`, with typed command interfaces
- **Web frontend**: React + Vite with SSE (Server-Sent Events) for streaming LLM output
- **Web backend**: Python API server serving both the frontend and orchestration logic
- **State management**: JSON-based project state with file-system persistence

### Engineering Practices
- **PyPI distribution** — packaged and published as `murder-wizard`
- **Docker deployment** — one-command startup via `docker-compose`
- **Test suite** — unit tests covering core workflow logic
- **A/B testing infrastructure** — landing page variant testing built into the web app

---

## Architecture

```
┌─────────────────┐     ┌──────────────────┐     ┌─────────────────┐
│   CLI (Python)  │     │  Web Frontend    │     │   LLM Providers │
│                 │     │  (React + Vite)  │     │                 │
│  - init         │◄───►│  - Dashboard     │◄───►│  - Claude       │
│  - phase 1-8    │ SSE │  - Project view  │HTTP │  - OpenAI       │
│  - expand       │     │  - SSE streaming │     │  - Ollama       │
│  - audit        │     │  - A/B testing   │     │  - MiniMax      │
└────────┬────────┘     └────────┬─────────┘     └─────────────────┘
         │                       │
         ▼                       ▼
┌──────────────────────────────────────────┐
│           Core Orchestration Layer       │
│  - Phase engine      - State management │
│  - Prompt templates  - Cost tracking     │
│  - Audit system      - Caching           │
└──────────────────────────────────────────┘
         │
         ▼
┌──────────────────────────────────────────┐
│        File-system Project Store         │
│  - Markdown artifacts  - JSON state     │
│  - Immutable backups   - Cost logs       │
└──────────────────────────────────────────┘
```

---

## Quick Start

### CLI

```bash
pip install murder-wizard

# Initialize a new project (prototype mode)
murder-wizard init myproject --prototype

# Run phases sequentially
murder-wizard phase myproject 1   # Mechanism design
murder-wizard phase myproject 2   # Story writing
murder-wizard phase myproject 3   # Visual assets

# Expand prototype to full 6-player version
murder-wizard expand myproject

# Continue remaining phases
murder-wizard phase myproject 4   # Playtesting
murder-wizard phase myproject 5   # Commercialization
murder-wizard phase myproject 6   # Print production

# Audit for consistency before release
murder-wizard audit myproject
```

### Web Application

```bash
# Backend
cd murder_wizard_web/backend
pip install -r requirements.txt
python main.py

# Frontend
cd murder_wizard_web/frontend
npm install
npm run dev

# Open http://localhost:5173
```

---

## Tech Stack

| Layer | Technologies |
|-------|-------------|
| **Language** | Python 3.9+, JavaScript / TypeScript |
| **LLM Integration** | Anthropic SDK, OpenAI SDK, Ollama, prompt engineering |
| **Backend** | Python (FastAPI-style), SSE streaming |
| **Frontend** | React, Vite, Monaco Editor |
| **Data / State** | JSON, Markdown, file-system persistence |
| **DevOps** | Docker, docker-compose, PyPI packaging, pytest |

---

## Project Structure

```
murder-mystery-ai-workflow/
├── murder_wizard/          # Core Python package
│   ├── phases/             # 8-phase workflow implementations
│   ├── prompts/            # Prompt template library
│   ├── llm/                # LLM provider abstraction layer
│   ├── state/              # State management & persistence
│   └── audit/              # Consistency auditing system
├── murder_wizard_web/      # Full-stack web app
│   ├── backend/            # Python API server
│   └── frontend/           # React + Vite frontend
├── templates/              # Reusable project templates
├── tests/                  # Unit test suite
├── docs/                   # Documentation
├── pyproject.toml          # PyPI package config
└── requirements.txt        # Dependencies
```

---

## Configuration

```bash
# Set LLM provider (default: claude)
export LLM_PROVIDER=openai
export OPENAI_API_KEY=sk-...

# Or use local Ollama (free, private)
export LLM_PROVIDER=ollama
export OLLAMA_BASE_URL=http://localhost:11434/v1
```

All settings can also be configured through the web UI at `/settings`.

---

## Development

```bash
git clone https://github.com/Shaojie66/murder-mystery-ai-workflow.git
cd murder-mystery-ai-workflow

# Install in development mode
pip install -e .

# Run tests
pytest tests/ -v

# Start web app in dev mode
cd murder_wizard_web/backend && python main.py &
cd murder_wizard_web/frontend && npm run dev
```

---

## License

MIT © [Shaojie Chen](https://github.com/Shaojie66)
