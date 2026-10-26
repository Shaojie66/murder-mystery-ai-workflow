# TODOS

## 当前迭代：本地可靠性 MVP（2026-10-24）

有效范围、依赖与验收以 [实施方案](./docs/reliability-mvp-plan.md) 为准。批次 A 已于 2026-10-26 验收；B/C/D 尚未实施。

### 批次 A：生成契约

- [x] **R01：隔离逐步 Prompt 与必填输入。** 每步仅含当前任务，存在残留变量时调用前失败。（2026-10-26 验收：阶段 2 六步独立模板 + 严格渲染）
- [x] **R02：合法矩阵才能保存为有效结果。** 示例对齐现有 schema；拒绝缺角色、缺事件、非法引用和默认全“否”降级，保留原有效产物。（已验收；非法响应的缓存会被剔除，矩阵写入为临时文件+替换）
- [x] **A 验收。** 全量 Python 回归 584 项通过（基线 120）；三轮对抗审查 + 收尾核验；不迁移现有作品。已知遗留：阶段 2 末尾轻量穿帮检查（归批次 B）、information_matrix.md 仍为普通写入。

### 批次 B：扩写与审计（依赖 A）

- [x] **R05/R06：完整材料审计与作者控制。** 纳入 a/b 本、DM、结局和矩阵；格式错误不算通过，P0 按实际问题计数，默认不自动覆盖角色正文。（2026-10-26 验收：`wizard/audit.py`；只读，修复仅在交互终端由作者选择后写入并备份）
- [x] **R03/R04：完整六人扩写。** 保留原两位角色约束，候选材料全量校验，部分失败不切完整版；JSON 与角色材料保持一致。（2026-10-26 验收：19 步内存候选 + 确认 + 备份回滚）
- [x] **B 验收。** 全量 738 项通过（基线 120）；覆盖表格 P0、审计缺材料、扩写任一步失败、降级路径移除及写入异常回滚。未做：真实模型试跑；未经对抗审查循环（仅自测）；Web 一键 expand 在批次 C 之前会明确失败（无确认入口）；`llm/client.py` 4096 输出上限未处理。

### 批次 C：入口与 Web（依赖 A/B）

- [x] **R07/R08：SSE 与任务结果合同。** JSON 事件、完整终态、单一状态来源、非阻塞执行、取消语义、反馈分析贯通；失败不显示完成。（2026-10-26：`core/sse_manager.py` 单一任务对象；引擎在线程中运行；`end` 终态事件 status=success|failed|cancelled；`analyze` 已接到 `PhaseRunner.run_stage_4_analyze`；前端以终态事件为准）
- [x] **R09：包导入可移植。** 消除对机器专属绝对软链接的运行依赖；删除软链接本身另行确认。（运行时代码已不再经 `murder_wizard.core/api` 软链接导入；两个软链接仍在原处，待你批准后再删）
- [x] **R10：初始化、恢复、PDF 成功判定。**（部分：必要 PDF 缺失判失败且不推进阶段；resume 恢复后落盘；init --type 改为真实五种类型。未处理：init 目录/模型选择的其余不一致） 初始化可继续，恢复可重新载入，必要 PDF 缺失不能标记成功。
- [x] **C 验收。**（751 项 Python 通过；前端构建通过；未做浏览器端人工点检；扩写的 Web 确认为 window.confirm + accept_overwrite 查询参数） HTTP 到前端的跨层合同、Python 全量回归与前端构建；仅使用临时项目和模拟模型。

### 批次 D：试点准备（核心闭环验收后）

- [x] **R11：留资与实验合同。** 修复 JSON 提交 422、分流与 PV 计数；没有可靠持久化和完整研究安排前不启动外部实验。（2026-10-26：留资接受 JSON，无效邮箱 422，同邮箱只计一次；分流按访客 id 稳定；访问数按 visit_id 去重，page_leave 不算访问；数据仍只在内存。未做：持久化、外部实验）
- [ ] **真人验证准备。** 落实 6 位目标作者、独立评审和真实六人试玩；组织、联系、资料收集、模型费用与付费试点另行授权。
- [x] **R12（文档部分）：公网/多用户前置评审。** 真实身份、项目归属与授权、设置隔离、数据持久化和成本控制；本轮不实施 SaaS。已把现状与前置评审清单写入 [docs/local-only-boundary.md](./docs/local-only-boundary.md)；评审项本身未实施。

### 后续候选，尚未批准

- 持久化作品版本、manifest/journal、依赖过期标记和旧作品迁移。
- 云端账号与同步、实时协作、支付、订阅权益、模板市场、发行和移动端扩展。

## 历史实现记录

以下勾选只保留早期“已实现”的记录，不代表当前可靠性验收通过。与本轮复现不一致时，以上方未完成任务及实施方案为准。

## murder-wizard CLI 开发

### P1

- [x] **TODO 0: 定义 expand 操作规范** ⭐来自 outside voice (已实现)
  完整契约定义于 `docs/expand-spec.md`。

- [x] **TODO 1: 实现轻量穿帮检查** (已实现)
  阶段2角色剧本生成后自动触发 `_run_consistency_check()`，检测角色与信息矩阵的明显矛盾。
  结果保存为 `consistency_report.md`。
  **Effort**: S

- [x] **TODO 2: 实现完整 audit 命令** (已实现)
  `murder-wizard audit` 全量深度检测，基于信息矩阵逐格核对。
  三轮 LLM 分析：矩阵逐格审计 + 机制一致性审计 + 结局合理性审计。
  生成 `audit_report.md`，建议在上线前独立运行。
  **Effort**: M | **Depends**: TODO 1（轻量穿帮检查作为基础）

### P2

- [x] **TODO 3: LLM 调用缓存** (已实现)
  `LLMCache` 类基于 SHA256(prompt+system+operation+model) 缓存 LLM 响应。
  缓存在项目目录 `cache.json`，`murder-wizard cache <name>` 查看统计，`--clear` 清空。
  **Effort**: S

- [x] **TODO 4: 并发控制** (已实现)
  `RateLimiter` 类基于信号量控制并发数（默认 max_concurrent=2）。
  expand 从单次 LLM 调用改为两阶段：Phase1 扩写事件线 + Phase2 并行生成4个新角色剧本。
  `murder_wizard/llm/rate_limit.py`，7个测试。
  **Effort**: S

- [x] **TODO 5: 本地 Ollama 支持** (已实现)
  `OllamaAdapter`（`murder_wizard/llm/client.py`）：Ollama 本地 LLM 适配器。
  OpenAI 兼容 API 端点（http://localhost:11434/v1），零 API 成本。
  通过环境变量配置：`LLM_PROVIDER=ollama`、`OLLAMA_BASE_URL`、`OLLAMA_MODEL`。
  **Effort**: M

---

## 记录

创建于 2026-03-30（CEO Review 后）
