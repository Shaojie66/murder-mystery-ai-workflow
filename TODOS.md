# TODOS

## murder-wizard CLI 开发

### P1

- [x] **TODO 0: 定义 expand 操作规范** ⭐来自 outside voice (已实现)
  完整契约定义于 `docs/expand-spec.md`。

- [ ] **TODO 1: 实现轻量穿帮检查**
  在阶段2的 LLM 生成后，自动检测明显穿帮（角色提及当时不知道的信息）。
  采用 dual-llm 架构：主 LLM 生成内容，轻量 LLM 做快速穿帮检测。
  **Effort**: S | **Depends**: 阶段2 prompt 开发完成

- [x] **TODO 1: 实现轻量穿帮检查** (已实现)
  阶段2角色剧本生成后自动触发 `_run_consistency_check()`，检测角色与信息矩阵的明显矛盾。
  结果保存为 `consistency_report.md`。
  **Effort**: S

- [ ] **TODO 2: 实现完整 audit 命令**
  `murder-wizard audit` 全量检测，基于信息矩阵深度分析穿帮。
  每次阶段2完成后提示运行，用户可在上线前独立诊断。
  **Effort**: M | **Depends**: TODO 1

### P2

- [x] **TODO 3: LLM 调用缓存** (已实现)
  `LLMCache` 类基于 SHA256(prompt+system+operation+model) 缓存 LLM 响应。
  缓存在项目目录 `cache.json`，`murder-wizard cache <name>` 查看统计，`--clear` 清空。
  **Effort**: S

- [ ] **TODO 4: 并发控制**
  expand 时控制多角色并行生成的速度，避免触发 API 速率限制。
  **Effort**: S | **Depends**: expand 实现

- [ ] **TODO 5: 本地 Ollama 支持**
  支持用户配置本地 LLM（Ollama），保护隐私，不依赖云端 API。
  **Effort**: M | **Depends**: 第一批发布后

---

## 记录

创建于 2026-03-30（CEO Review 后）
