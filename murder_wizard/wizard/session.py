"""Session persistence for murder-wizard projects."""
import json
import os
import threading
from pathlib import Path
from typing import Optional
from datetime import datetime

from murder_wizard.wizard.state_machine import MurderWizardState, Stage


class SessionManager:
    """管理项目会话持久化"""

    def __init__(self, project_name: str, base_path: Optional[str] = None):
        # 防止路径穿越：禁止 .. 成分和绝对路径
        if ".." in project_name or os.path.isabs(project_name):
            raise ValueError(f"Invalid project name: {project_name!r}")
        # 禁止斜杠（防止子目录注入）
        safe_name = project_name.replace("/", "_").replace("\\", "_")
        self.project_name = safe_name
        if base_path is None:
            base_path = os.path.expanduser("~/.murder-wizard/projects")
        self.base_path = Path(base_path)
        self.project_path = self.base_path / self.project_name
        self.session_file = self.project_path / "session.json"
        self.cost_log = self.project_path / "cost.log"
        self._lock = threading.Lock()

    def ensure_project_dir(self) -> None:
        """确保项目目录存在"""
        self.project_path.mkdir(parents=True, exist_ok=True)

    def save(self, state: MurderWizardState) -> None:
        """保存状态到 session.json（线程安全，原子写入）"""
        self.ensure_project_dir()
        data = state.to_dict()
        data["saved_at"] = datetime.now().isoformat()
        tmp = self.session_file.with_suffix(".json.tmp")
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        tmp.rename(self.session_file)

    def load(self) -> Optional[MurderWizardState]:
        """从 session.json 加载状态"""
        if not self.session_file.exists():
            return None
        try:
            with open(self.session_file, encoding="utf-8") as f:
                data = json.load(f)
            return MurderWizardState.from_dict(data)
        except (json.JSONDecodeError, KeyError, ValueError) as e:
            # session.json 损坏，返回 None
            return None

    def log_cost(self, operation: str, tokens_used: int, cost: float) -> None:
        """记录 API 消耗（线程安全）"""
        with self._lock:
            self.ensure_project_dir()
            entry = {
                "timestamp": datetime.now().isoformat(),
                "operation": operation,
                "tokens": tokens_used,
                "cost": cost,
            }
            with open(self.cost_log, "a", encoding="utf-8") as f:
                f.write(json.dumps(entry, ensure_ascii=False) + "\n")

    def get_total_cost(self) -> float:
        """获取总消耗"""
        if not self.cost_log.exists():
            return 0.0
        total = 0.0
        with open(self.cost_log, encoding="utf-8") as f:
            for line in f:
                try:
                    entry = json.loads(line)
                    total += entry.get("cost", 0.0)
                except json.JSONDecodeError:
                    continue
        return total

    def list_projects(self) -> list[str]:
        """列出所有项目"""
        if not self.base_path.exists():
            return []
        return [p.name for p in self.base_path.iterdir() if p.is_dir()]

    def recover_from_files(self) -> Optional[MurderWizardState]:
        """从输出文件重建状态（session.json 损坏时）。

        按优先级从高到低检查所有 8 阶段工件，以最高阶段的已有文件为准。
        """
        # 按优先级排序：越高阶段的工件越能说明进度
        stage_artifacts = [
            (Stage.STAGE_8_COMMUNITY, "community_plan.md"),
            (Stage.STAGE_7_PROMO, "promo_content.md"),
            (Stage.STAGE_6_PRINT, "script.pdf"),
            (Stage.STAGE_5_COMMERCIAL, "commercial.md"),
            (Stage.STAGE_4_TEST, "test_guide.md"),
            (Stage.STAGE_3_VISUAL, "image-prompts.md"),
            (Stage.STAGE_2_SCRIPT, "characters.md"),
            (Stage.STAGE_1_MECHANISM, "mechanism.md"),
        ]

        found_stage: Stage | None = None
        for stage, artifact_name in stage_artifacts:
            if (self.project_path / artifact_name).exists():
                found_stage = stage
                break

        if found_stage is None:
            # 回退到旧的 legacy 文件名（兼容旧项目）
            outline_file = self.project_path / "outline.md"
            characters_file = self.project_path / "characters.md"
            plot_file = self.project_path / "plot.md"
            if not any(f.exists() for f in [outline_file, characters_file, plot_file]):
                return None
            if plot_file.exists():
                found_stage = Stage.PLOT_BUILD
            elif characters_file.exists():
                found_stage = Stage.CHARACTER_DESIGN
            else:
                found_stage = Stage.STORY_BRIEF

        state = MurderWizardState(project_name=self.project_name)
        state.current_stage = found_stage

        # 回退：legacy outline 文件
        if found_stage is None or found_stage in (Stage.STORY_BRIEF, Stage.CHARACTER_DESIGN, Stage.PLOT_BUILD):
            outline_file = self.project_path / "outline.md"
            if outline_file.exists():
                state.outline = outline_file.read_text(encoding="utf-8")

        return state
