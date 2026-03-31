"""JSON truth file manager for murder-wizard.

Inspired by inkos: immutable truth files with Zod schema validation,
JSON delta updates, and version tracking.

Truth files live in: ~/.murder-wizard/projects/<name>/state/
"""
from __future__ import annotations

import hashlib
import json
import shutil
from datetime import datetime
from pathlib import Path
from typing import Optional

from pydantic import BaseModel, ValidationError

from murder_wizard.wizard.schemas import (
    CharacterMatrix,
    CharacterEntry,
    CognitiveState,
    EvidenceItem,
    GameState,
    PendingHooksFile,
    ChapterSummariesFile,
    SubplotBoardFile,
    EmotionalArcsFile,
    TruthDelta,
    DeltaOp,
    Meta,
)


class TruthFileManager:
    """Manages all JSON truth files for a project.

    Provides:
    - Load/save with Zod/Pydantic validation
    - Backup on every write (immutable history)
    - Delta generation for incremental updates
    - Migration from old Markdown files
    - Schema version migration
    """

    STATE_DIR = "state"

    def __init__(self, project_path: Path):
        self.project_path = Path(project_path)
        self.state_dir = self.project_path / self.STATE_DIR
        self.state_dir.mkdir(exist_ok=True)

    # ─── File paths ─────────────────────────────────────────────────────────

    def _path(self, name: str) -> Path:
        return self.state_dir / f"{name}.json"

    def _backup_path(self, name: str, timestamp: str) -> Path:
        backup_dir = self.state_dir / ".backups"
        backup_dir.mkdir(exist_ok=True)
        return backup_dir / f"{name}.{timestamp}.json"

    # ─── Generic load/save ──────────────────────────────────────────────────

    def load(self, name: str, schema_class: type) -> Optional[BaseModel]:
        """Load a truth file, validate against schema, return Pydantic model.

        Returns None if file doesn't exist.
        Raises ValidationError if content doesn't match schema.
        """
        path = self._path(name)
        if not path.exists():
            return None

        data = json.loads(path.read_text(encoding="utf-8"))
        return schema_class.model_validate(data)

    def save(self, name: str, model: BaseModel, author: str = "llm", note: str = "") -> None:
        """Save a truth file with backup.

        Creates a timestamped backup before writing.
        Updates meta.updated_at.
        """
        path = self._path(name)

        # Backup existing file
        if path.exists():
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            shutil.copy2(path, self._backup_path(name, timestamp))

        # Update meta
        if hasattr(model, "meta") and model.meta:
            model.meta.updated_at = datetime.now().isoformat()
            model.meta.commit_hash = _git_commit() or "no-git"

        # Write
        content = model.model_dump_json(ensure_ascii=False, indent=2)
        path.write_text(content, encoding="utf-8")

    def exists(self, name: str) -> bool:
        return self._path(name).exists()

    # ─── Character Matrix ────────────────────────────────────────────────────

    def load_matrix(self) -> Optional[CharacterMatrix]:
        return self.load("character_matrix", CharacterMatrix)

    def save_matrix(self, matrix: CharacterMatrix, author: str = "llm", note: str = "") -> None:
        self.save("character_matrix", matrix, author=author, note=note)

    def create_matrix(
        self,
        char_count: int = 6,
        event_count: int = 7,
        is_prototype: bool = False,
        brief_content: str = "",
    ) -> CharacterMatrix:
        """Create a new empty character matrix."""
        char_ids = [f"R{i+1}" for i in range(char_count)]
        event_ids = [f"E{i+1}" for i in range(event_count)]

        characters = {}
        for cid in char_ids:
            characters[cid] = CharacterEntry(
                character_id=cid,
                name="",
                event_cognitions={
                    eid: CognitiveState(state="否", detail="")
                    for eid in event_ids
                },
            )

        meta = Meta(
            created_at=datetime.now().isoformat(),
            updated_at=datetime.now().isoformat(),
            commit_hash=_git_commit() or "no-git",
            brief_content_hash=_sha256(brief_content),
        )

        return CharacterMatrix(
            char_count=char_count,
            event_count=event_count,
            is_prototype=is_prototype,
            characters=characters,
            evidence={},
            meta=meta,
        )

    # ─── Delta updates ───────────────────────────────────────────────────────

    def generate_delta(
        self,
        old_matrix: CharacterMatrix,
        new_matrix: CharacterMatrix,
        author: str = "llm",
        reason: str = "",
    ) -> TruthDelta:
        """Generate a delta between two character matrices.

        Compares old vs new and produces a list of operations.
        This is what inkos calls the "Reflector" output.
        """
        ops = []

        # Character-level changes
        old_chars = set(old_matrix.characters.keys())
        new_chars = set(new_matrix.characters.keys())

        for cid in new_chars - old_chars:
            ops.append(DeltaOp(
                op="add",
                path=f"characters.{cid}",
                new_value=f"CharacterEntry({new_matrix.characters[cid].name or cid})",
                reason=reason,
            ))

        for cid in old_chars - new_chars:
            ops.append(DeltaOp(
                op="delete",
                path=f"characters.{cid}",
                old_value=f"CharacterEntry({old_matrix.characters[cid].name or cid})",
                reason=reason,
            ))

        for cid in old_chars & new_chars:
            old_char = old_matrix.characters[cid]
            new_char = new_matrix.characters[cid]

            # Field-level changes within character
            for field in ["name", "role", "public_relationship"]:
                old_val = getattr(old_char, field, "")
                new_val = getattr(new_char, field, "")
                if old_val != new_val:
                    ops.append(DeltaOp(
                        op="update",
                        path=f"characters.{cid}.{field}",
                        old_value=str(old_val),
                        new_value=str(new_val),
                        reason=reason,
                    ))

            # Event cognition changes
            old_cogs = old_char.event_cognitions
            new_cogs = new_char.event_cognitions

            for eid in set(new_cogs.keys()) | set(old_cogs.keys()):
                old_state = old_cogs.get(eid, CognitiveState(state="否"))
                new_state = new_cogs.get(eid, CognitiveState(state="否"))
                if old_state.state != new_state.state:
                    ops.append(DeltaOp(
                        op="update",
                        path=f"characters.{cid}.event_cognitions.{eid}",
                        old_value=f"{old_state.state}: {old_state.detail}",
                        new_value=f"{new_state.state}: {new_state.detail}",
                        reason=reason,
                    ))

        return TruthDelta(
            target_file="character_matrix",
            timestamp=datetime.now().isoformat(),
            operations=ops,
            author=author,
            reason=reason,
        )

    def apply_delta(self, matrix: CharacterMatrix, delta: TruthDelta) -> CharacterMatrix:
        """Apply a delta to a character matrix, returning a new instance."""
        # Deep copy
        import copy
        updated = copy.deepcopy(matrix)

        for op in delta.operations:
            self._apply_op(updated, op)

        updated.meta.updated_at = datetime.now().isoformat()
        return updated

    def _apply_op(self, matrix: CharacterMatrix, op: "DeltaOp") -> None:
        """Apply a single DeltaOp to a CharacterMatrix."""
        parts = op.path.split(".")
        if len(parts) < 2:
            return

        if parts[0] == "characters" and len(parts) >= 2:
            cid = parts[1]
            if cid not in matrix.characters:
                if op.op == "add":
                    matrix.characters[cid] = CharacterEntry(character_id=cid)
                else:
                    return

            char = matrix.characters[cid]

            if len(parts) == 2:
                # Top-level character operation
                if op.op == "delete":
                    del matrix.characters[cid]
                return

            field = parts[2]

            if field == "event_cognitions" and len(parts) >= 4:
                eid = parts[3]
                if op.op in ["add", "update", "replace"]:
                    # Parse new value: "知: detail" format
                    if ":" in op.new_value:
                        state_str, detail = op.new_value.split(":", 1)
                        char.event_cognitions[eid] = CognitiveState(
                            state=state_str.strip(),
                            detail=detail.strip(),
                        )
                elif op.op == "delete":
                    char.event_cognitions.pop(eid, None)
            elif hasattr(char, field) and op.op in ["add", "update", "replace"]:
                setattr(char, field, op.new_value)

    # ─── Migration from Markdown ──────────────────────────────────────────────

    def migrate_from_markdown(
        self,
        matrix_md: str,
        char_count: int = 6,
        event_count: int = 7,
        is_prototype: bool = False,
    ) -> CharacterMatrix:
        """Parse old Markdown information_matrix.md and create CharacterMatrix JSON.

        This is a best-effort parse — the LLM-generated Markdown is
        not perfectly structured, so we do approximate parsing.
        """
        char_ids = [f"R{i+1}" for i in range(char_count)]
        event_ids = [f"E{i+1}" for i in range(event_count)]

        # Try to parse table from Markdown
        # Format: | | R1 | R2 | ... |
        #         | E1 | 知 | 疑 | ... |
        lines = matrix_md.split("\n")
        char_order = []
        cells: dict[str, dict[str, str]] = {}

        # Find header row to extract character order
        for line in lines:
            if line.startswith("|") and "R1" in line:
                parts = [p.strip() for p in line.split("|")[1:]]
                char_order = [p for p in parts if p.startswith("R")]
                break

        if not char_order:
            char_order = char_ids

        # Parse data rows
        for line in lines:
            if not line.startswith("|") or line.startswith("|---") or "R1" in line:
                continue
            parts = [p.strip() for p in line.split("|")[1:]]
            if not parts:
                continue
            event_id = parts[0].replace("（核心）", "").strip()
            if not event_id.startswith("E"):
                continue

            cells[event_id] = {}
            for i, state_str in enumerate(parts[1:], start=0):
                if i < len(char_order):
                    cells[event_id][char_order[i]] = state_str

        # Build CharacterMatrix
        characters: dict[str, CharacterEntry] = {}
        for cid in char_ids:
            eid_cogs: dict[str, CognitiveState] = {}
            for eid in event_ids:
                state_str = cells.get(eid, {}).get(cid, "否")
                # Extract state (first char or bracketed)
                import re
                match = re.search(r"\[([^\]]+)\]", state_str)
                state = match.group(1) if match else state_str.strip()[:2]
                valid_states = ["知", "疑", "昧", "否", "误信", "隐瞒"]
                if state not in valid_states:
                    state = "否"
                eid_cogs[eid] = CognitiveState(state=state, detail=state_str)

            characters[cid] = CharacterEntry(
                character_id=cid,
                event_cognitions=eid_cogs,
            )

        return CharacterMatrix(
            char_count=char_count,
            event_count=event_count,
            is_prototype=is_prototype,
            characters=characters,
            evidence={},
            meta=Meta(
                created_at=datetime.now().isoformat(),
                updated_at=datetime.now().isoformat(),
                commit_hash=_git_commit() or "no-git",
                brief_content_hash=_sha256(matrix_md),
                note="Migrated from information_matrix.md",
            ),
        )

    # ─── Evidence chain helpers ──────────────────────────────────────────────

    def add_evidence(
        self,
        evidence_id: str,
        name: str,
        description: str,
        source_event: str,
        source_character: str,
        chain_role: str,
        points_to: str = "",
    ) -> EvidenceItem:
        """Create but do NOT persist an evidence item — use add_evidence_to_matrix to persist."""
        return EvidenceItem(
            evidence_id=evidence_id,
            name=name,
            description=description,
            source_event=source_event,
            source_character=source_character,
            chain_role=chain_role,
            points_to=points_to,
        )

    def add_evidence_to_matrix(
        self,
        matrix: CharacterMatrix,
        evidence_id: str,
        name: str,
        description: str,
        source_event: str,
        source_character: str,
        chain_role: str,
        points_to: str = "",
    ) -> CharacterMatrix:
        """Add an evidence item to the matrix and save it atomically."""
        matrix.evidence[evidence_id] = EvidenceItem(
            evidence_id=evidence_id,
            name=name,
            description=description,
            source_event=source_event,
            source_character=source_character,
            chain_role=chain_role,
            points_to=points_to,
        )
        self.save_matrix(matrix, author="human", note=f"Added evidence {evidence_id}")
        return matrix

    # ─── Audit helpers ───────────────────────────────────────────────────────

    def audit_matrix_completeness(self, matrix: CharacterMatrix) -> list[str]:
        """Check for missing or inconsistent data in matrix.

        Returns list of issue descriptions.
        """
        issues = []

        # Check all characters have all events
        expected_chars = [f"R{i+1}" for i in range(matrix.char_count)]
        for cid in expected_chars:
            if cid not in matrix.characters:
                issues.append(f"Missing character: {cid}")
                continue
            char = matrix.characters[cid]
            expected_events = [f"E{i+1}" for i in range(matrix.event_count)]
            for eid in expected_events:
                if eid not in char.event_cognitions:
                    issues.append(f"Character {cid} missing cognition for {eid}")
                elif char.event_cognitions[eid].state == "否":
                    # Check if they should know (they are the culprit or witness)
                    pass  # "否" is valid for characters who weren't present

        # Check evidence chain completeness
        if not matrix.evidence:
            issues.append("No evidence chain defined — evidence is empty")

        # Check that at least one character knows each event
        expected_events = [f"E{i+1}" for i in range(matrix.event_count)]
        for eid in expected_events:
            knowers = matrix.all_know(eid)
            if not knowers:
                issues.append(f"Event {eid} has no character who [知] — evidence chain broken")

        return issues

    def audit_killer_knowledge(self, matrix: CharacterMatrix) -> list[str]:
        """Check that the killer (R1) has sufficient knowledge to be solvable."""
        issues = []

        killer = matrix.characters.get("R1")
        if not killer:
            issues.append("No R1 (killer) character found")
            return issues

        killer_knows = [
            eid for eid, cog in killer.event_cognitions.items()
            if cog.state in ["知", "误信"]
        ]

        if len(killer_knows) < matrix.event_count * 0.5:
            issues.append(
                f"Killer (R1) only knows {len(killer_knows)} of {matrix.event_count} events "
                f"— may be too mysterious to solve"
            )

        return issues


# ─── Helpers ─────────────────────────────────────────────────────────────────

def _git_commit() -> str:
    """Get short git commit hash if in a git repo, else None."""
    try:
        from pathlib import Path
        import subprocess
        result = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode == 0:
            return result.stdout.strip()
    except Exception:
        pass
    return None


def _sha256(content: str) -> str:
    """SHA256 hex digest of content."""
    return hashlib.sha256(content.encode("utf-8")).hexdigest()[:16]
