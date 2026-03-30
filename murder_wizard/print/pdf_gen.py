"""PDF 生成模块."""
from pathlib import Path
from typing import Optional


class PDFGenerator:
    """剧本杀 PDF 排版生成"""

    def __init__(self, project_path: Path):
        self.project_path = project_path

    def generate_script_pdf(self, output_path: Optional[Path] = None) -> Path:
        """
        生成剧本 PDF。

        Args:
            output_path: 输出路径，默认 project_path/script.pdf

        Returns:
            生成的 PDF 文件路径
        """
        if output_path is None:
            output_path = self.project_path / "script.pdf"

        # TODO: 实现 PDF 生成
        # 方案1: reportlab
        # 方案2: weasyprint
        # 方案3: 调用外部工具（如 pandoc）
        raise NotImplementedError("PDF generation pending")

    def generate_clue_cards(self, output_dir: Optional[Path] = None) -> Path:
        """生成线索卡 PDF"""
        if output_dir is None:
            output_dir = self.project_path / "materials" / "线索卡"

        # TODO: 实现线索卡生成
        raise NotImplementedError("线索卡 PDF pending")

    def check_print_ready(self) -> tuple[bool, list[str]]:
        """
        检查是否满足印刷要求。

        Returns:
            (是否就绪, 问题列表)
        """
        issues = []

        # 检查分辨率（300dpi+）
        # 检查色彩空间（CMYK）
        # 检查刀版线
        # 检查字体嵌入

        return len(issues) == 0, issues
