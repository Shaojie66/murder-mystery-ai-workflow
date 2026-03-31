# CHANGELOG

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).

## [0.6.0] - 2026-03-31

### Added

#### JSON Truth File 系统
- `TruthFileManager`（`murder_wizard/wizard/truth_files.py`）：JSON 真相文件管理器
  - Pydantic 验证 + 每次写入自动备份（immutable history）
  - Delta 生成（增量更新，避免 context window bloat）
  - Markdown 迁移（从 `information_matrix.md` 迁移到 JSON）
  - 审计 helpers（角色认知完整性、凶手知识充足性）
- `schemas.py`（`murder_wizard/wizard/schemas.py`）：Pydantic 模型
  - `CharacterMatrix`：角色×事件信息矩阵
  - `TruthDelta`：增量更新格式（add/update/delete/replace）
  - `GameState`、`PendingHooksFile`、`ChapterSummariesFile` 等

#### Reviser 自动修复循环
- `run_audit()` 重构：Auditor → Reviser → Re-audit 循环（最多3轮）
- 每轮运行三轮审计：信息矩阵 / 机制一致性 / 结局合理性
- 发现 P0 问题 → Reviser 自动修复 → 重新审计
- `05_reviser.md`：Reviser prompt 模板
- `02_script_generation.md`：新增结构化 JSON 输出说明

#### Design Context
- `.impeccable.md`：设计决策文档（用户、Brand Personality、Aesthetic Direction、Design Principles）
- `CLAUDE.md` 新增 Design Context 小节

#### 测试
- `tests/test_truth_files.py`：13 个测试（TruthFileManager、CharacterMatrix、Delta、Reviser helpers）

### Fixed

- `_extract_json_from_response`（`phase_runner.py`）：正则只匹配一层嵌套 JSON，替换为 brace-counting 算法正确处理多层嵌套
- `add_evidence`（`truth_files.py`）：方法返回 matrix 但从未持久化，替换为 `add_evidence_to_matrix` 原子写入
- `information_matrix_json`（`loader.py`）：与 `information_matrix` 完全相同（未实现 JSON-only 模式），添加 `{{#if json_only}}` 条件模板块
- `_apply_op`（`truth_files.py`）：条件 `op.op == "update" and op.op in ["add","update"]` 永远为 False，修复为 `op.op in ["add","update","replace"]`
- `_count_p0_issues`（`phase_runner.py`）：正则遗漏常见 LLM 输出格式（P0：3、P0（3）、P0问题3个等），扩展 pattern 列表
- 死方法 `_summarize_audit_issues`（`phase_runner.py`）：AST 分析发现定义但从未调用，已移除

---

## [0.5.0] - 2026-03-30

### Added

#### 本地 Ollama 支持
- `OllamaAdapter`（`murder_wizard/llm/client.py`）：Ollama 本地 LLM 适配器
- OpenAI 兼容 API 端点（http://localhost:11434/v1），无需额外部署
- 零 API 成本，保护隐私，适合开发和测试
- 通过环境变量配置：`LLM_PROVIDER=ollama`、`OLLAMA_BASE_URL`、`OLLAMA_MODEL`

---

## [0.4.0] - 2026-03-30

### Added

#### expand 并发控制
- `RateLimiter`（`murder_wizard/llm/rate_limit.py`）：信号量控制并发数，限制同时进行的 API 调用
- expand 改为两阶段：Phase1 扩写事件线和信息矩阵 + Phase2 并行生成4个新角色剧本
- 默认 max_concurrent=2，delay_between_calls=1.0s（尊重 API 限制）
- 降级路径：无法解析新角色时自动回退到单次扩写

#### RateLimiter 测试
- `tests/test_rate_limit.py`：7个测试（并发数/延迟/错误隔离/顺序保证）

---

## [0.3.0] - 2026-03-30

### Added

#### 完整 audit 审计命令
- `murder-wizard audit <name>`：完整穿帮审计（独立命令，不自动触发）
- 三轮深度 LLM 分析：信息矩阵逐格审计 + 机制一致性审计 + 结局合理性审计
- 生成 `audit_report.md`，含 P1/P2/P3 问题分级和修复优先级表
- 建议在上线前独立运行

---

## [0.2.0] - 2026-03-30

### Added

#### LLM 缓存
- `LLMCache`（`murder_wizard/llm/cache.py`）：基于 SHA256(prompt+system+operation+model) 缓存 LLM 响应
- 缓存在项目目录 `cache.json`，避免重复 API 调用
- `murder-wizard cache <name>`：查看缓存统计
- `murder-wizard cache <name> --clear`：清空缓存

