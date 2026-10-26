# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 项目概述

`murder-wizard` — 剧本杀创作 CLI 工具，提供 8 阶段完整工作流（机制设计→剧本创作→视觉物料→用户测试→商业化→印刷生产→宣发内容→社区运营）。

`murder_wizard_web` — Web 版本（React + FastAPI + Tailwind），包含落地页、项目仪表盘、信息矩阵编辑器、Monaco 文件编辑器。

## 开发命令

```bash
# CLI
pip install -e .                              # 安装
pytest tests/ -v                              # 运行全部测试
pytest tests/test_phase_runner.py -v          # 单个测试文件
pytest tests/ -k "test_session" -v            # 按名称过滤

# Web 后端
cd murder_wizard_web/backend
pip install -r requirements.txt
python main.py                                # http://localhost:8000

# Web 前端
cd murder_wizard_web/frontend
npm install
npm run dev                                   # http://localhost:5173

# Docker
cd murder_wizard_web && docker-compose up -d
```

## 核心架构

**CLI 核心** (`murder_wizard/`)
- `cli/phase_runner.py` — 阶段执行器，所有 LLM 调用通过 `_call_llm()` 自动记录 token 消耗
- `cli/commands.py` — CLI 命令路由（init/status/phase/expand/resume/audit/cache）
- `wizard/session.py` — 会话持久化到 `~/.murder-wizard/projects/<name>/`
- `wizard/state_machine.py` — 8 阶段状态机枚举
- `wizard/schemas.py` — Pydantic 模型（CharacterMatrix, TruthDelta 等）
- `llm/client.py` — Claude/OpenAI/Ollama/MiniMax 适配器

**Web 核心** (`murder_wizard_web/`)
- `backend/main.py` — FastAPI 入口
- `backend/api/phases.py` — 阶段执行 + SSE 流式输出
- `backend/core/phase_runner_web.py` — CLI PhaseRunner 的 SSE 包装器

**产物路径**: `~/.murder-wizard/projects/<name>/`
- `outline.md`, `mechanism.md`, `characters.md`, `information_matrix.md`, `image-prompts.md`
- `test_guide.md`, `iteration_report.md`, `commercial.md`
- `script.pdf`, `clue_cards.pdf`
- `state/character_matrix.json` (角色×事件信息矩阵，真相文件)
- `cost.log` (API token 消耗日志)

## 8 阶段工作流

```
阶段1：机制设计    → mechanism.md
阶段2：剧本创作    → characters.md + information_matrix.md
阶段3：视觉物料    → image-prompts.md
阶段4：用户测试    → test_guide.md + iteration_report.md
阶段5：商业化      → commercial.md
阶段6：印刷生产    → script.pdf + clue_cards.pdf
阶段7：宣发内容    → promo_content.md
阶段8：社区运营    → community_plan.md
```

**原型模式**: 默认 2 人 + 3 事件 → `expand` 扩写为完整 6 人 + 7 事件

## LLM 配置

| 环境变量 | 默认值 | 说明 |
|---------|--------|------|
| `LLM_PROVIDER` | `claude` | `claude` / `openai` / `ollama` / `minimax` |
| `ANTHROPIC_API_KEY` | - | Claude API |
| `OPENAI_API_KEY` | - | GPT-4o |
| `OLLAMA_BASE_URL` | `http://localhost:11434/v1` | Ollama（推荐开发测试用） |

## 剧本杀类型

5 种类型（各自有独立 Prompt 模板 `murder_wizard/prompts/`）：

| 类型 | 英文 | 核心特点 |
|------|------|----------|
| 情感本 | emotion | 情感弧线、角色成长、两难抉择 |
| 推理本 | reasoning | 证据链、逻辑推理、公平性验证 |
| 欢乐本 | fun | 社交碰撞、喜剧人设、即兴空间 |
| 恐怖本 | horror | 氛围营造、心理压迫、悬念揭示 |
| 机制本 | mechanic | 阵营对抗、策略博弈、平衡性 |

## 执行约定

1. 所有 LLM 调用通过 `PhaseRunner._call_llm()`，自动记录 token 消耗
2. session.json 损坏时，`SessionManager.recover_from_files()` 从 md 文件重建状态
3. 阶段跳过逻辑：检查产物文件是否已存在
4. 新增阶段：Stage 枚举 → PhaseRunner 方法 → commands.py 路由
5. 穿帮检测：角色 A 不能知道角色 B 当时不知道的信息

## Design Context

### 用户
剧本杀创作者 — 有创作热情但对完整流程不熟悉，CLI 舒适度高。最终产出印刷用 PDF。

### Brand Personality
- **Voice**: 冷静、务实、不废话 — 像个经验丰富的制作人
- **3-word personality**: 专业、可靠、有章法

### Design Principles
1. **专业感来自克制** — 功能性色彩（green=完成 yellow=进行中 red=错误），不多余装饰
2. **输出即名片** — 阶段生成的 .md 文件本身就是专业工作文档，不是中间产物
3. **流程透明，状态明确** — `murder-wizard status` 一眼看清 8 阶段进度和缺失产物
4. **容错与恢复** — Ctrl+C 保存进度，session.json 损坏时自动重建
5. **Prompt 质量 = 产出质量** — prompt 模板是核心资产，创意简报（brief.md）是所有后续 prompt 的默认上下文

### Web Design Tokens
```
--bg-base: #12110F        --bg-raised: #1C1917      --border: #3D3532
--text-cream: #F5F0E8    --text-muted: #8A8078     --text-faint: #6B6460
--accent-crimson: #9B1C1C --accent-gold: #C77A08
```
