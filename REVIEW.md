# Engineering Review: murder-wizard

Date: 2026-04-01
Reviewer: /plan-eng-review
Scope: Full codebase architecture, security, test coverage, code quality

---

## 1. Architecture

### Data Flow

```
CLI / Web UI
    │
    ▼
┌─────────────────────────────────────────────────────────────┐
│ PhaseRunner / PhaseRunnerWeb                                │
│  ┌──────────────────────────────────────────────────────┐   │
│  │ PromptLoader (templates from prompts/ directory)     │   │
│  └──────────────────────────────────────────────────────┘   │
│    │                                                         │
│    ▼                                                         │
│  ┌──────────────────────────────────────────────────────┐   │
│  │ LLM Adapter (Claude/OpenAI/MiniMax/Ollama)           │   │
│  │  - complete() → LLMResponse                          │   │
│  │  - complete_streaming() → Iterator[str]               │   │
│  └──────────────────────────────────────────────────────┘   │
│    │                                                         │
│    ▼                                                         │
│  ┌──────────────────────────────────────────────────────┐   │
│  │ LLMCache (cache.json per project)                    │   │
│  └──────────────────────────────────────────────────────┘   │
│    │                                                         │
│    ▼                                                         │
│  ┌──────────────────────────────────────────────────────┐   │
│  │ SessionManager (session.json)                         │   │
│  │  - save(state) → atomic write                        │   │
│  │  - load() → MurderWizardState                        │   │
│  └──────────────────────────────────────────────────────┘   │
│    │                                                         │
│    ▼                                                         │
│  ┌──────────────────────────────────────────────────────┐   │
│  │ File System (~/.murder-wizard/projects/<name>/)     │   │
│  │  - mechanism.md, characters.md, information_matrix.md│   │
│  └──────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────────────────────────────┐
│ MurderWizardState (State Machine)                           │
│  - Stage enum (15 states across 2 lineages)                 │
│  - can_advance_to() / advance_to()                        │
│  - to_dict() / from_dict() serialization                  │
└─────────────────────────────────────────────────────────────┘
```

### State Machines

**Lineage 1 — Legacy 7-stage (no active runner):**
```
IDLE(0) → TYPE_SELECT(1) → STORY_BRIEF(2) → CHARACTER_DESIGN(3)
                                              ↓
                                        PLOT_BUILD(4)
                                              ↓
                                        ASSET_PROMPT(5)
                                              ↓
                                          OUTPUT(6)
```

**Lineage 2 — Current 8-stage (active runner):**
```
STAGE_1_MECHANISM(7) → STAGE_2_SCRIPT(8) → STAGE_3_VISUAL(9)
                                                  ↓
                      STAGE_4_TEST(10) ← ─ ─ ─ ─ ┘
                          │
              STAGE_5_COMMERCIAL(11)
                          │
                    STAGE_6_PRINT(12)
                          │
                    STAGE_7_PROMO(13)
                          │
               STAGE_8_COMMUNITY(14)
```

**Transition Map:**
```python
IDLE              → [TYPE_SELECT]
TYPE_SELECT       → [STORY_BRIEF, STAGE_1_MECHANISM]
STORY_BRIEF       → [CHARACTER_DESIGN, STAGE_1_MECHANISM]
CHARACTER_DESIGN  → [PLOT_BUILD, STAGE_2_SCRIPT]
PLOT_BUILD        → [ASSET_PROMPT, STAGE_3_VISUAL]
ASSET_PROMPT      → [OUTPUT]
OUTPUT            → [STAGE_4_TEST]
STAGE_1_MECHANISM → [STAGE_2_SCRIPT]
STAGE_2_SCRIPT    → [STAGE_3_VISUAL]
STAGE_3_VISUAL    → [STAGE_4_TEST]
STAGE_4_TEST      → [STAGE_5_COMMERCIAL]
STAGE_5_COMMERCIAL→ [STAGE_6_PRINT]
STAGE_6_PRINT     → [STAGE_7_PROMO]
STAGE_7_PROMO     → [STAGE_8_COMMUNITY]
STAGE_8_COMMUNITY → []
```

### Error Paths

