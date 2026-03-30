"""PDF 生成模块 - 使用 reportlab."""
import os
from pathlib import Path
from typing import Optional


class PDFGenerator:
    """剧本杀 PDF 排版生成"""

    def __init__(self, project_path: Path):
        self.project_path = project_path
        self._check_dependencies()

    def _check_dependencies(self):
        """检查依赖"""
        try:
            from reportlab.lib.pagesizes import A4
            from reportlab.pdfgen import canvas
            from reportlab.pdfbase import pdfmetrics
            from reportlab.pdfbase.ttfonts import TTFont
            self._has_fonts = True
        except ImportError:
            self._has_fonts = False

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

        try:
            from reportlab.lib.pagesizes import A4
            from reportlab.pdfgen import canvas
            from reportlab.lib.styles import getSampleStyleSheet
            from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak
            from reportlab.lib.units import cm
        except ImportError:
            raise RuntimeError(
                "reportlab 未安装。运行: pip install reportlab\n"
                "或使用 --no-pdf 参数跳过 PDF 生成"
            )

        # 读取剧本内容
        characters_file = self.project_path / "characters.md"
        if not characters_file.exists():
            raise FileNotFoundError(f"角色剧本文件不存在：{characters_file}")

        content = characters_file.read_text(encoding="utf-8")

        # 创建 PDF
        doc = SimpleDocTemplate(
            str(output_path),
            pagesize=A4,
            rightMargin=2*cm,
            leftMargin=2*cm,
            topMargin=2*cm,
            bottomMargin=2*cm
        )

        styles = getSampleStyleSheet()
        story = []

        # 解析 Markdown 内容并添加段落
        lines = content.split("\n")
        for line in lines:
            line = line.strip()
            if not line:
                story.append(Spacer(1, 0.3*cm))
            elif line.startswith("# "):
                story.append(Paragraph(f"<b>{line[2:]}</b>", styles["Title"]))
                story.append(Spacer(1, 0.5*cm))
            elif line.startswith("## "):
                story.append(Paragraph(f"<b>{line[3:]}</b>", styles["Heading1"]))
                story.append(Spacer(1, 0.3*cm))
            elif line.startswith("### "):
                story.append(Paragraph(f"<b>{line[4:]}</b>", styles["Heading2"]))
                story.append(Spacer(1, 0.2*cm))
            elif line.startswith("---"):
                story.append(Spacer(1, 0.5*cm))
            else:
                # 处理 Markdown 强调
                line = line.replace("**", "<b>", 1).replace("**", "</b>", 1)
                story.append(Paragraph(line, styles["Normal"]))

        doc.build(story)
        return output_path

    def generate_clue_cards(self, output_dir: Optional[Path] = None) -> Path:
        """生成线索卡 PDF"""
        if output_dir is None:
            output_dir = self.project_path / "materials" / "线索卡"
        output_dir.mkdir(parents=True, exist_ok=True)

        try:
            from reportlab.lib.pagesizes import A4
            from reportlab.pdfgen import canvas
            from reportlab.lib.units import cm
        except ImportError:
            raise RuntimeError("reportlab 未安装")

        output_path = output_dir / "线索卡.pdf"

        # 读取信息矩阵
        matrix_file = self.project_path / "information_matrix.md"
        if matrix_file.exists():
            matrix_content = matrix_file.read_text(encoding="utf-8")
        else:
            matrix_content = ""

        c = canvas.Canvas(str(output_path), pagesize=A4)
        width, height = A4

        # 每页生成 6 张线索卡（2行3列）
        card_width = width / 3 - 1*cm
        card_height = height / 2 - 1*cm

        # 生成示例线索卡
        clues = [
            "关键证据",
            "时间线",
            "人物关系",
            "隐藏线索",
            "指向线索",
            "迷惑线索",
        ]

        for i, clue in enumerate(clues):
            col = i % 3
            row = i // 3
            x = 0.5*cm + col * (card_width + 0.5*cm)
            y = height - (row + 1) * (card_height + 0.5*cm)

            # 绘制卡片边框
            c.rect(x, y, card_width, card_height)

            # 添加卡片内容
            c.setFont("Helvetica", 12)
            c.drawString(x + 0.3*cm, y + card_height - 0.5*cm, f"线索 {i+1}")
            c.setFont("Helvetica", 9)
            c.drawString(x + 0.3*cm, y + card_height - 1*cm, clue)

        c.save()
        return output_path

    def check_print_ready(self) -> tuple[bool, list[str]]:
        """
        检查是否满足印刷要求。

        Returns:
            (是否就绪, 问题列表)
        """
        issues = []

        # 检查必要文件
        required_files = ["characters.md", "mechanism.md"]
        for f in required_files:
            if not (self.project_path / f).exists():
                issues.append(f"缺少文件：{f}")

        # 检查图像
        materials_dir = self.project_path / "materials"
        if materials_dir.exists():
            images = list((materials_dir / "角色图").glob("*.png")) + \
                    list((materials_dir / "角色图").glob("*.jpg"))
            if len(images) < 2:
                issues.append("角色图数量不足（建议至少2张）")
        else:
            issues.append("缺少物料目录 materials/")

        return len(issues) == 0, issues

    def generate_proof_order(self, print_shop: str = "default") -> dict:
        """
        生成印刷订单信息。

        Args:
            print_shop: 印刷厂标识

        Returns:
            订单信息字典，包含下单所需信息
        """
        info = {
            "project_name": self.project_path.name,
            "files": {},
            "checklist": {},
        }

        # 剧本 PDF
        script_pdf = self.project_path / "script.pdf"
        if script_pdf.exists():
            info["files"]["script_pdf"] = str(script_pdf)

        # 线索卡 PDF
        clue_pdf = self.project_path / "materials" / "线索卡" / "线索卡.pdf"
        if clue_pdf.exists():
            info["files"]["clue_cards_pdf"] = str(clue_pdf)

        # 物料清单
        if (self.project_path / "materials").exists():
            info["files"]["materials_dir"] = str(self.project_path / "materials")

        # 印刷要求清单
        info["checklist"] = {
            "分辨率": "300dpi+",
            "色彩空间": "CMYK",
            "字体": "嵌入",
            "出血": "3mm",
            "刀版线": "提供",
        }

        return info
