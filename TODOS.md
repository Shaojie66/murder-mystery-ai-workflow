# TODOS

## murder-wizard CLI 开发

### P1

- [ ] **TODO 0: 定义 expand 操作规范** ⭐来自 outside voice
  expand 操作的完整契约：扩展单位（outline→scene？character→full script？）、保留字段（哪些不可变）、可扩展字段（哪些可新生成）、幂等性（多次expand结果是否一致）、依赖传播（展开角色背景是否更新动机/线索/时间线）。
  **Effort**: S | **Depends**: 无，第一批前必须完成

- [ ] **TODO 1: 实现轻量穿帮检查**
  在阶段2的 LLM 生成后，自动检测明显穿帮（角色提及当时不知道的信息）。
  采用 dual-llm 架构：主 LLM 生成内容，轻量 LLM 做快速穿帮检测。
  **Effort**: S | **Depends**: 阶段2 prompt 开发完成

- [ ] **TODO 2: 实现完整 audit 命令**
  `murder-wizard audit` 全量检测，基于信息矩阵深度分析穿帮。
  每次阶段2完成后提示运行，用户可在上线前独立诊断。
  **Effort**: M | **Depends**: TODO 1

### P2

- [ ] **TODO 3: LLM 调用缓存**
  相同输入（stage + user input）缓存结果到本地 JSON，避免重复 API 调用。
  **Effort**: S | **Depends**: 无

- [ ] **TODO 4: 并发控制**
  expand 时控制多角色并行生成的速度，避免触发 API 速率限制。
  **Effort**: S | **Depends**: expand 实现

- [ ] **TODO 5: 本地 Ollama 支持**
  支持用户配置本地 LLM（Ollama），保护隐私，不依赖云端 API。
  **Effort**: M | **Depends**: 第一批发布后

---

## 记录

创建于 2026-03-30（CEO Review 后）
