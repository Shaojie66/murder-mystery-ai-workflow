# murder-wizard

> 一个人 + AI，从灵感到商业化发布的剧本杀创作 CLI 工具。

[![PyPI version](https://img.shields.io/pypi/v/murder-wizard.svg)](https://pypi.org/project/murder-wizard/)
[![Python](https://img.shields.io/pypi/pyversions/murder-wizard.svg)](https://pypi.org/project/murder-wizard/)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)

## 核心功能

- **5 类剧本杀类型化工作流**：情感本、推理本、欢乐本、恐怖本、机制本
- **8 阶段完整流程**：从机制设计到社区运营
- **质量门禁**：每阶段自动验证输出质量
- **原型模式**：2 人小本快速验证，再扩写为 6 人完整版
- **Web 界面**：可选的浏览器界面（FastAPI + React）
- **LLM 适配**：支持 Claude / GPT-4o / Ollama

## 安装

```bash
pip install murder-wizard
```

设置环境变量：

```bash
export ANTHROPIC_API_KEY="sk-ant-..."   # Claude API（主要）
export OPENAI_API_KEY="sk-..."           # GPT-4o（备选）
```

## 快速开始

```bash
# 1. 初始化项目
murder-wizard init myproject --type mechanic

# 2. 运行阶段
murder-wizard phase myproject 1   # 机制设计
murder-wizard phase myproject 2   # 剧本创作
murder-wizard phase myproject 3   # 视觉物料

# 3. 查看状态
murder-wizard status myproject
```

## 剧本杀类型

| 类型 | 核心特点 | 适用场景 |
|------|----------|----------|
| 情感本 | 情感弧线、角色成长、两难抉择 | 追求沉浸体验的玩家 |
| 推理本 | 证据链、逻辑推理、公平性验证 | 烧脑爱好者 |
| 欢乐本 | 社交碰撞、喜剧人设、即兴空间 | 聚会团建 |
| 恐怖本 | 氛围营造、心理压迫、悬念揭示 | 追求刺激的玩家 |
| 机制本 | 阵营对抗、策略博弈、平衡性 | 策略游戏爱好者 |

## 工作流 8 阶段

```
阶段1：机制设计 ──→ 阶段2：剧本创作 ──→ 阶段3：视觉物料
     │                    │                    │
     ▼                    ▼                    ▼
  mechanism.md       characters.md         image-prompts.md
                 + information_matrix.md

                                           │
                                           ▼
              扩写 expand ──→ 阶段4：用户测试
                   │                │
                   │                ▼
                   │          test_guide.md
                   │                │
                   ▼                ▼
              阶段5：商业化 ──→ 阶段6：印刷生产
                   │                │
                   ▼                ▼
             commercial.md      script.pdf
                              + clue_cards.pdf
```

## 全部命令

| 命令 | 说明 |
|------|------|
| `murder-wizard init <name>` | 初始化项目 |
| `murder-wizard status <name>` | 查看状态 |
| `murder-wizard phase <name> <n>` | 运行阶段 1-8 |
| `murder-wizard expand <name>` | 原型扩写为完整版 |
| `murder-wizard resume <name>` | 从中断处继续 |
| `murder-wizard audit <name>` | 完整穿帮审计（上线前必做） |
| `murder-wizard cache <name>` | 查看/清空 LLM 缓存 |

## 项目结构

```
murder-wizard/
├── murder_wizard/          # CLI 包
│   ├── cli/               # 命令行入口
│   ├── llm/              # LLM 适配层（Claude/GPT-4o/Ollama）
│   ├── prompts/          # Prompt 模板库
│   ├── wizard/           # 核心逻辑（状态机、会话）
│   ├── print/            # PDF 生成
│   └── web/              # Web 界面（可选）
├── tests/                 # pytest 测试
├── docs/                 # 工作流文档
├── templates/            # 可复用模板
└── prompts/              # Prompt 库
```

## 输出产物

```
~/.murder-wizard/projects/<name>/
├── mechanism.md           # 机制设计
├── information_matrix.md  # 信息矩阵
├── characters.md         # 角色剧本
├── image-prompts.md      # 图像提示词
├── test_guide.md         # 测试指南
├── commercial.md         # 商业化方案
├── script.pdf            # 剧本 PDF
├── clue_cards.pdf        # 线索卡 PDF
└── audit_report.md      # 穿帮审计报告
```

## 配置

| 环境变量 | 说明 | 默认值 |
|----------|------|--------|
| `ANTHROPIC_API_KEY` | Anthropic API Key | 必填 |
| `OPENAI_API_KEY` | OpenAI API Key（备选） | 选填 |
| `LLM_PROVIDER` | LLM 提供商 | `claude` |
| `OLLAMA_BASE_URL` | Ollama 服务地址 | `http://localhost:11434` |

## Web 界面（可选）

```bash
# 启动 Web 服务
cd murder_wizard_web && docker-compose up

# 访问 http://localhost:3000
```

## 文档

- [工作流详解](./docs/) — 8 阶段完整流程文档
- [模板库](./templates/) — 可直接复用的模板
- [Prompt 库](./prompts/) — AI 创作提示词
- [CHANGELOG](./CHANGELOG.md) — 版本变更记录

## 开发

```bash
# 本地开发安装
git clone https://github.com/Shaojie66/murder-mystery-ai-workflow.git
cd murder-mystery-ai-workflow
pip install -e .

# 运行测试
pytest tests/ -v

# CLI 调试
python -m murder_wizard.cli --help
```

## License

MIT © [Shaojie Chen](https://github.com/Shaojie66)
