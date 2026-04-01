# murder-wizard

> 一个人 + AI，从灵感到商业化发布的剧本杀创作工具。

[![PyPI version](https://img.shields.io/pypi/v/murder-wizard.svg)](https://pypi.org/project/murder-wizard/)
[![Python](https://img.shields.io/pypi/pyversions/murder-wizard.svg)](https://pypi.org/project/murder-wizard/)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)

---

## 两种使用方式

| 方式 | 适用场景 | 入口 |
|------|---------|------|
| **CLI** | 本地创作、自动化脚本 | `murder-wizard <command>` |
| **Web** | 浏览器管理、SSE实时预览、团队协作 | `murder-wizard-web` |

---

## 安装

### CLI

```bash
pip install murder-wizard
```

### Web 版

```bash
cd murder_wizard_web
# 后端
cd backend && pip install -r requirements.txt
# 前端
cd ../frontend && npm install
```

---

## 快速开始

### CLI 模式

```bash
# 1. 初始化项目（原型模式）
murder-wizard init myproject --type mechanic --prototype

# 2. 运行阶段 1-3
murder-wizard phase myproject 1   # 机制设计
murder-wizard phase myproject 2   # 剧本创作
murder-wizard phase myproject 3   # 视觉物料

# 3. 扩写为完整 6 人版
murder-wizard expand myproject

# 4. 继续完整阶段
murder-wizard phase myproject 4   # 用户测试
murder-wizard phase myproject 4 --analyze   # 分析反馈
murder-wizard phase myproject 5   # 商业化
murder-wizard phase myproject 6   # 印刷生产

# 查看状态
murder-wizard status myproject
```

### Web 模式

```bash
# 终端 1：后端
cd murder_wizard_web/backend
python main.py

# 终端 2：前端
cd murder_wizard_web/frontend
npm run dev

# 浏览器打开
http://localhost:5173
```

---

## 工作流 8 阶段

```
阶段1：机制设计 ──→ 阶段2：剧本创作 ──→ 阶段3：视觉物料
     │                    │                    │
     ▼                    ▼                    ▼
  mechanism.md      characters.md         image-prompts.md
                 + information_matrix.md

                                           │
              扩写 expand ──→ 阶段4：用户测试
                   │                │
                   │                ▼
                   │          test_guide.md
                   │          + iteration_report.md
                   │                │
                   ▼                ▼
              阶段5：商业化 ──→ 阶段6：印刷生产
                   │                │
                   ▼                ▼
             commercial.md      script.pdf
                             + clue_cards.pdf
                             + print_order.json
                                           │
              阶段7：宣发内容 ──→ 阶段8：社区运营
```

---

## 全部命令（CLI）

| 命令 | 说明 |
|------|------|
| `murder-wizard init <name>` | 初始化项目 |
| `murder-wizard status <name>` | 查看状态 |
| `murder-wizard phase <name> <n>` | 运行阶段 1-8 |
| `murder-wizard expand <name>` | 原型扩写为完整版 |
| `murder-wizard resume <name>` | 从中断处继续 |
| `murder-wizard audit <name>` | 完整穿帮审计（上线前必做） |
| `murder-wizard cache <name>` | 查看/清空 LLM 缓存 |

---

## Web 功能

### 页面路由

| 路由 | 说明 |
|------|------|
| `/` | 项目列表仪表盘 |
| `/projects/:name` | 项目详情 + 8阶段进度 |
| `/projects/:name/phase/:n` | 阶段执行（SSE流式输出） |
| `/projects/:name/matrix` | 信息矩阵可视化编辑器 |
| `/projects/:name/files/:f` | Monaco编辑器（Markdown） |
| `/projects/:name/audit` | 穿帮审计报告 |
| `/projects/:name/costs` | API消耗统计 |
| `/metrics` | 落地页A/B测试统计 |
| `/settings` | LLM / Notion / Obsidian 配置 |
| `/subscription` | 订阅管理（Pro版本） |
| `/landing` | 落地页（随机分配A/B） |
| `/landing-a` | 落地页A（技术向） |
| `/landing-b` | 落地页B（新手友好） |

### 落地页 A/B 测试

访问 `/landing` 随机分配，或通过 `?variant=a` / `?variant=b` 强制指定版本。

---

## 配置

### 环境变量

| 环境变量 | 默认值 | 说明 |
|----------|--------|------|
| `LLM_PROVIDER` | `claude` | `claude` / `openai` / `ollama` / `minimax` |
| `ANTHROPIC_API_KEY` | - | Claude API Key（provider=claude时） |
| `OPENAI_API_KEY` | - | OpenAI API Key（provider=openai时） |
| `OLLAMA_BASE_URL` | `http://localhost:11434/v1` | Ollama 服务地址（provider=ollama时） |
| `OLLAMA_MODEL` | `llama3` | Ollama 模型名 |

> **注**：API Key 也可通过 Web 界面设置（`/settings`），保存在 `~/.murder-wizard/settings.json`。

### LLM 提供商

| 提供商 | 说明 |
|--------|------|
| `claude` | Anthropic Claude（默认，需要 ANTHROPIC_API_KEY） |
| `openai` | OpenAI GPT-4o（需要 OPENAI_API_KEY） |
| `ollama` | 本地 Ollama（零成本，保护隐私） |
| `minimax` | MiniMax（需要 MINIMAX_API_KEY） |

---

## 输出产物

```
~/.murder-wizard/projects/<name>/
├── outline.md              # 大纲
├── mechanism.md           # 机制设计
├── information_matrix.md   # 信息矩阵（Markdown）
├── characters.md          # 角色剧本
├── image-prompts.md       # 图像提示词
├── test_guide.md         # 测试指南
├── iteration_report.md    # 迭代报告
├── commercial.md         # 商业化方案
├── script.pdf           # 剧本 PDF
├── materials/            # 视觉物料
│   ├── 角色图/
│   ├── 海报/
│   └── 卡牌/
├── state/                # JSON 真相文件
│   ├── character_matrix.json  # 角色×事件信息矩阵
│   └── .backups/         # 自动备份（immutable）
├── cost.log             # API 消耗日志
└── audit_report.md      # 完整穿帮审计报告
```

---

## 原型模式

默认开启原型模式（2人 + 3事件），先快速验证核心机制，再通过 `expand` 扩写为完整的 6 人 + 5-7 事件版本。

```bash
# 原型模式（默认）
murder-wizard init myproject

# 完整模式（直接6人）
murder-wizard init myproject --full --type mechanic
```

---

## Pro 版本（订阅制）

| 功能 | 免费版 | Pro版（¥29/月） |
|------|--------|----------------|
| 8阶段工作流 | ✅ | ✅ |
| 本地存储 | ✅ | ✅ |
| 云端存储 | ❌ | ✅ |
| 团队协作 | ❌ | ✅（最多10人） |
| AI 穿帮检测 | ❌ | ✅ |
| 高级模板库 | ❌ | ✅ |
| 优先 LLM 通道 | ❌ | ✅ |
| 专属客服 | ❌ | ✅ |

订阅管理入口：`/subscription` 或 Web 界面侧边栏。

---

## 文档

- [工作流详解](./docs/) — 8阶段完整流程文档
- [模板库](./templates/) — 可直接复用的模板
- [Prompt库](./prompts/) — AI创作提示词
- [Pro版探索计划](./discovery_plan.md) — GUI+Web升级产品探索
- [CHANGELOG](./CHANGELOG.md) — 版本变更记录

---

## 开发

```bash
# 安装
git clone https://github.com/Shaojie66/murder-mystery-ai-workflow.git
cd murder-mystery-ai-workflow
pip install -e .

# CLI 测试
pytest tests/ -v

# Web 后端
cd murder_wizard_web/backend
pip install -r requirements.txt
python main.py   # http://localhost:8000

# Web 前端
cd ../frontend
npm install
npm run dev      # http://localhost:5173

# 生产构建
cd ../frontend && npm run build
```

---

## Docker 部署

```bash
# 一键启动（后端 + 前端）
cd murder_wizard_web
docker-compose up -d

# 查看日志
docker-compose logs -f

# 停止
docker-compose down

# 环境变量（可选）
LLM_PROVIDER=claude ANTHROPIC_API_KEY=sk-xxx docker-compose up -d
```

前端访问：`http://localhost:3000`
后端 API：`http://localhost:8000`

---

## License

MIT © [Shaojie Chen](https://github.com/Shaojie66)