#### 轻量穿帮检查
- 阶段2角色剧本生成后自动触发 `_run_consistency_check()`
- 检查角色与信息矩阵的明显矛盾（时间线/知识盲区/秘密泄露）
- 结果保存为 `consistency_report.md`

#### 文档
- `docs/expand-spec.md`：expand 操作完整规范（扩展单位/保留字段/幂等性/限制）

#### 测试
- `tests/test_llm_cache.py`：8 个缓存测试
- 全部 33 个测试通过

---

## [0.1.0] - 2026-03-30

### Added

#### murder-wizard CLI 工具

- `murder_wizard` Python 包，setuptools 发版
- 8 个 Click 命令：`init`、`status`、`phase`、`expand`、`resume`
- `PhaseRunner` 阶段执行器，支持全部 8 阶段 LLM 调用
- `PDFGenerator`：reportlab 生成剧本 PDF + 线索卡 PDF
- `SessionManager`：JSON 持久化 + cost.log API 消耗记录
- 状态机：Stage 枚举（7 个遗留状态 + 8 个新状态）
- 原型模式：2 人 + 3 事件，expand 扩写为 6 人 + 5-7 事件

#### 测试

- `tests/test_state_machine.py` — 13 个测试
- `tests/test_session.py` — 11 个测试
- `tests/test_llm_client.py` — 5 个测试
- 全部 25 个测试通过

#### 标准仓库文件

- `.gitignore` — Python 标准忽略规则
- `LICENSE` — MIT 许可证
- `CONTRIBUTING.md` — 贡献指南
- `pyproject.toml` — 完整元数据（keywords、classifiers、urls）
- 重写 `README.md` — CLI 工具导向，含快速开始、命令表、工作流图

### Fixed

- `session.py recover_from_files()`：错误使用 `state.Stage` → 修正为模块级 `Stage` 导入
- `phase_runner.py`：修复两个未关闭的 f-string 多行 triple-quote

---

## [2.0.0] - 2026-03-30

### Added

#### 新增文档
- `docs/04_用户测试.md` - 用户测试流程详解（P0/P1/P2问题分类）
- `docs/05_商业化.md` - 商业化路径（成本核算、定价策略、销售渠道）
- `docs/06_印刷生产.md` - 印刷生产全流程（打样、量产、质检）
- `docs/07_宣发内容.md` - Dan Koe流量方法论（内容矩阵、平台策略）
- `docs/08_社区运营.md` - 社区运营（社群搭建、反馈闭环、扩展包）
- `docs/09_项目管理.md` - 项目管理（甘特图、风险管理、里程碑）

#### 新增模板
- `templates/用户测试报告.md` - 用户测试报告模板
- `templates/成本核算表.md` - 成本核算表模板
- `templates/宣发排期表.md` - 宣发排期表模板
- `templates/社区运营记录.md` - 社区运营记录模板

#### 新增Prompt库
- `prompts/机制研究.md` - 4个机制研究Prompt（原创构思、规则书改编、平衡性验证、扩展建议）
- `prompts/剧本生成.md` - 6个剧本生成Prompt（背景、a本、b本、DM手册、结局扩展）
- `prompts/穿帮检测.md` - 5个穿帮检测Prompt（全本、单角色、交叉、逻辑漏洞、快速自检）
- `prompts/宣发文案.md` - 7个宣发文案Prompt（小红书、B站、公众号、抖音、Dan Koe风格等）

### Changed

- 扩展工作流从3阶段到8阶段（14-16周完整生命周期）
- 更新CLAUDE.md目录结构
- 更新README.md工作流展示

---

## [1.0.0] - 2026-03-30

### Added

- 项目概览文档
- 机制设计文档（Gemini研究 + 规则书改编）
- 剧本创作文档（六视角信息差管理）
- 视觉物料文档（即梦AI生图技巧）
- 项目时间线（12周甘特图）
- 执行清单模板
- 角色设定模板
- 信息矩阵表模板
- 游戏大纲模板
- 完整版集成文档

### Known Issues

- 暂无

---

## Template Changelog

```markdown
## [版本号] - YYYY-MM-DD

### Added
- 新增功能

### Changed
- 功能变更

### Deprecated
- 废弃功能

### Removed
- 删除功能

### Fixed
- 修复问题

### Security
- 安全相关
```