```
LLM Call Failure
  ├─ RateLimitError → exponential backoff retry (3 attempts)
  ├─ Other Exception → propagate, stage fails
  └─ All retries exhausted → stage returns False, user sees error message

File I/O Failure
  ├─ session.json corrupt/missing → load() returns None
  │   └─ recover_from_files() tries to rebuild from artifacts
  ├─ cache.json corrupt → LLMCache._load() catches JSONDecodeError, resets to {}
  └─ Artifact file write fails → atomic write via temp + rename pattern

State Machine Corruption
  ├─ Invalid stage value in session.json → Stage.from_value() raises ValueError
  │   └─ caught by session.load(), returns None
  ├─ Invalid transition → advance_to() raises ValueError
  └─ JSONDecodeError on load → session.load() returns None

SSE Connection Failure
  ├─ Client disconnects → asyncio.CancelledError → cleanup in finally block
  ├─ Queue full → asyncio.QueueFull caught, event dropped silently
  └─ Timeout (60s) → keepalive comment sent

Phase Runner Web
  ├─ Project not found → emit error event
  ├─ Phase runner exception → emit error event, return False
  └─ Cancel → sets _cancelled flag, runner checks and exits early
```

---

## 2. Test Matrix

**Total: 90 tests passing**

| Test File | # Tests | Phase Coverage | Failure Modes Tested |
|-----------|---------|---------------|---------------------|
| `test_state_machine.py` | 14 | All stages | Invalid transitions, to_dict/from_dict, stage ordering |
| `test_session.py` | 12 | Persistence | Save/load, corrupt JSON, missing file, recover_from_files |
| `test_llm_client.py` | 10 | LLM adapters | Invalid provider, token cost calc, Ollama init/estimate |
| `test_llm_cache.py` | 7 | LLM caching | Cache miss, set/get, different operation/prompt/system, clear, stats, persistence |
| `test_rate_limit.py` | 7 | Concurrency | Parallel execution, semaphore limits, ordering, delay, error handling |
| `test_truth_files.py` | 17 | Phase 2 (matrix) | Matrix create/save/load, delta generate/apply, backup, audit_completeness, audit_killer, migrate_from_markdown, schema validation |
| `test_prompt_loader.py` | 19 | Prompt rendering | Load/cache, variable substitution, is_prototype modes, fill_rules, matrix_table, consistency rounds, system prompts per type |
| `test_commands.py` | 1 | Status display | Stage ordering in status table |
| `test_expand_types.py` | 3 | Expand operation | Type-specific prompts for expand Phase 1, Phase 2 parse chars, char tasks |
| `test_api_integration.py` | 6 | Web API | Project CRUD, phase status, cancel, auth |

**Gaps:**

| Area | Gap | Severity |
|------|-----|----------|
| Phase 1-8 actual execution | No end-to-end phase runner tests | P1 |
| LLM hallucination/invalid output | No tests for malformed JSON extraction | P1 |
| Path traversal in API | No tests for `../` in project names | P0 |
| JWT auth | No tests for token expiry, invalid signatures | P1 |
| `can_advance_to()` external usage | Defined and tested but never called externally | P1 |
| Phase 2 skip logic mismatch | Only checks `characters.md`, ignores other 5 artifacts | P1 |
| SSE streaming | No tests for SSE connection lifecycle | P2 |
| RateLimiter thread safety | No stress tests for concurrent access | P2 |
| Audit Reviser loop | No tests for Auditor→Reviser→Re-audit cycle | P1 |

---

## 3. Failure Modes

### Phase 1 (STAGE_1_MECHANISM)
- LLM hallucination in Q1/Q2/Q3 outputs
- Wrong template selected for story_type
- Q2 output not valid markdown for mechanism.md

### Phase 2 (STAGE_2_SCRIPT)
- Malformed JSON in Q1 matrix → fallback to markdown migration
- JSON fails `CharacterMatrix.model_validate()` → migrates from markdown
- Q3 (a本) fails or produces inconsistent content with matrix
- Six artifacts: `information_matrix.md`, `background.md`, `characters.md`, `scripts_b.md`, `dm_manual.md`, `endings.md`
- **P1 Bug:** Skip check only verifies `characters.md` — other 5 could be missing from interrupted run

### Phase 3-8
- Each phase can fail at LLM call level
- Skip-if-exists checks per artifact
- Phase 6 PDF generation may fail if reportlab not installed

### Expand Operation
- Phase 1 expand fails
- Phase 2 parse chars fails → falls back to single-pass
- Concurrent character generation: some fail, others succeed

---

## 4. Security Concerns

**[P0] Hardcoded JWT SECRET_KEY**
- File: `murder_wizard_web/backend/core/auth.py:8`
- Code: `SECRET_KEY = "murder-wizard-secret-key-change-in-production"`
- Impact: Anyone can forge valid JWT tokens → create/read/delete any project
- Fix: Load from env var `JWT_SECRET_KEY` with error if not set in production

