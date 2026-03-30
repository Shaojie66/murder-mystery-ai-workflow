# murder-wizard

> 一个人 + AI，从灵感到商业化发布的剧本杀创作 CLI 工具。

[![PyPI version](https://img.shields.io/pypi/v/murder-wizard.svg)](https://pypi.org/project/murder-wizard/)
[![Python](https://img.shields.io/pypi/pyversions/murder-wizard.svg)](https://pypi.org/project/murder-wizard/)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)

## 安装

```bash
pip install murder-wizard
```

需要设置环境变量：

```bash
export ANTHROPIC_API_KEY="sk-ant-..."   # Claude API（主要）
export OPENAI_API_KEY="sk-..."           # GPT-4o（备选）
```

## 快速开始

```bash
# 1. 初始化项目（原型模式，2人小本快速验证）
murder-wizard init myproject --type mechanic --prototype

# 2. 运行阶段1-3
murder-wizard phase myproject 1   # 机制设计
murder-wizard phase myproject 2   # 剧本创作
murder-wizard phase myproject 3   # 视觉物料

# 3. 扩写为完整6人版
murder-wizard expand myproject

# 4. 继续完整阶段
murder-wizard phase myproject 4   # 用户测试
murder-wizard phase myproject 4 --analyze   # 分析反馈
murder-wizard phase myproject 5   # 商业化
murder-wizard phase myproject 6   # 印刷生产

# 查看状态
murder-wizard status myproject
```

## 工作流 8 阶段

```
阶段1：机制设计 ──→ 阶段2：剧本创作 ──→ 阶段3：视觉物料
     │                    │                    │
     ▼                    ▼                    ▼
  mechanism.md      characters.md         image-prompts.md
                 + information_matrix.md
                                           │
                                           ▼
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
```

## 全部命令

| 命令 | 说明 |
|------|------|
| `murder-wizard init <name>` | 初始化项目 |
| `murder-wizard status <name>` | 查看状态 |
| `murder-wizard phase <name> <n>` | 运行阶段 1-8 |
| `murder-wizard expand <name>` | 原型扩写为完整版 |
| `murder-wizard resume <name>` | 从中断处继续 |

## 原型模式

默认开启原型模式（2人 + 3事件），先快速验证核心机制，再通过 `expand` 扩写为完整的 6 人 + 5-7 事件版本。

```bash
# 原型模式（默认）
murder-wizard init myproject

# 完整模式（直接6人）
murder-wizard init myproject --full --type mechanic
```

## 输出产物

```
~/.murder-wizard/projects/<name>/
├── outline.md              # 大纲
├── mechanism.md           # 机制设计
├── information_matrix.md   # 信息矩阵
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
└── cost.log             # API 消耗日志
```

## 配置

| 环境变量 | 说明 | 默认值 |
|----------|------|--------|
| `ANTHROPIC_API_KEY` | Anthropic API Key | 必填 |
| `OPENAI_API_KEY` | OpenAI API Key（备选） | 必填 |
| `MURDER_WIZARD_LLM` | LLM 提供商 | `claude` |

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
