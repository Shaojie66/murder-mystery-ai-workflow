# Murder Mystery CLI Wizard — Design Doc

## Problem Statement

剧本杀创作者有想法但不知道流程，需要一个工具引导他们从想法到完整剧本产出。

## What Makes This Cool

RPG Maker式的交互式向导，把剧本杀创作的完整工作流变成一个对话式CLI。用户回答问题，工具在每个阶段生成内容，最终输出完整的可打印剧本杀项目。

## Constraints

- v1: CLI only
- 基于现有工作流文档构建
- 使用现有LLM API（Claude/GPT），不微调模型

## Premises

1. Target user: 有想法但不知道创作流程的人，CLI舒适度高
2. 核心循环: 类型选择 → 引导问答 → 类型特定输出
3. v1仅CLI，验证后考虑网页
4. Prompt框架而非微调模型

## Recommended Approach

**CLI Interview Wizard** (Effort: M — 1-2 weeks)

交互式问答CLI，RPG Maker式体验：
1. `murder-wizard init` 启动向导
2. 选择剧本类型（情感/机制/推理）
3. 基于类型自适应问答流程
4. 每阶段生成内容并保存到项目目录
5. 最终输出完整剧本杀项目文件夹

技术栈: **Python + Click** — 最简洁的CLI框架，与现有workflow文档同语言

### 状态机

```
IDLE → TYPE_SELECT → STORY_BRIEF → CHARACTER_DESIGN → PLOT_BUILD → ASSET_PROMPT → OUTPUT
```

| 状态 | 输入 | LLM调用 | 输出文件 |
|------|------|---------|---------|
| TYPE_SELECT | 类型选择（情感/机制/推理） | 系统提示词模板 | - |
| STORY_BRIEF | 背景/主题/时代 | 背景生成prompt | `outline.md` |
| CHARACTER_DESIGN | 6个角色基础信息 | 角色生成prompt | `characters.md` |
| PLOT_BUILD | 核心事件/冲突 | 剧本结构prompt | `plot.md` |
| ASSET_PROMPT | 角色描述 | 图像提示词prompt | `image-prompts.md` |
| OUTPUT | 汇总所有 | 完成状态 | `project.json` |

### 输出目录结构

```
my-murder-mystery/
├── murder-wizard-session.json   # wizard进度（可恢复）
├── outline.md                  # 故事大纲
├── characters.md               # 6角色设定
├── plot.md                     # 剧本结构
├── image-prompts.md            # 视觉提示词
└── materials/                  # 物料目录（用户自行填充）
    ├── 角色图/
    ├── 海报/
    └── 卡牌/
```

### 错误处理

- API失败: 重试3次，提示用户检查网络/API配额
- Ctrl+C: 保存当前进度到 `murder-wizard-session.json`，下次可恢复
- 部分生成失败: 保存已成功部分，提示用户重试该阶段

## Open Questions

- ~~CLI框架选型~~ → **Python + Click** 已选定
- API密钥管理: 环境变量 `MURDER_WIZARD_API_KEY`
- ~~项目输出格式~~ → **固定目录结构** 已选定

## Success Criteria

- 用户运行 `murder-wizard init`，进入问答流程
- 完成问答后生成完整的项目文件夹
- 项目文件夹包含: `outline.md`, `characters.md`, `plot.md`, `image-prompts.md`
- 可以在15分钟内完成一个基础剧本的框架

## Distribution Plan

GitHub Releases + `pip install murder-wizard`

## Next Steps

1. CLI框架选型并搭建脚手架 → **Python + Click**
2. 设计问答流程状态机（type → questions → generation → output）
3. 将现有workflow文档的prompt提取为可调用函数
4. 实现第一个阶段: 类型选择 + 基本信息收集
5. 集成LLM API，生成角色模板