**[P0] Path traversal in DELETE /api/projects/{name}**
- File: `murder_wizard_web/backend/api/projects.py:243-249`
- `project_path = MURDER_WIZARD_BASE / name` — no validation of name
- `shutil.rmtree(project_path)` — arbitrary directory deletion
- Fix: Validate `name` in all project endpoints, reject `..`, absolute paths, slashes

**[P0] Path traversal in GET /api/projects/{name}**
- File: `murder_wizard_web/backend/api/projects.py:191-196`
- Same issue — could read arbitrary files
- Fix: Same as above

**[P1] CORS allows all origins with credentials**
- File: `murder_wizard_web/backend/main.py:17-23`
- `allow_origins=["*"]` with `allow_credentials=True`
- Impact: Any website can make authenticated requests
- Fix: Restrict to specific origins via `ALLOWED_ORIGINS` env var

**[P1] API key masking incomplete**
- File: `murder_wizard_web/backend/api/settings.py:64-67`
- Key echoed back in responses; ObsidianConfig vault_path not masked
- Fix: Use `***` placeholder, never echo keys back

**[P2] Ollama remote URL warning only prints to stderr**
- File: `murder_wizard/llm/client.py:287-295`
-剧本杀 content sent to remote Ollama server — user not meaningfully warned
- Fix: Require `OLLAMA_NO_URL_WARN=1` to explicitly allow remote

**[P2] API key in environment variables logged in stack traces**
- File: Multiple adapter `__init__` methods
- Fix: Sanitize error messages to exclude credential info

---

## 5. Code Quality

**[P1] Phase 2 skip logic only checks `characters.md`**
- File: `murder_wizard/cli/phase_runner.py:210`
- Impact: Interrupted Phase 2 run leaves 5 of 6 artifacts missing
- Fix: Check all 6 artifacts before skipping

**[P1] `can_advance_to()` never called externally**
- File: `murder_wizard/wizard/state_machine.py:66-86`
- Method defined, tested (2 tests), but only caller is `advance_to()` itself
- Fix: Integrate into PhaseRunner or remove

**[P1] Unused import in `phase_runner_web.py`**
- File: `murder_wizard_web/backend/core/phase_runner_web.py:14`
- `from murder_wizard.wizard.truth_files import TruthFileManager` — imported but never used
- Fix: Remove

**[P2] Magic numbers duplicated across 4 adapter files**
- `max_tokens=4096` duplicated in ClaudeAdapter, OpenAIAdapter, MiniMaxAdapter, OllamaAdapter
- `max_retries=3`, `base_delay=2` duplicated
- Claude pricing `$3/$15` per MTok hardcoded
- Fix: Extract to module-level constants

**[P2] `ollama.py` client uses `print()` instead of `logging`**
- File: `murder_wizard/llm/client.py:288-294`
- Fix: Use `logging.warning()`

**[P2] `_load_settings_from_file()` swallows all exceptions**
- File: `murder_wizard/llm/client.py:384-387`
- Fix: Log or be more specific about expected exceptions

**[P2] `recover_from_files()` wrong artifact priority**
- File: `murder_wizard/wizard/session.py:109-110`
- `if plot_file.exists(): state.current_stage = Stage.PLOT_BUILD` — priority order is wrong
- Fix: Check all artifacts, set to highest stage that exists

**[P2] `_build_expand_phase1_prompt()` not using PromptLoader**
- File: `murder_wizard/cli/phase_runner.py:695-720`
- Raw f-string instead of template system
- Fix: Move to prompt template file

**[P2] Module import inside try block**
- File: `murder_wizard/cli/phase_runner.py:1414`
- `from murder_wizard.print.pdf_gen import PDFGenerator` inside try
- Fix: Move to top of file

---

## 6. Recommendations

### Priority 1 (Critical — Fix Immediately)
1. Fix hardcoded JWT SECRET_KEY → env var with required check
2. Fix path traversal in API project endpoints → name validation

### Priority 2 (High — Fix Before Production)
3. Fix Phase 2 skip logic → check all 6 artifacts
4. Extract magic numbers to constants
5. Restrict CORS origins via env var
6. Integrate or remove `can_advance_to()`
7. Add missing test coverage (JWT, path traversal, end-to-end)

### Priority 3 (Medium — Fix in Next Sprint)
8. Use `logging` instead of `print()` for Ollama warning
9. Fix `recover_from_files()` stage priority
10. Move `_build_expand_phase1_prompt()` to PromptLoader
11. Block remote Ollama with env var
12. Sanitize error messages to exclude API keys
