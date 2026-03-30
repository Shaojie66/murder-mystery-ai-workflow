"""Session persistence for murder-wizard projects."""
import json
import os
from pathlib import Path
from typing import Optional
from datetime import datetime

from murder_wizard.wizard.state_machine import MurderWizardState


class SessionManager:
    """管理项目会话持久化"""

    def __init__(self, project_name: str, base_path: Optional[str] = None):
        self.project_name = project_name
        if base_path is None:
            base_path = os.path.expanduser("~/.murder-wizard/projects")
        self.base_path = Path(base_path)
        self.project_path = self.base_path / project_name
        self.session_file = self.project_path / "session.json"
        self.cost_log = self.project_path / "cost.log"

    def ensure_project_dir(self) -> None:
        """确保项目目录存在"""
        self.project_path.mkdir(parents=True, exist_ok=True)

    def save(self, state: MurderWizardState) -> None:
        """保存状态到 session.json"""
        self.ensure_project_dir()
        data = state.to_dict()
        data["saved_at"] = datetime.now().isoformat()
        with open(self.session_file, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def load(self) -> Optional[MurderWizardState]:
        """从 session.json 加载状态"""
        if not self.session_file.exists():
            return None
        try:
            with open(self.session_file, encoding="utf-8") as f:
                data = json.load(f)
            return MurderWizardState.from_dict(data)
        except (json.JSONDecodeError, KeyError) as e:
            # session.json 损坏，返回 None
            return None

    def log_cost(self, operation: str, tokens_used: int, cost: float) -> None:
        """记录 API 消耗"""
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
        """从输出文件重建状态（session.json 损坏时）"""
        # 检查是否存在输出文件
        outline_file = self.project_path / "outline.md"
        characters_file = self.project_path / "characters.md"
        plot_file = self.project_path / "plot.md"

        if not any(f.exists() for f in [outline_file, characters_file, plot_file]):
            return None

        # 重建状态
        state = MurderWizardState(project_name=self.project_name)

        if outline_file.exists():
            state.outline = outline_file.read_text(encoding="utf-8")
            state.current_stage = state.Stage.STORY_BRIEF

        if characters_file.exists():
            state.current_stage = state.Stage.CHARACTER_DESIGN

        if plot_file.exists():
            state.current_stage = state.Stage.PLOT_BUILD

        return state
