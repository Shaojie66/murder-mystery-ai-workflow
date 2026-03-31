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

## 5 类剧本杀类型

支持 5 种剧本杀类型，每种有独立的 Prompt 模板和工作流：

| 类型 | 英文 | 核心特点 | 关键词 |
|------|------|----------|--------|
| 情感本 | emotion | 情感弧线、角色成长、两难抉择 | 情感共鸣、关系动态 |
| 推理本 | reasoning | 证据链、逻辑推理、公平性验证 | 烧脑、线索交织 |
| 欢乐本 | fun | 社交碰撞、喜剧人设、即兴空间 | 笑点、误会反转 |
| 恐怖本 | horror | 氛围营造、心理压迫、悬念揭示 | 恐惧升级、留白艺术 |
| 机制本 | mechanic | 阵营对抗、策略博弈、平衡性 | 翻盘机制、技能设计 |

类型化 Prompt 模板位置：`murder_wizard/prompts/`

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
│   │   ├── cache.py     # LLM 响应缓存（SHA256 hash）
│   │   └── rate_limit.py # 并发控制器（信号量限流）
│   ├── print/            # PDF 生成
│   │   └── pdf_gen.py   # reportlab PDF 输出
│   ├── assets/           # 第三方 API 适配器（存根）
│   │   └── jimeng.py    # 即梦 AI + 海螺 AI（待集成）
│   └── wizard/           # 核心逻辑
│       ├── session.py    # 会话持久化（JSON）
│       ├── state_machine.py # 状态机（8阶段枚举）
│       ├── schemas.py    # Pydantic 模型（CharacterMatrix, TruthDelta 等）
│       └── truth_files.py # JSON 真相文件管理器
├── tests/                 # pytest 测试（75个，全部通过）
├── docs/                 # 工作流文档（8阶段详解）
├── templates/            # 可复用模板
├── prompts/             # Prompt 库（见 prompts/FRAMEWORK.md）

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

## LLM 配置

通过环境变量选择 LLM provider：

| 环境变量 | 默认值 | 说明 |
|---------|--------|------|
| `LLM_PROVIDER` | `claude` | `claude` / `openai` / `ollama` |
| `OLLAMA_BASE_URL` | `http://localhost:11434/v1` | Ollama 服务地址 |
| `OLLAMA_MODEL` | `llama3` | Ollama 模型名 |

Ollama 优势：本地运行，零 API 成本，保护隐私。推荐用于开发和测试。

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
# 75 tests: state_machine, session, llm_client, llm_cache, rate_limit, truth_files
```

## Design Context

### 用户
剧本杀创作者 — 有创作热情但对完整流程不熟悉，CLI 舒适度高。
在电脑前工作，用 terminal 运行工具，最终产出印刷用 PDF。
Job to be done：从一个创意想法出发，通过引导式问答 + AI 辅助，产出一套完整的、可印刷的剧本杀作品。
Emotional goal：感到"这件事可以做成"，每一步都有成果，不是空转。

### Brand Personality
- **Voice**: 冷静、务实、不废话 — 像个经验丰富的制作人
- **Tone**: 专业感体现在每个细节（输出文件的排版、prompt 的质量、一致的状态显示），而不是包装
- **3-word personality**: 专业、可靠、有章法
- **Emotional goal**: 用户信任这个工具能帮他们把剧本做出来，而不是"看起来很酷但用起来失望"

### Aesthetic Direction
- **Visual medium**: Terminal UI (Rich library) — 非 GUI，无 CSS/网页
- **Color usage**: 功能性色彩（状态：green=完成 yellow=进行中 red=错误 cyan=标题），不多余装饰
- **参考**: YC Office Hours 的问答风格 — 结构清晰、尊重用户时间
- **Anti-reference**: 不要游戏化/动画过多的 CLI，不要过度表情包化

### Design Principles

1. **专业感来自克制**
   - TUI 不需要花哨的 ASCII art 或渐变色
   - Rich Panel/Table/Markdown 足以传达层次
   - 颜色用于状态识别，不是装饰

2. **输出即名片**
   - 每个阶段生成的 .md 文件本身就是专业的工作文档
   - 不是"中间产物"，用户可以直接拿去给合作方看
   - PDF 排版要有正规出版物的样子（字体、留白、标题层级）

3. **流程透明，状态明确**
   - `murder-wizard status` 一眼看清 8 阶段进度和缺失产物
   - 不让用户猜"现在做到哪了"
   - API 消耗透明（cost.log），让用户控制预算

4. **容错与恢复**
   - Ctrl+C 保存进度，`resume` 命令继续
   - session.json 损坏时从 md 文件重建
   - 阶段失败不污染已生成的产物文件

5. **Prompt 质量 = 产出质量**
   - prompt 模板本身是工具的核心资产
   - 定期根据产出质量迭代 prompt（不是改工具本身）
   - 创意简报（brief.md）是所有后续 prompt 的默认上下文，保持一致性
