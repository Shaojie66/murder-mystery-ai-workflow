"""Phase runner for executing story generation phases."""

import json
from pathlib import Path
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field
from datetime import datetime
from .prompts.loader import PromptLoader
from .generator import generate_with_llm


@dataclass
class StageResult:
    """Result of a stage execution."""
    stage: int
    success: bool
    result: str = ""
    error: str = ""
    quality_gate_passed: bool = False
    execution_time: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "stage": self.stage,
            "success": self.success,
            "result": self.result,
            "error": self.error,
            "quality_gate_passed": self.quality_gate_passed,
            "execution_time": self.execution_time,
        }


@dataclass
class ProjectState:
    """Complete state of a murder mystery project."""
    project_name: str
    story_type: str
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = ""
    stage_results: List[Dict[str, Any]] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "project_name": self.project_name,
            "story_type": self.story_type,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "stage_results": self.stage_results,
            "metadata": self.metadata,
        }


class PhaseRunner:
    """Runs each phase of story generation with type-specific prompts.

    Inspired by Claude Code's progressive harness pattern:
    - Quality gates between stages
    - State persistence and recovery
    - Type-specific validation
    - Verification checkpoints
    """

    # Story type choices
    STORY_TYPES = ["emotion", "reasoning", "fun", "horror", "mechanic"]

    # Phase names
    PHASE_NAMES = {
        1: "机制设计",
        2: "角色剧本",
        3: "图像生成",
        4: "测试指南",
        5: "商业化",
        6: "成品输出",
        7: "宣发文案",
        8: "社区运营",
    }

    # Type display names
    TYPE_DISPLAY = {
        "emotion": "情感本",
        "reasoning": "推理本",
        "fun": "欢乐本",
        "horror": "恐怖本",
        "mechanic": "机制本",
    }

    def __init__(self, project_dir: Path, story_type: str = "mechanic"):
        self.project_dir = Path(project_dir)
        self.story_type = story_type
        self._loader = PromptLoader()
        self.state: Dict[str, Any] = {}

    def _load_state(self) -> Dict[str, Any]:
        """Load project state from file."""
        state_file = self.project_dir / "murder-wizard-session.json"
        if state_file.exists():
            with open(state_file, "r", encoding="utf-8") as f:
                return json.load(f)
        return {}

    def _save_state(self, state: Dict[str, Any]):
        """Save project state to file."""
        state_file = self.project_dir / "murder-wizard-session.json"
        state["updated_at"] = datetime.now().isoformat()
        with open(state_file, "w", encoding="utf-8") as f:
            json.dump(state, f, indent=2, ensure_ascii=False)

    def _build_stage_prompt(self, stage: int, **variables) -> str:
        """Build prompt for a specific stage."""
        variables["story_type"] = self.story_type

        if stage == 1:
            return self._loader.stage1_design(**variables)
        elif stage == 2:
            return self._loader.stage2_script(**variables)
        elif stage == 3:
            return self._loader.stage3_image(**variables)
        elif stage == 4:
            return self._loader.stage4_testing(**variables)
        elif stage == 5:
            return self._loader.stage5_marketing(**variables)
        else:
            raise ValueError(f"Unknown stage: {stage}")

    def _get_system_prompt(self, stage: int) -> str:
        """Get system prompt for a specific stage."""
        if stage == 1:
            return self._loader.system_stage1_designer(self.story_type)
        elif stage == 2:
            return self._loader.system_stage2_writer(self.story_type)
        elif stage == 3:
            return self._loader.system_stage3_artist(self.story_type)
        elif stage == 4:
            return self._loader.system_stage4_tester(self.story_type)
        elif stage == 5:
            return self._loader.system_stage5_marketer(self.story_type)
        else:
            raise ValueError(f"Unknown stage: {stage}")

    def _validate_output(self, stage: int, result: str) -> bool:
        """Validate stage output against quality gates.

        Inspired by Claude Code's verification agents pattern.
        """
        if len(result) < 100:
            return False

        # Stage-specific validation
        if stage == 1:
            # Check for mechanism completeness
            required_keywords = ["角色", "机制", "设计"]
            return all(kw in result for kw in required_keywords)

        elif stage == 2:
            # Check for script completeness
            required_keywords = ["角色", "剧本", "关系"]
            return all(kw in result for kw in required_keywords)

        elif stage == 3:
            # Check for image prompt completeness
            required_keywords = ["图像", "提示词", "画面"]
            return all(kw in result for kw in required_keywords)

        elif stage == 4:
            # Check for testing guide completeness
            required_keywords = ["测试", "评估", "问题"]
            return all(kw in result for kw in required_keywords)

        elif stage == 5:
            # Check for marketing completeness
            required_keywords = ["营销", "受众", "推广"]
            return all(kw in result for kw in required_keywords)

        return True

    def run_stage(self, stage: int, **variables) -> Dict[str, Any]:
        """Run a specific stage and return the result.

        Includes quality gate validation after execution.
        """
        prompt = self._build_stage_prompt(stage, **variables)
        system = self._get_system_prompt(stage)

        try:
            result = generate_with_llm(system_prompt=system, user_prompt=prompt)

            # Validate output quality
            quality_passed = self._validate_output(stage, result)

            # Save result to state
            self.state = self._load_state()
            self.state[f"stage{stage}_result"] = result
            self.state[f"stage{stage}_quality_passed"] = quality_passed
            self._save_state(self.state)

            # Save to file
            output_file = self.project_dir / f"stage{stage}.md"
            output_file.write_text(result, encoding="utf-8")

            return {
                "success": True,
                "stage": stage,
                "result": result,
                "quality_gate_passed": quality_passed,
            }

        except Exception as e:
            return {
                "success": False,
                "stage": stage,
                "result": "",
                "error": str(e),
            }

    def run_stage_with_retry(self, stage: int, max_retries: int = 2, **variables) -> Dict[str, Any]:
        """Run a stage with retry on quality gate failure.

        Inspired by Claude Code's retry mechanism.
        """
        for attempt in range(max_retries + 1):
            result = self.run_stage(stage, **variables)

            if result.get("success") and result.get("quality_gate_passed"):
                return result

            if attempt < max_retries:
                print(f"Quality gate failed for stage {stage}, retry {attempt + 2}/{max_retries + 1}")

        return result

    def run_stage_1(self, **variables) -> Dict[str, Any]:
        """Run Stage 1: 机制设计 (Mechanism Design)."""
        print(f"Running Stage 1 (机制设计) for {self.get_story_type_display()}...")
        return self.run_stage_with_retry(1, **variables)

    def run_stage_2(self, mechanism_content: str = "", brief_content: str = "") -> Dict[str, Any]:
        """Run Stage 2: 角色剧本 (Character Scripts)."""
        print(f"Running Stage 2 (角色剧本) for {self.get_story_type_display()}...")
        variables = {
            "mechanism_content": mechanism_content,
            "brief_content": brief_content,
        }
        return self.run_stage_with_retry(2, **variables)

    def run_stage_3(self, script_content: str = "") -> Dict[str, Any]:
        """Run Stage 3: 图像生成 (Image Generation)."""
        print(f"Running Stage 3 (图像生成) for {self.get_story_type_display()}...")
        variables = {
            "script_content": script_content,
        }
        return self.run_stage_with_retry(3, **variables)

    def run_stage_4(self, image_content: str = "") -> Dict[str, Any]:
        """Run Stage 4: 测试指南 (Testing Guide)."""
        print(f"Running Stage 4 (测试指南) for {self.get_story_type_display()}...")
        variables = {
            "image_content": image_content,
        }
        return self.run_stage_with_retry(4, **variables)

    def run_stage_5(self, testing_content: str = "") -> Dict[str, Any]:
        """Run Stage 5: 商业化 (Commercialization)."""
        print(f"Running Stage 5 (商业化) for {self.get_story_type_display()}...")
        variables = {
            "testing_content": testing_content,
        }
        return self.run_stage_with_retry(5, **variables)

    def run_pipeline(self, start: int = 1, end: int = 5) -> List[Dict[str, Any]]:
        """Run pipeline from start to end stage.

        Each stage's output feeds into the next.
        """
        results = []
        previous_output = ""

        for stage in range(start, end + 1):
            if stage == 1:
                result = self.run_stage_1()
            elif stage == 2:
                mechanism = results[0]["result"] if results else ""
                result = self.run_stage_2(mechanism_content=mechanism)
            elif stage == 3:
                script = result["result"] if result else ""
                result = self.run_stage_3(script_content=script)
            elif stage == 4:
                images = result["result"] if result else ""
                result = self.run_stage_4(image_content=images)
            elif stage == 5:
                testing = result["result"] if result else ""
                result = self.run_stage_5(testing_content=testing)
            else:
                break

            results.append(result)

            if not result.get("success"):
                print(f"Stage {stage} failed, stopping pipeline")
                break

            # Store result for next stage
            if stage == 1:
                previous_output = result.get("result", "")
            elif stage == 2:
                previous_output = result.get("result", "")
            elif stage == 3:
                previous_output = result.get("result", "")
            elif stage == 4:
                previous_output = result.get("result", "")

        return results

    def get_quality_report(self) -> Dict[str, Any]:
        """Get quality gate report for all completed stages."""
        report = {
            "story_type": self.story_type,
            "story_type_display": self.get_story_type_display(),
            "stages": {},
        }

        state = self._load_state()

        for stage in range(1, 6):
            key = f"stage{stage}_quality_passed"
            if key in state:
                report["stages"][self.PHASE_NAMES[stage]] = {
                    "passed": state[key],
                    "has_result": f"stage{stage}_result" in state,
                }

        return report

    def get_story_type_display(self) -> str:
        """Get display name for story type."""
        return self.TYPE_DISPLAY.get(self.story_type, self.story_type)

    @classmethod
    def get_available_types(cls) -> List[str]:
        """Get list of available story types."""
        return cls.STORY_TYPES

    @classmethod
    def get_phase_name(cls, stage: int) -> str:
        """Get phase name for a stage number."""
        return cls.PHASE_NAMES.get(stage, f"Phase {stage}")

    @classmethod
    def get_type_display_name(cls, story_type: str) -> str:
        """Get display name for a story type."""
        return cls.TYPE_DISPLAY.get(story_type, story_type)
