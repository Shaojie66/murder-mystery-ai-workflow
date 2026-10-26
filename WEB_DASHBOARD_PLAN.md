# Murder Wizard Web Dashboard — Architecture Plan

> **历史方案说明（2026-10-24 更新）**：本文保留早期探索内容。当前产品按本地单用户 Alpha 推进，有效范围与验收见[本地可靠性 MVP 方案](./docs/reliability-mvp-plan.md)。除另附日期、样本与原始结果外，需求、市场、价格、增长及准确率均为待验证假设。
>
> 此处保留早期模块拆分；目录与功能以当前代码为准。本轮按用户闭环修复合同与执行状态，不按页面数量判断完成。

## Overview

Full web-based management dashboard for the murder-wizard CLI tool.

**Tech Stack:**
- Backend: FastAPI (Python) + SSE streaming
- Frontend: React 18 + TypeScript + Vite + Tailwind CSS + Zustand
- Location: `murder_wizard_web/` subdirectory in the repo

## Directory Structure

```
murder_wizard_web/
├── backend/
│   ├── main.py                  # FastAPI app entry
│   ├── requirements.txt
│   ├── murder_wizard/          # Symlinked from parent
│   ├── api/
│   │   ├── projects.py         # Project CRUD
│   │   ├── phases.py            # Phase execution + SSE
│   │   ├── files.py            # File read/write
│   │   ├── matrix.py           # Character matrix API
│   │   ├── audit.py            # Audit API
│   │   ├── pdf.py              # PDF generation
│   │   └── costs.py            # Cost API
│   └── core/
│       ├── config.py            # Base path config
│       ├── phase_runner_web.py  # SSE PhaseRunner wrapper
│       └── sse_manager.py       # SSE connection manager
└── frontend/
    ├── src/
    │   ├── api/                 # API client functions
    │   ├── components/          # React components
    │   ├── pages/               # Route pages
    │   ├── stores/              # Zustand stores
    │   ├── hooks/               # Custom hooks
    │   └── types/               # TypeScript types
    ├── package.json
    ├── vite.config.ts
    ├── tailwind.config.js
    └── tsconfig.json
```

## API Endpoints

### Projects
- `GET /api/projects` — List all projects
- `POST /api/projects` — Create project
- `GET /api/projects/{name}` — Get project details
- `DELETE /api/projects/{name}` — Delete project

### Phase Execution
- `POST /api/projects/{name}/phases/{stage}/run` — Run phase with SSE streaming
- `GET /api/projects/{name}/phases/{stage}/status` — Check running status
- `POST /api/projects/{name}/expand` — Expand prototype (SSE)
- `POST /api/projects/{name}/audit` — Run audit (SSE)

### Files
- `GET /api/projects/{name}/files` — List files
- `GET /api/projects/{name}/files/{filename}` — Get content
- `PUT /api/projects/{name}/files/{filename}` — Save content

### Matrix
- `GET /api/projects/{name}/matrix` — Get character matrix JSON
- `PUT /api/projects/{name}/matrix/cells/{char_id}/{event_id}` — Update cell
- `POST /api/projects/{name}/matrix/evidence` — Add evidence

### Costs
- `GET /api/projects/{name}/costs` — Cost breakdown

### PDF
- `POST /api/projects/{name}/pdf/generate` — Generate PDF
- `GET /api/projects/{name}/pdf/status` — Print readiness

## SSE Event Types

```
start | progress | token | cost | artifact | stage_complete |
round_complete | revision_complete | audit_complete | error | end
```

## Build Priority

1. **Phase 1**: Core backend + Project list (FastAPI + React setup)
2. **Phase 2**: Phase execution with SSE streaming
3. **Phase 3**: File viewer + Monaco editor
4. **Phase 4**: Information matrix visualizer
5. **Phase 5**: Audit + Expand SSE
6. **Phase 6**: PDF preview + Cost dashboard
7. **Phase 7**: Full init wizard migration
