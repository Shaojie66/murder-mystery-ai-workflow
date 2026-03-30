# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working in this repository.

## 项目概述

`murder-wizard` — 剧本杀创作 CLI 工具。提供 8 阶段完整工作流，从大纲到商业发布。

## 工具链

| 环节 | 工具 | 作用 |
|------|------|------|
| 机制研究 | Gemini 3 Pro | 深度研究模式，分析/改编桌游规则 |
| 剧本创作 | Claude / GPT-4o | 大纲扩展、逐章扩写、文风润色 |
| 穿帮检测 | Claude | 一致性检查，信息矩阵管理 |
| 视觉物料 | 即梦 (Jimeng) | 国风人物图、场景图、物料底图 |
| 视频生成 | 海螺AI | 宣传片分镜 |
| 宣发文案 | Claude | 全平台文案生成 |

## CLI 命令

| 命令 | 说明 |
|------|------|
| `murder-wizard init <name>` | 初始化项目 |
| `murder-wizard status <name>` | 查看状态 |
| `murder-wizard phase <name> <n>` | 运行阶段 1-8 |
| `murder-wizard expand <name>` | 原型扩写为完整版 |
| `murder-wizard resume <name>` | 从中断处继续 |
| `murder-wizard audit <name>` | 完整穿帮审计（上线前必做） |
| `murder-wizard cache <name>` | 查看/清空 LLM 缓存 |

## 8 阶段工作流

```
阶段1：机制设计（2周）
  └── LLM 生成机制设计（mechanism.md）

阶段2：剧本创作（4周）
  └── LLM 生成信息矩阵 + 角色剧本（information_matrix.md + characters.md）

阶段3：视觉物料（2周）
  └── LLM 生成图像提示词（image-prompts.md）

阶段4：用户测试（1周）
  └── LLM 生成测试指南（test_guide.md）
  └── --analyze 分析 feedback.md 生成迭代报告（iteration_report.md）

阶段5：商业化（1周）
  └── LLM 生成商业化方案（commercial.md）

阶段6：印刷生产（2周）
  └── PDFGenerator 生成 script.pdf + clue_cards.pdf（reportlab）

阶段7：宣发内容（2周）
  └── LLM 生成多平台文案（promo_content.md）

阶段8：社区运营（持续）
  └── LLM 生成运营方案（community_plan.md）

expand：将原型扩写为完整版本（2人→6人，3事件→5-7事件）
```

## 目录结构

```
剧本杀AI创作工作流/
├── murder_wizard/          # CLI 包
│   ├── __init__.py        # Click CLI 入口
│   ├── cli/               # CLI 层
│   │   ├── __init__.py   # main() 命令组
│   │   ├── commands.py    # 命令实现
│   │   ├── phase_runner.py # 阶段执行器（核心逻辑）
│   │   └── wizard_tui.py  # init 向导 TUI
│   ├── llm/              # LLM 适配层
│   │   ├── client.py     # Claude + OpenAI 适配器
│   │   └── cache.py     # LLM 响应缓存（SHA256 hash）
│   ├── print/            # PDF 生成
│   │   └── pdf_gen.py   # reportlab PDF 输出
│   ├── assets/           # 第三方 API 适配器（存根）
│   │   └── jimeng.py    # 即梦 AI + 海螺 AI（待集成）
│   └── wizard/           # 核心逻辑
│       ├── session.py    # 会话持久化（JSON）
│       └── state_machine.py # 状态机（8阶段枚举）
├── tests/                 # pytest 测试（33个，全部通过）
├── docs/                 # 工作流文档（8阶段详解）
├── templates/            # 可复用模板
├── prompts/             # Prompt 库
├── CLAUDE.md            # 本文件
├── CHANGELOG.md         # 版本记录
├── CONTRIBUTING.md      # 贡献指南
├── LICENSE              # MIT 许可证
└── README.md            # 项目说明
```

## 状态机（Stage 枚举）

```
IDLE → TYPE_SELECT → STORY_BRIEF → CHARACTER_DESIGN → PLOT_BUILD → ASSET_PROMPT → OUTPUT
  │                                                        │
  └──► STAGE_1_MECHANISM ──► STAGE_2_SCRIPT ──► STAGE_3_VISUAL
                                                      │
                              ──► STAGE_4_TEST ──► STAGE_5_COMMERCIAL
                                                                │
                                    ──► STAGE_6_PRINT ──► STAGE_7_PROMO ──► STAGE_8_COMMUNITY
```

## 关键约束

- 剧本杀固定为 6 人（原型模式 2 人）
- 每人有 a 本（阅读本）+ b 本（线索本）
- 必须避免穿帮：角色 A 不能知道角色 B 当时不知道的信息
- 原型模式默认开启，expand 后扩写为完整版
- API 消耗记录在 `cost.log`

## 执行约定

1. 所有 LLM 调用通过 `PhaseRunner._call_llm()`，自动记录 token 消耗
2. 阶段产物保存到 `~/.murder-wizard/projects/<name>/`
3. session.json 损坏时，`SessionManager.recover_from_files()` 从 md 文件重建状态
4. 阶段跳过逻辑：检查产物文件是否已存在
5. 新增阶段：Stage 枚举 → PhaseRunner 方法 → commands.py 路由 → show_status 产物列表

## 测试

```bash
pytest tests/ -v
# 33 tests: state_machine, session, llm_client, llm_cache
```
