# TODOS

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

- [ ] **TODO 5: 本地 Ollama 支持**
  支持用户配置本地 LLM（Ollama），保护隐私，不依赖云端 API。
  **Effort**: M | **Depends**: 第一批发布后

---

## 记录

创建于 2026-03-30（CEO Review 后）
