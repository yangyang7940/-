"""依据学校提供的 Word 模板生成专业综合实训报告。"""

from __future__ import annotations

import copy
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont
from docx import Document
from docx.enum.section import WD_SECTION
from docx.enum.style import WD_STYLE_TYPE
from docx.enum.table import WD_CELL_VERTICAL_ALIGNMENT, WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_BREAK, WD_LINE_SPACING
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Inches, Pt, RGBColor


ROOT = Path(__file__).resolve().parent
TEMPLATE = ROOT.parent / "专业综合实训报告模板.docx"
OUTPUT = ROOT / "计科中外1班+赵子恒_专业综合实训报告.docx"
DOCS_DIR = ROOT / "docs"
GREEN = "0F7957"
LIGHT_GREEN = "E7F5EE"
GRAY = "F2F4F3"


def set_east_asia(run, name: str) -> None:
    run.font.name = "Times New Roman"
    run._element.rPr.rFonts.set(qn("w:eastAsia"), name)


def style_run(run, *, size: float = 12, bold: bool = False, font: str = "宋体", color: str | None = None) -> None:
    set_east_asia(run, font)
    run.font.size = Pt(size)
    run.bold = bold
    if color:
        run.font.color.rgb = RGBColor.from_string(color)


def clear_and_write(paragraph, text: str, **style) -> None:
    paragraph.clear()
    run = paragraph.add_run(text)
    style_run(run, **style)


def set_repeat_table_header(row) -> None:
    tr_pr = row._tr.get_or_add_trPr()
    tbl_header = OxmlElement("w:tblHeader")
    tbl_header.set(qn("w:val"), "true")
    tr_pr.append(tbl_header)


def shade_cell(cell, fill: str) -> None:
    tc_pr = cell._tc.get_or_add_tcPr()
    shading = tc_pr.find(qn("w:shd"))
    if shading is None:
        shading = OxmlElement("w:shd")
        tc_pr.append(shading)
    shading.set(qn("w:fill"), fill)


def set_cell_text(cell, text: object, *, bold: bool = False, color: str | None = None, align=WD_ALIGN_PARAGRAPH.CENTER) -> None:
    cell.text = ""
    paragraph = cell.paragraphs[0]
    paragraph.alignment = align
    paragraph.paragraph_format.space_before = Pt(0)
    paragraph.paragraph_format.space_after = Pt(0)
    run = paragraph.add_run(str(text))
    style_run(run, size=9.5, bold=bold, font="宋体", color=color)
    cell.vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.CENTER


def set_repeat_no_split(row) -> None:
    tr_pr = row._tr.get_or_add_trPr()
    cant_split = OxmlElement("w:cantSplit")
    tr_pr.append(cant_split)


def add_table(doc: Document, headers: list[str], rows: list[list[object]], widths: list[float] | None = None):
    table = doc.add_table(rows=1, cols=len(headers))
    table.style = "Table Grid"
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    table.autofit = True
    header = table.rows[0]
    set_repeat_table_header(header)
    for index, value in enumerate(headers):
        shade_cell(header.cells[index], GREEN)
        set_cell_text(header.cells[index], value, bold=True, color="FFFFFF")
    for values in rows:
        row = table.add_row()
        set_repeat_no_split(row)
        for index, value in enumerate(values):
            set_cell_text(row.cells[index], value, align=WD_ALIGN_PARAGRAPH.LEFT if index else WD_ALIGN_PARAGRAPH.CENTER)
            if len(table.rows) % 2 == 1:
                shade_cell(row.cells[index], "F7F9F8")
    if widths:
        for row in table.rows:
            for cell, width in zip(row.cells, widths):
                cell.width = Cm(width)
    doc.add_paragraph()
    return table


def add_body(doc: Document, text: str, *, bold_lead: str | None = None):
    paragraph = doc.add_paragraph(style="Normal")
    paragraph.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    paragraph.paragraph_format.first_line_indent = Pt(24)
    paragraph.paragraph_format.line_spacing_rule = WD_LINE_SPACING.ONE_POINT_FIVE
    paragraph.paragraph_format.space_after = Pt(0)
    if bold_lead and text.startswith(bold_lead):
        first = paragraph.add_run(bold_lead)
        style_run(first, size=12, bold=True)
        rest = paragraph.add_run(text[len(bold_lead) :])
        style_run(rest, size=12)
    else:
        run = paragraph.add_run(text)
        style_run(run, size=12)
    return paragraph


def add_heading(doc: Document, text: str, level: int):
    paragraph = doc.add_paragraph(style=f"Heading {level}")
    run = paragraph.add_run(text)
    sizes = {1: 16, 2: 14, 3: 12}
    style_run(run, size=sizes[level], bold=True, font="黑体")
    return paragraph


def add_equation(doc: Document, text: str):
    paragraph = doc.add_paragraph()
    paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
    paragraph.paragraph_format.space_before = Pt(6)
    paragraph.paragraph_format.space_after = Pt(6)
    run = paragraph.add_run(text)
    style_run(run, size=11, font="Times New Roman")


def add_caption(doc: Document, text: str, source: str | None = None):
    paragraph = doc.add_paragraph()
    paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = paragraph.add_run(text)
    style_run(run, size=10.5, font="宋体")
    if source:
        source_p = doc.add_paragraph()
        source_p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        source_run = source_p.add_run(f"图片来源：{source}")
        style_run(source_run, size=9, font="宋体", color="777777")


def add_picture(doc: Document, path: Path, caption: str, *, width_inches: float = 6.15, source: str = "本项目设计与实际运行结果"):
    paragraph = doc.add_paragraph()
    paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
    paragraph.add_run().add_picture(str(path), width=Inches(width_inches))
    add_caption(doc, caption, source)


def add_page_break(doc: Document) -> None:
    doc.add_paragraph().add_run().add_break(WD_BREAK.PAGE)


def add_field(paragraph, instruction: str, placeholder: str = "") -> None:
    run = paragraph.add_run()
    begin = OxmlElement("w:fldChar")
    begin.set(qn("w:fldCharType"), "begin")
    instr = OxmlElement("w:instrText")
    instr.set(qn("xml:space"), "preserve")
    instr.text = instruction
    separate = OxmlElement("w:fldChar")
    separate.set(qn("w:fldCharType"), "separate")
    text = OxmlElement("w:t")
    text.text = placeholder
    end = OxmlElement("w:fldChar")
    end.set(qn("w:fldCharType"), "end")
    run._r.extend([begin, instr, separate, text, end])


def configure_styles(doc: Document) -> None:
    normal = doc.styles["Normal"]
    normal.font.name = "Times New Roman"
    normal._element.rPr.rFonts.set(qn("w:eastAsia"), "宋体")
    normal.font.size = Pt(12)
    normal.paragraph_format.line_spacing_rule = WD_LINE_SPACING.ONE_POINT_FIVE
    normal.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    for level, size in ((1, 16), (2, 14), (3, 12)):
        style_name = f"Heading {level}"
        try:
            style = doc.styles[style_name]
        except KeyError:
            style = doc.styles.add_style(style_name, WD_STYLE_TYPE.PARAGRAPH)
            style.base_style = normal
        style.font.name = "Times New Roman"
        style._element.rPr.rFonts.set(qn("w:eastAsia"), "黑体")
        style.font.size = Pt(size)
        style.font.bold = True
        style.font.color.rgb = RGBColor(0, 0, 0)
        style.paragraph_format.keep_with_next = True
        style.paragraph_format.space_before = Pt(12 if level == 1 else 8)
        style.paragraph_format.space_after = Pt(6)
        style_ppr = style._element.get_or_add_pPr()
        old_outline = style_ppr.find(qn("w:outlineLvl"))
        if old_outline is not None:
            style_ppr.remove(old_outline)
        outline = OxmlElement("w:outlineLvl")
        outline.set(qn("w:val"), str(level - 1))
        style_ppr.append(outline)
        if style._element.find(qn("w:qFormat")) is None:
            style._element.append(OxmlElement("w:qFormat"))
        if level == 1:
            style.paragraph_format.page_break_before = True


def set_section_header_footer(section, *, header_text: str = "湖北第二师范学院", page_start: int | None = None) -> None:
    section.header.is_linked_to_previous = False
    header = section.header
    header_p = header.paragraphs[0]
    clear_and_write(header_p, header_text, size=9, font="宋体", color="777777")
    header_p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    section.footer.is_linked_to_previous = False
    footer_p = section.footer.paragraphs[0]
    footer_p.clear()
    footer_p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    add_field(footer_p, " PAGE ", "1")
    if page_start is not None:
        pg_num = OxmlElement("w:pgNumType")
        pg_num.set(qn("w:start"), str(page_start))
        section._sectPr.append(pg_num)


def font(size: int, bold: bool = False):
    paths = [
        Path("C:/Windows/Fonts/msyhbd.ttc" if bold else "C:/Windows/Fonts/msyh.ttc"),
        Path("C:/Windows/Fonts/simhei.ttf" if bold else "C:/Windows/Fonts/simsun.ttc"),
    ]
    for path in paths:
        if path.exists():
            return ImageFont.truetype(str(path), size)
    return ImageFont.load_default()


def centered_text(draw: ImageDraw.ImageDraw, box: tuple[int, int, int, int], text: str, used_font, fill: str = "#17352b") -> None:
    left, top, right, bottom = box
    bbox = draw.multiline_textbbox((0, 0), text, font=used_font, spacing=6, align="center")
    width, height = bbox[2] - bbox[0], bbox[3] - bbox[1]
    draw.multiline_text(((left + right - width) / 2, (top + bottom - height) / 2), text, font=used_font, fill=fill, spacing=6, align="center")


def arrow(draw: ImageDraw.ImageDraw, start: tuple[int, int], end: tuple[int, int]) -> None:
    draw.line([start, end], fill="#4f8f77", width=5)
    x, y = end
    draw.polygon([(x, y), (x - 16, y - 10), (x - 16, y + 10)], fill="#4f8f77")


def make_diagrams() -> None:
    DOCS_DIR.mkdir(exist_ok=True)
    title_font, box_font, small_font = font(42, True), font(28, True), font(22)

    image = Image.new("RGB", (1600, 900), "#f7faf8")
    draw = ImageDraw.Draw(image)
    centered_text(draw, (0, 25, 1600, 105), "智能简历筛选系统总体架构", title_font)
    boxes = [
        ((70, 270, 320, 600), "用户层\n招聘人员 / 学生"),
        ((390, 210, 680, 660), "表示层\nHTML + CSS + JS\n\n单份匹配\n批量排名\n方法说明"),
        ((760, 210, 1050, 660), "服务层\nPython HTTP API\n\n参数校验\n路由分发\n异常处理"),
        ((1130, 125, 1530, 390), "算法层\nTF-IDF 相似度\n技能 / 年限 / 学历\n综合评分与解释"),
        ((1130, 490, 1530, 755), "数据层\n岗位 CSV\n匿名简历 CSV\n标注集与评估结果"),
    ]
    for index, (coords, text) in enumerate(boxes):
        fill = "#e3f3eb" if index in (0, 3) else "#ffffff"
        draw.rounded_rectangle(coords, radius=24, fill=fill, outline="#9bc5b3", width=3)
        centered_text(draw, coords, text, box_font if index == 0 else small_font)
    arrow(draw, (320, 435), (390, 435))
    arrow(draw, (680, 435), (760, 435))
    arrow(draw, (1050, 330), (1130, 260))
    arrow(draw, (1050, 535), (1130, 620))
    image.save(DOCS_DIR / "系统总体架构图.png", quality=95)

    image = Image.new("RGB", (1600, 820), "#f7faf8")
    draw = ImageDraw.Draw(image)
    centered_text(draw, (0, 20, 1600, 100), "简历岗位匹配处理流程", title_font)
    top_boxes = [
        ((45, 170, 265, 320), "输入岗位\n与简历"),
        ((325, 170, 545, 320), "文本规范化\n中英文分词"),
        ((605, 170, 825, 320), "提取技能\n年限与学历"),
        ((885, 170, 1105, 320), "计算 TF-IDF\n余弦相似度"),
        ((1165, 170, 1385, 320), "四维加权\n综合得分"),
    ]
    for coords, text in top_boxes:
        draw.rounded_rectangle(coords, radius=18, fill="#ffffff", outline="#8fbea9", width=3)
        centered_text(draw, coords, text, small_font)
    for index in range(len(top_boxes) - 1):
        arrow(draw, (top_boxes[index][0][2], 245), (top_boxes[index + 1][0][0], 245))
    draw.rounded_rectangle((310, 470, 1290, 690), radius=24, fill="#e3f3eb", outline="#68a98e", width=3)
    centered_text(draw, (330, 490, 610, 670), "匹配技能\n缺失技能", small_font)
    centered_text(draw, (660, 490, 940, 670), "亮点与风险\n推荐等级", small_font)
    centered_text(draw, (990, 490, 1270, 670), "单份解释\n候选人排名", small_font)
    draw.line([(630, 510), (630, 650)], fill="#9bc5b3", width=2)
    draw.line([(960, 510), (960, 650)], fill="#9bc5b3", width=2)
    draw.line([(1275, 320), (1275, 430), (800, 430), (800, 470)], fill="#4f8f77", width=5)
    draw.polygon([(800, 470), (790, 452), (810, 452)], fill="#4f8f77")
    image.save(DOCS_DIR / "匹配处理流程图.png", quality=95)


def prepare_template() -> Document:
    doc = Document(str(TEMPLATE))
    body = doc._element.body
    elements = list(body)
    # 保留模板封面、项目自评页及其分节属性，删除示例摘要、目录和示例正文。
    for element in elements[21:-1]:
        body.remove(element)

    paragraphs = doc.paragraphs
    clear_and_write(paragraphs[5], "专业综合实训报告", size=30, font="黑体")
    paragraphs[5].alignment = WD_ALIGN_PARAGRAPH.CENTER

    cover_fields = [
        (7, "题    目", "智能简历筛选与岗位匹配系统"),
        (9, "学    院", "计算机科学与技术"),
        (10, "专业班级", "计科中外1班"),
        (11, "姓    名", "赵子恒"),
        (12, "指导教师", ""),
    ]
    for index, label, value in cover_fields:
        paragraph = paragraphs[index]
        paragraph.clear()
        paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
        paragraph.paragraph_format.line_spacing = 1.7
        label_run = paragraph.add_run(f"{label}    ")
        style_run(label_run, size=14, font="宋体")
        value_run = paragraph.add_run(value or "                    ")
        style_run(value_run, size=14, font="宋体")
        value_run.underline = True
    clear_and_write(paragraphs[15], "二〇二六 年 九 月 二十六 日", size=14, font="宋体")
    paragraphs[15].alignment = WD_ALIGN_PARAGRAPH.CENTER

    assessment_table = doc.tables[0]
    assessment_table.style = "Table Grid"
    assessment_table.alignment = WD_TABLE_ALIGNMENT.CENTER
    for row_index, row in enumerate(assessment_table.rows):
        for cell in row.cells:
            set_cell_text(cell, cell.text.strip(), bold=row_index == 0)
            if row_index == 0:
                shade_cell(cell, GREEN)
                for run in cell.paragraphs[0].runs:
                    run.font.color.rgb = RGBColor(255, 255, 255)
    set_cell_text(assessment_table.cell(6, 1), "92 分", bold=True, color=GREEN)

    # 将模板中的空段落移动到自评表之前作为标题，保持原有分节不变。
    assessment_title = paragraphs[16]
    clear_and_write(assessment_title, "项目自评", size=18, bold=True, font="黑体")
    assessment_title.alignment = WD_ALIGN_PARAGRAPH.CENTER
    assessment_table._tbl.addprevious(assessment_title._p)
    clear_and_write(paragraphs[17], "自评说明：项目由本人独立完成，功能、代码、测试、文档和演示材料均按任务书要求准备。建议自评分数为 92 分，具体依据见第 5 章。", size=11, font="宋体")
    paragraphs[17].paragraph_format.line_spacing_rule = WD_LINE_SPACING.ONE_POINT_FIVE
    paragraphs[17].alignment = WD_ALIGN_PARAGRAPH.JUSTIFY

    configure_styles(doc)
    update_fields = OxmlElement("w:updateFields")
    update_fields.set(qn("w:val"), "true")
    doc.settings._element.append(update_fields)
    for section in doc.sections:
        section.top_margin = Cm(2.54)
        section.bottom_margin = Cm(2.54)
        section.left_margin = Cm(3.0)
        section.right_margin = Cm(2.5)
    doc.sections[0].header.is_linked_to_previous = False
    doc.sections[0].header.paragraphs[0].clear()
    doc.sections[0].footer.is_linked_to_previous = False
    doc.sections[0].footer.paragraphs[0].clear()
    for section in doc.sections[1:]:
        set_section_header_footer(section)
    return doc


def build_report() -> Path:
    make_diagrams()
    doc = prepare_template()

    # 中文摘要
    title = doc.add_paragraph()
    title.alignment = WD_ALIGN_PARAGRAPH.CENTER
    clear_and_write(title, "摘  要", size=18, bold=True, font="黑体")
    add_body(doc, "随着岗位信息与求职简历数量持续增加，完全依赖人工阅读的初筛方式存在耗时长、标准不统一和依据难追溯等问题。本项目面向课程实训场景，设计并实现了一套智能简历筛选与岗位匹配系统。系统以 Python 为主要开发语言，采用本地浏览器交互形式，不依赖付费接口或专用硬件，可在离线环境完成单份简历分析和候选人批量排序。")
    add_body(doc, "在方法上，系统首先对中英文混合文本进行大小写、空白和全角符号规范化，再利用英文单词及中文单字、二元和三元片段构建词项；随后计算基于 TF-IDF 的余弦相似度，并通过技能别名词典提取岗位技能，同时识别经验年限与学历等级。最终按照文本相似度 40%、技能覆盖率 35%、经验匹配度 15% 和学历匹配度 10% 形成综合得分，输出已匹配技能、待补充技能、优势、风险和推荐等级，实现结果可解释。")
    add_body(doc, "项目构建了 6 个测试岗位、18 份匿名简历和人工相关性标注集，并编写算法、数据访问和接口自动测试。实际运行的 11 项自动测试全部通过；标注集评估得到 Top-1 准确率 100%、Precision@3 为 66.67%、Recall@3 为 100%。结果表明，该系统能够稳定完成课程规模的人岗初筛任务，并通过明确的权重与证据展示降低黑盒感。系统不采集性别、年龄、照片等敏感属性，定位为人工招聘决策的辅助工具。")
    keywords = doc.add_paragraph()
    keywords.paragraph_format.space_before = Pt(10)
    lead = keywords.add_run("关键词：")
    style_run(lead, size=12, bold=True)
    tail = keywords.add_run("智能招聘；简历筛选；岗位匹配；TF-IDF；可解释人工智能")
    style_run(tail, size=12)

    add_page_break(doc)
    title = doc.add_paragraph()
    title.alignment = WD_ALIGN_PARAGRAPH.CENTER
    clear_and_write(title, "ABSTRACT", size=18, bold=True, font="Times New Roman")
    abstract_texts = [
        "As the number of job descriptions and resumes grows, manual screening becomes time-consuming, inconsistent, and difficult to audit. This project designs and implements an intelligent resume screening and job matching system for a lightweight course-practice scenario. Python is used as the primary programming language. The application runs locally through a browser and requires neither a paid API nor dedicated hardware. It supports both single-resume analysis and batch candidate ranking.",
        "The system normalizes mixed Chinese and English text and builds features from English words as well as Chinese character n-grams. It then calculates TF-IDF cosine similarity, extracts normalized skills through an alias dictionary, and identifies experience and education requirements. The final score combines text similarity (40%), skill coverage (35%), experience matching (15%), and education matching (10%). Matched skills, missing skills, strengths, risks, and a recommendation level are displayed to make the result explainable.",
        "A test set containing six positions, eighteen anonymous resumes, and manually labeled relevance data was created. All eleven automated tests passed. The evaluation achieved 100% Top-1 accuracy, 66.67% Precision@3, and 100% Recall@3. The system is suitable for a course-scale screening task and should be used only as decision support. Sensitive demographic attributes are deliberately excluded, and final employment decisions remain the responsibility of human reviewers.",
    ]
    for text in abstract_texts:
        paragraph = doc.add_paragraph()
        paragraph.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
        paragraph.paragraph_format.first_line_indent = Pt(24)
        paragraph.paragraph_format.line_spacing_rule = WD_LINE_SPACING.ONE_POINT_FIVE
        run = paragraph.add_run(text)
        style_run(run, size=12, font="Times New Roman")
    keywords = doc.add_paragraph()
    lead = keywords.add_run("Keywords: ")
    style_run(lead, size=12, bold=True, font="Times New Roman")
    tail = keywords.add_run("intelligent recruitment; resume screening; job matching; TF-IDF; explainable AI")
    style_run(tail, size=12, font="Times New Roman")

    # 目录页，设置为打开 Word 时自动更新。
    add_page_break(doc)
    toc_title = doc.add_paragraph()
    toc_title.alignment = WD_ALIGN_PARAGRAPH.CENTER
    clear_and_write(toc_title, "目  录", size=18, bold=True, font="黑体")
    toc = doc.add_paragraph()
    add_field(toc, ' TOC \\o "1-3" \\h \\z \\u ', "打开文档后更新目录")
    hint = doc.add_paragraph()
    hint.alignment = WD_ALIGN_PARAGRAPH.CENTER
    clear_and_write(hint, "提示：Microsoft Word 会在打开文档时更新目录，也可按 Ctrl+A 后按 F9 手动更新。", size=9, font="宋体", color="777777")

    body_section = doc.add_section(WD_SECTION.NEW_PAGE)
    body_section.top_margin = Cm(2.54)
    body_section.bottom_margin = Cm(2.54)
    body_section.left_margin = Cm(3.0)
    body_section.right_margin = Cm(2.5)
    set_section_header_footer(body_section, page_start=1)

    # 第 1 章
    add_heading(doc, "1. 引言", 1)
    add_heading(doc, "1.1 项目背景", 2)
    add_body(doc, "招聘初筛的核心任务，是在有限时间内判断候选人是否满足岗位的基本要求并确定后续复核顺序。传统流程通常由招聘人员逐份阅读简历，将技能、项目、学历和年限与岗位描述进行比对。当候选人数量增加时，相同信息会被反复查找，判断标准也容易因阅读顺序和个人经验产生波动。对于课程实训而言，完整的人岗匹配过程同时涉及文本处理、规则设计、算法实现、网页交互、数据测试和结果解释，能够覆盖人工智能应用开发的主要环节。")
    add_body(doc, "信息检索研究通常将查询与文档表示为词项向量，再以词频和逆文档频率突出具有区分度的词项[1-3]。岗位描述可以视为查询，简历可以视为候选文档，因此 TF-IDF 与余弦相似度适合构成轻量化的语义相关度基础。不过，招聘场景还存在技能、最低学历和经验年限等硬性条件，单纯依赖文本相似度可能将语言表述相近但条件不足的候选人排在前面。本项目由此采用“文本相似度 + 结构化规则”的混合方案。")

    add_heading(doc, "1.2 问题定义", 2)
    add_body(doc, "系统输入包括岗位信息和候选人简历文本。岗位信息至少包含岗位名称、职责描述、技能要求、最低经验和最低学历；简历至少应包含求职方向、技能、学历、项目或工作经历。系统输出为 0～100 分的综合匹配得分、四个分项得分、匹配与缺失技能、亮点、风险以及推荐等级。批量模式还需对同一岗位下的多名候选人进行稳定排序。")
    add_body(doc, "该任务并不是自动作出录用决定，而是把重复的关键词核对和基本条件检查转化为统一、可复现的初筛过程。评价系统好坏时，除关注排序正确性外，还应考察结果是否可解释、输入异常是否得到处理、是否泄露个人信息以及运行环境是否足够轻量。")

    add_heading(doc, "1.3 项目目标与范围", 2)
    add_body(doc, "本项目目标包括：第一，实现单份简历与指定岗位的自动匹配；第二，实现匿名候选人测试集的批量评分与排序；第三，展示四维分数和具体证据，便于人工复核；第四，提供无需联网的一键启动方式；第五，建立可重复执行的自动测试和评估流程。系统面向课程演示和小规模辅助筛选，不包含真实招聘平台账号、在线爬取、自动邀约、在线模型训练或最终录用审批。")

    add_heading(doc, "1.4 创新性与实用价值", 2)
    add_body(doc, "项目的创新点主要体现在三个方面。其一，为中文简历设计无需外部分词库的字符 n-gram 方案，使程序在仅有 Python 标准库的环境中仍可运行；其二，将语义相关度与岗位硬性条件组合，并逐项展示匹配依据，避免只有总分而无法说明原因；其三，从设计阶段排除性别、年龄、照片、籍贯等敏感人口属性，并将“人工最终复核”写入页面和报告，体现负责任的人工智能使用边界。")
    add_body(doc, "实用性方面，系统支持选择内置岗位和匿名简历，也支持读取 TXT 或 Markdown 文件以及直接粘贴文本。招聘人员可快速获得候选人排序，学生可用它演示文本预处理、特征提取、评分和软件测试的完整流程。由于没有付费 API、模型文件或显卡要求，项目可以在普通个人计算机上稳定展示。")

    add_heading(doc, "1.5 报告结构", 2)
    add_body(doc, "第 1 章说明背景、问题和目标；第 2 章分析业务需求及相关技术；第 3 章给出系统架构、数据设计和核心算法；第 4 章介绍实现、测试、实验结果和改进方向；第 5 章总结个人分工、四周进度、自评和心得；最后列出参考文献及代码、视频和运行说明附录。")

    # 第 2 章
    add_heading(doc, "2. 需求分析与相关技术", 1)
    add_heading(doc, "2.1 用户与业务流程", 2)
    add_body(doc, "系统的主要用户是需要进行简历初筛的招聘人员，也可由课程答辩者作为演示者使用。单份匹配流程为：选择目标岗位，输入或载入简历，点击分析，查看得分与证据，必要时导出 JSON 结果。批量流程为：选择岗位，系统读取匿名人才库，对所有简历执行统一算法，按综合得分降序显示排名。两种流程共享同一套匹配核心，保证标准一致。")

    add_heading(doc, "2.2 功能需求", 2)
    add_caption(doc, "表2-1 系统功能需求")
    add_table(
        doc,
        ["编号", "功能模块", "主要输入", "处理过程", "主要输出"],
        [
            ["F01", "岗位选择", "岗位编号", "读取岗位职责与条件", "岗位详情和技能标签"],
            ["F02", "简历输入", "样例或文本文件", "长度检查与文本读取", "统一简历文本"],
            ["F03", "单份匹配", "岗位与简历", "四维评分与解释生成", "总分、分项分、建议"],
            ["F04", "批量排名", "岗位与人才库", "批量评分并稳定排序", "候选人排名表"],
            ["F05", "结果解释", "评分中间结果", "整理技能与风险证据", "亮点和复核要点"],
            ["F06", "结果导出", "单份匹配结果", "序列化为 UTF-8 JSON", "本地结果文件"],
        ],
        [1.4, 2.5, 3.0, 5.4, 4.2],
    )

    add_heading(doc, "2.3 非功能需求", 2)
    add_body(doc, "易用性要求界面操作路径清晰，演示者无需记忆命令；性能要求课程规模数据在点击后快速返回；可靠性要求空文本、未知岗位和无效请求均返回可读提示；可维护性要求算法、数据访问、服务和页面相互分离；兼容性要求支持 Python 3.9 以上及常见现代浏览器；隐私要求测试数据匿名化且默认绑定 127.0.0.1，不对外网开放。")

    add_heading(doc, "2.4 相关技术", 2)
    add_heading(doc, "2.4.1 TF-IDF 与向量空间模型", 3)
    add_body(doc, "TF-IDF 由词频和逆文档频率组成。词频体现词项在当前文本中的重要程度，逆文档频率降低高频通用词的权重并突出稀有词[1-3]。岗位和简历被转换为稀疏向量后，余弦相似度可衡量两个向量的方向接近程度，不直接受文本绝对长度影响。该方法计算量小、结果可复现，适合轻量离线场景。")

    add_heading(doc, "2.4.2 词典规则与信息抽取", 3)
    add_body(doc, "岗位匹配不仅关心整体文本，还需要定位 Python、SQL、Spring Boot、自然语言处理等具体技能。系统维护规范技能名与别名集合，例如将 Vue3 归一为 Vue、将自然语言处理归一为 NLP、将 SpringBoot 归一为 Spring Boot。经验年限通过中英文正则表达式提取最大有效数值，学历则映射为有序等级。规则方法透明、便于修改，也适合数据量有限的教学项目。")

    add_heading(doc, "2.4.3 Python 本地 HTTP 服务", 3)
    add_body(doc, "系统采用 Python 标准库 ThreadingHTTPServer 提供本地静态页面与 JSON 接口。官方文档说明该服务器通过线程处理浏览器连接[4]。项目只绑定本机回环地址，并设置 2 MB 请求体上限、静态路径校验、明确的 MIME 类型和统一异常响应。该服务适合本地课程演示，不作为互联网生产服务器使用。")

    add_heading(doc, "2.5 可行性分析", 2)
    add_body(doc, "技术上，文本规范化、TF-IDF、余弦相似度和规则抽取均可由 Python 标准库实现；经济上，无需购买云服务、模型额度或硬件；操作上，使用浏览器表单和一键启动脚本即可；进度上，项目可拆分为需求设计、模块实现、测试优化和成果整理四个阶段，与任务书四周安排一致。因此方案具备实现条件。")

    # 第 3 章
    add_heading(doc, "3. 系统设计与方法", 1)
    add_heading(doc, "3.1 总体架构", 2)
    add_body(doc, "系统采用分层结构。表示层由 HTML、CSS 和 JavaScript 组成，负责岗位选择、文本输入、结果图形化和排名表格；服务层由 Python HTTP 处理器组成，负责路由、参数校验、静态资源和 JSON 响应；算法层完成文本表示、特征抽取、四维评分及解释；数据层使用 UTF-8 CSV 保存岗位、匿名简历和人工标注。模块之间通过清晰的数据结构连接，便于单独测试。")
    add_picture(doc, DOCS_DIR / "系统总体架构图.png", "图3-1 系统总体架构图")

    add_heading(doc, "3.2 数据设计", 2)
    add_heading(doc, "3.2.1 岗位数据", 3)
    add_body(doc, "岗位表包含 job_id、title、department、location、description、required_skills、min_years 和 min_education 八个字段。required_skills 使用竖线分隔，便于人工维护；算法仍会同时从岗位标题、职责和技能字段中抽取技能，避免单一字段缺失。测试集覆盖数据分析、前端、机器学习、产品运营、Java 后端和 NLP 应用六类岗位。")
    add_heading(doc, "3.2.2 简历与标注数据", 3)
    add_body(doc, "匿名简历表包含 resume_id、name、target_role、years、education、skills、summary 和 experience。系统将结构化字段拼接为带标签的完整文本后送入算法。18 份简历均为课程测试所需的虚构数据，不对应真实个人。标注表为每个岗位指定 2 份相关简历，用于计算 Top-1 准确率、Precision@3 和 Recall@3。")

    add_heading(doc, "3.3 文本预处理", 2)
    add_body(doc, "预处理首先把输入转换为字符串，统一英文小写、连续空白以及常见全角符号。英文内容使用字母数字正则提取单词；中文无需第三方分词库，而是同时生成单字、二元和三元片段。例如“数据分析”可产生“数、据、分、析、数据、据分、分析、数据分、据分析”等词项。技能词典识别出的规范技能还会以独立特征加入向量，从而提高技能名的一致性。")
    add_body(doc, "中文字符 n-gram 的优点是不依赖词典切分，对未登录词和中英文混写较稳健；不足是特征数量较多且语义边界不如专业分词准确。考虑测试集仅 18 份简历，标准库实现的性能完全满足要求。后续扩大数据规模时，可替换为结巴分词、Sentence-BERT 等模型，同时保持外层接口不变。")

    add_heading(doc, "3.4 核心匹配算法", 2)
    add_picture(doc, DOCS_DIR / "匹配处理流程图.png", "图3-2 简历岗位匹配处理流程")

    add_heading(doc, "3.4.1 TF-IDF 相似度", 3)
    add_body(doc, "设词项 t 在文档 d 中出现次数为 n(t,d)，文档词项总数为 Σn(k,d)，则归一化词频为：")
    add_equation(doc, "TF(t,d) = n(t,d) / Σₖ n(k,d)                                      （3.1）")
    add_body(doc, "设参与计算的文本总数为 N，包含词项 t 的文本数为 DF(t)。为避免分母为零并平滑小样本，系统采用：")
    add_equation(doc, "IDF(t) = ln[(1 + N) / (1 + DF(t))] + 1                             （3.2）")
    add_body(doc, "词项权重为 TF 与 IDF 的乘积。岗位向量 q 与简历向量 d 的余弦相似度为：")
    add_equation(doc, "Sim(q,d) = (q · d) / (||q||₂ ||d||₂) × 100                         （3.3）")
    add_body(doc, "单份匹配以一个岗位和一份简历构建文档集合；批量排名则以岗位和全部候选人共同计算文档频率，使同一批候选人使用统一参照。若文本为空，服务层直接拒绝；若向量范数为零，相似度记为 0。")

    add_heading(doc, "3.4.2 技能覆盖率", 3)
    add_body(doc, "技能覆盖率等于候选人已具备的岗位技能数除以岗位要求技能总数。提取时按规范名称去重并保持固定顺序。输出不仅给出百分比，还列出 matched_skills 和 missing_skills。这样即使两名候选人总分接近，复核者仍能看到差异来自哪些技能。")
    add_equation(doc, "Skill = |S_resume ∩ S_job| / |S_job| × 100                         （3.4）")

    add_heading(doc, "3.4.3 经验与学历匹配", 3)
    add_body(doc, "经验匹配使用“候选人年限 / 岗位最低年限”的比例并将上限设为 100，超过最低要求不会无限加分。岗位不限制年限时记为满分。学历按照不限、专科、本科、硕士、博士映射为 0～5 级；达到或超过要求记为满分，未达到时按等级比例给分。该设计将硬性条件纳入评分，但不会因单项不足直接把其他信息全部归零。")

    add_heading(doc, "3.4.4 综合得分与推荐等级", 3)
    add_body(doc, "根据问题性质和可解释性要求，文本相似度与技能覆盖占主要权重，经验和学历用于校正。最终公式如下：")
    add_equation(doc, "Score = 0.40×Sim + 0.35×Skill + 0.15×Experience + 0.10×Education  （3.5）")
    add_caption(doc, "表3-1 综合评分权重与推荐规则")
    add_table(
        doc,
        ["维度/区间", "权重或范围", "设计说明/推荐结论"],
        [
            ["文本相似度", "40%", "衡量岗位职责与简历描述的整体相关度"],
            ["技能覆盖", "35%", "核验岗位明确技能并展示缺口"],
            ["经验匹配", "15%", "比较候选人年限与岗位最低年限"],
            ["学历匹配", "10%", "比较有序学历等级"],
            ["高度匹配", "80～100", "建议优先进入面试"],
            ["较匹配", "65～79.9", "建议进入初筛"],
            ["可考虑", "50～64.9", "建议结合项目经历复核"],
            ["暂不匹配", "0～49.9", "建议保留人才库"],
        ],
        [3.8, 3.2, 9.2],
    )

    add_heading(doc, "3.5 模块与接口设计", 2)
    add_body(doc, "matcher.py 负责技能、年限、学历提取以及单份评分和批量排序；repository.py 负责 CSV 读取、字段校验和简历文本拼接；app.py 提供 GET /api/bootstrap、POST /api/match 和 POST /api/rank 三个接口；evaluate.py 读取人工标注并计算评估指标；static 目录包含页面结构、视觉样式与交互脚本；tests 目录包含算法、数据和接口测试。")
    add_body(doc, "接口只接收 JSON。单份匹配请求包括 job_id 和 resume_text，响应包含岗位信息和完整解释结果；批量排名请求只需 job_id，响应按 total_score 降序排列。静态文件路径在解析后必须位于 static 目录内，避免通过上级路径访问项目外文件。请求体超过 2 MB、岗位不存在或文本为空时均返回 4xx 错误和中文提示。")

    add_heading(doc, "3.6 隐私、公平与使用边界", 2)
    add_body(doc, "招聘属于影响个人机会的高影响场景。NIST AI 风险管理框架强调在人工智能系统生命周期中进行治理、测量和持续风险管理[5]。本项目采取四项限制：只使用岗位相关的能力信息；不采集年龄、性别、照片、民族、籍贯等敏感属性；页面持续提示结果仅用于辅助初筛；测试数据全部匿名且默认不离开本机。")
    add_body(doc, "仍需注意，技能词典、权重和人工标注都可能带有设计者偏好；简历表述能力也不完全等于真实工作能力。因此系统输出不能作为自动淘汰或录用的唯一依据。真实部署前应扩大多样化样本、进行分组公平性评估、建立申诉和人工复核机制，并由用人单位根据法律与管理制度审批。")

    # 第 4 章
    add_heading(doc, "4. 系统实现与实验结果", 1)
    add_heading(doc, "4.1 开发与运行环境", 2)
    add_caption(doc, "表4-1 开发与运行环境")
    add_table(
        doc,
        ["类别", "配置", "用途"],
        [
            ["操作系统", "Windows 11 64 位", "开发、运行与浏览器测试"],
            ["开发语言", "Python 3.12.13", "算法、数据处理和本地服务"],
            ["前端技术", "HTML5 / CSS3 / JavaScript", "本地网页与可视化交互"],
            ["数据格式", "UTF-8 CSV / JSON", "岗位、简历、标注和结果"],
            ["测试框架", "unittest / http.client", "算法、数据和接口自动测试"],
            ["外部依赖", "无", "核心项目只使用 Python 标准库"],
        ],
        [3.0, 6.3, 6.9],
    )

    add_heading(doc, "4.2 关键功能实现", 2)
    add_heading(doc, "4.2.1 核心算法实现", 3)
    add_body(doc, "tokenize 函数先调用 normalize_text，然后分别提取英文词项和中文字符 n-gram，并追加规范技能特征。semantic_similarities 将岗位和候选文本转为 Counter，统计文档频率，生成稀疏字典向量并计算余弦值。score_resume 计算四个维度、综合分和推荐等级，同时组织 strengths 与 risks；rank_resumes 复用同一评分函数并执行稳定排序。")
    add_body(doc, "这种实现没有把算法逻辑写在页面或接口中。测试可以直接向核心函数传入普通字典和字符串，从而快速验证边界值。批量模式一次计算所有候选人的 IDF，避免逐份计算时参照集合变化。排序键先取负得分，再取简历编号，保证分数相同情况下结果仍可复现。")

    add_heading(doc, "4.2.2 本地服务实现", 3)
    add_body(doc, "app.py 使用 ThreadingHTTPServer 监听 127.0.0.1:8765，主页加载后通过 /api/bootstrap 一次性获得岗位摘要、匿名简历列表和统计数量。POST 接口先限制请求体大小并解析 JSON，再校验岗位编号。服务端响应均采用 ensure_ascii=False，保证中文不被转义；静态文件根据扩展名明确设置 text/css 和 application/javascript，解决 Windows MIME 注册差异导致的样式加载问题。")

    add_heading(doc, "4.2.3 交互界面实现", 3)
    add_body(doc, "页面采用深绿色侧边导航和浅色内容区，将单份匹配、批量排名和方法说明分为三个视图。选择岗位后立即展示职责、学历、年限和技能标签；选择匿名样例时自动填充文本；分析后以环形总分、四个进度条、技能标签和双栏提示展示结果。批量模式使用排名表，并对前三名突出显示。移动端宽度下，布局会自动切换为单列。")

    add_picture(doc, DOCS_DIR / "系统首页.png", "图4-1 系统首页与单份匹配输入区")
    add_picture(doc, DOCS_DIR / "系统匹配结果界面.png", "图4-2 单份简历四维匹配结果")
    add_picture(doc, DOCS_DIR / "系统批量排名界面.png", "图4-3 Java 后端岗位批量排名结果")

    add_heading(doc, "4.3 测试设计与执行", 2)
    add_heading(doc, "4.3.1 测试策略", 3)
    add_body(doc, "测试分为三个层次。单元测试验证技能别名、经验年限、学历等级、空输入、得分范围和排序；数据测试验证岗位与简历数量、编号唯一性、字段完整性及每个岗位是否存在标注；接口测试在随机空闲端口启动本地服务器，真实发送 bootstrap、match 和 rank 请求，验证成功与异常响应。最后在浏览器中人工执行单份匹配和批量排名，检查页面样式、交互反馈与控制台错误。")

    add_caption(doc, "表4-2 主要功能与异常测试结果")
    add_table(
        doc,
        ["编号", "测试内容", "预期结果", "实际结果", "结论"],
        [
            ["T01", "Python/Vue3/SpringBoot/NLP 别名提取", "归一为规范技能名", "全部正确识别", "通过"],
            ["T02", "中英文多段经验年限", "取最大有效年限", "正确提取 2.5 年", "通过"],
            ["T03", "硕士、本科、专科学历比较", "等级单调递减", "顺序符合设计", "通过"],
            ["T04", "空简历请求", "拒绝并给出中文错误", "返回“简历内容不能为空”", "通过"],
            ["T05", "Java 岗位批量排序", "R013 排名第一", "R013 排名第一", "通过"],
            ["T06", "岗位与简历数据校验", "6 岗位、18 简历且编号唯一", "数量与唯一性正确", "通过"],
            ["T07", "未知岗位接口请求", "HTTP 400 与可读提示", "返回 400 和岗位提示", "通过"],
            ["T08", "浏览器样式和交互", "三视图正常且无控制台错误", "样式、匹配、排名均正常", "通过"],
        ],
        [1.2, 4.7, 4.8, 4.8, 1.7],
    )
    add_body(doc, "最终执行命令为“python -m unittest discover -s tests -v”。实际共运行 11 项自动测试，用时约 0.58 秒，全部通过；随后执行 compileall 未发现语法错误。浏览器测试过程中发现 Windows 将 .css 识别为 application/x-css，导致页面样式未应用。修正为显式 MIME 映射后重新加载，浏览器读取到 137 条样式规则，单份匹配和批量排名均无控制台警告或错误。该问题体现了测试对实际交付质量的作用。")

    add_heading(doc, "4.4 排名评估", 2)
    add_heading(doc, "4.4.1 评估指标", 3)
    add_body(doc, "信息检索通常使用准确率与召回率衡量排序结果[3]。本项目定义：Top-1 准确率表示每个岗位排名第一的简历是否属于人工相关集合；Precision@3 表示前三名中相关简历所占比例；Recall@3 表示每个岗位的相关简历有多少进入前三名。人工为每个岗位标注 2 份相关简历，因此理想 Recall@3 为 100%，而当第三名是相近方向但未标为相关时，Precision@3 的上限为 2/3。")
    add_equation(doc, "Precision@3 = 前 3 名中的相关简历数 / 3                               （4.1）")
    add_equation(doc, "Recall@3 = 前 3 名中的相关简历数 / 该岗位相关简历总数                    （4.2）")

    add_heading(doc, "4.4.2 评估结果", 3)
    add_caption(doc, "表4-3 标注测试集评估结果")
    add_table(
        doc,
        ["指标", "结果", "解释"],
        [
            ["测试岗位数", "6", "覆盖数据、前端、算法、运营、后端和 NLP"],
            ["匿名简历数", "18", "每类方向包含相关与相近候选人"],
            ["Top-1 Accuracy", "100%", "6 个岗位的第一名均属于人工相关集合"],
            ["Precision@3", "66.67%", "平均每个岗位前三名中有 2 名相关候选人"],
            ["Recall@3", "100%", "12 份人工相关简历全部进入对应岗位前三名"],
        ],
        [4.3, 3.0, 9.3],
    )
    add_body(doc, "六个岗位的第一名依次为 R001、R004、R007、R010、R013 和 R016，均与目标岗位方向一致。每个岗位标注的 2 名相关候选人都进入前三名，说明技能规则和文本相关度能够抓住主要人岗特征。第三名通常是具备部分交叉能力的候选人，例如产品运营岗位第三名为具备 A/B 测试的数据分析师，属于需要人工进一步判断的合理结果。")

    add_heading(doc, "4.5 局限性与改进", 2)
    add_body(doc, "第一，测试集规模较小且由项目设计者构建，不能代表真实招聘数据分布；后续应邀请多人独立标注并使用交叉验证。第二，字符 n-gram 能处理中文但缺乏深层语义理解，对同义改写和否定表达的识别有限；后续可引入轻量中文句向量模型并保留当前规则作为硬性条件。第三，技能词典需要人工维护，可增加后台配置和词典版本记录。第四，当前经验抽取取最大年限，无法区分实习、全职和并行项目，后续可加入时间段解析。")
    add_body(doc, "第五，综合权重依据课程场景设定，真实岗位应由领域人员通过历史数据和业务目标校准，并进行敏感性分析。第六，系统当前只读取文本文件；后续可在不上传云端的前提下增加 PDF 和 DOCX 本地解析。第七，系统没有用户账户和权限控制，因此只能在本机使用，不应直接暴露到公网。Python 官方也明确指出 http.server 不适合作为生产服务器[4]，如需部署应迁移至成熟 Web 框架和反向代理。")

    # 第 5 章
    add_heading(doc, "5. 个人分工、心得与总结", 1)
    add_heading(doc, "5.1 个人分工", 2)
    add_body(doc, "任务书要求不分组、每人一个选题。本项目由赵子恒独立完成，包括选题与需求分析、技术路线设计、核心算法编写、匿名测试数据构建、本地服务与网页界面实现、自动测试、浏览器兼容性修复、实验评估、运行说明、演示材料和实训报告撰写。独立开发有利于形成完整知识链，也要求对算法效果、软件质量和使用边界共同负责。")

    add_heading(doc, "5.2 四周实施过程", 2)
    add_caption(doc, "表5-1 实训进度与成果")
    add_table(
        doc,
        ["阶段", "主要任务", "阶段成果"],
        [
            ["第1周", "选题、问题定义、需求分析、方案设计", "需求清单、四维评分方案、系统架构"],
            ["第2周", "数据设计、算法与服务模块开发", "岗位与简历数据、核心匹配和 API"],
            ["第3周", "界面完善、自动测试、浏览器验证", "三视图界面、11 项测试、兼容性修复"],
            ["第4周", "评估、报告、说明和答辩材料整理", "实验指标、Word 报告、README、演示稿"],
        ],
        [2.4, 7.2, 7.0],
    )

    add_heading(doc, "5.3 自评依据", 2)
    add_caption(doc, "表5-2 项目自评分数明细")
    add_table(
        doc,
        ["考核项目", "权重", "建议得分", "依据"],
        [
            ["项目创新性与实用性", "25", "23", "离线、可解释、无付费 API，具备实际初筛流程"],
            ["功能实现与代码质量", "25", "24", "主要功能完整，模块分离，11 项自动测试通过"],
            ["文档与演示材料完整性", "20", "19", "报告、README、测试数据、截图和演示稿齐全"],
            ["团队协作与分工合理性", "15", "13", "按个人项目要求独立完成，过程与职责明确"],
            ["平时表现与问题应对", "15", "13", "发现并修复 Windows MIME 兼容性问题"],
            ["合计", "100", "92", "建议自评分数 92 分"],
        ],
        [5.3, 2.0, 2.6, 8.7],
    )
    add_body(doc, "自评分数为 92 分。未给满分的主要原因是测试数据规模有限、尚未接入真实匿名业务数据，也未实现 PDF/DOCX 解析和生产级权限体系。该分数既反映当前成果已完整满足课程任务书的主要交付要求，也保留了对真实应用差距的客观判断。")

    add_heading(doc, "5.4 心得体会", 2)
    add_body(doc, "本次实训让我认识到，人工智能项目不等于调用一个大型模型。针对明确的问题选择合适复杂度的方法，并把数据、算法、界面、测试和解释串联起来，同样能够形成有价值的智能应用。TF-IDF 本身并不复杂，但只有加入岗位规则、异常处理、排名评估和结果展示后，才真正成为可操作的系统。")
    add_body(doc, "另一个重要收获是测试不能停留在函数是否运行。自动测试证明了算法和接口的基本正确性，真实浏览器检查又发现了 Windows MIME 类型导致样式失效的问题。这个问题在只看代码时很难发现，却会直接影响答辩效果。通过定位响应头并增加显式映射，系统从“能返回数据”改进为“能够稳定展示”。")
    add_body(doc, "最后，招聘辅助系统涉及个人机会，准确率并不是唯一目标。透明权重、证据展示、敏感属性排除和人工复核提示同样重要。NIST AI RMF 将治理、映射、测量和管理贯穿系统生命周期[5]，这种思路使我在设计阶段就考虑错误影响、数据边界和使用责任，而不是等功能完成后再补充说明。")

    add_heading(doc, "5.5 项目总结", 2)
    add_body(doc, "本项目完成了一套可离线运行的智能简历筛选与岗位匹配系统。系统以 Python 为主要语言，自主实现中英文混合文本处理、TF-IDF 余弦相似度、技能归一化、年限和学历提取、四维综合评分、单份解释和批量排序；同时提供浏览器界面、匿名测试数据、自动测试、评估脚本和完整运行说明。实际测试表明主要功能稳定，标注集相关简历能够进入目标岗位前三名。")
    add_body(doc, "项目达到了任务书中问题定义、系统设计、技术实现、测试改进和总结的要求，也形成了源码、测试数据、使用说明、报告和演示脚本等交付物。后续若继续开发，将优先扩充真实匿名数据、加入本地文档解析与句向量模型、建设技能词典配置界面，并开展权重敏感性与公平性评估。")

    # 参考文献
    add_heading(doc, "参考文献", 1)
    references = [
        "[1] SPÄRCK JONES K. A statistical interpretation of term specificity and its application in retrieval[J]. Journal of Documentation, 1972, 28(1): 11-21. DOI:10.1108/EB026526.",
        "[2] SALTON G, BUCKLEY C. Term-weighting approaches in automatic text retrieval[J]. Information Processing & Management, 1988, 24(5): 513-523. DOI:10.1016/0306-4573(88)90021-0.",
        "[3] MANNING C D, RAGHAVAN P, SCHÜTZE H. Introduction to Information Retrieval[M]. Cambridge: Cambridge University Press, 2008.",
        "[4] PYTHON SOFTWARE FOUNDATION. http.server—HTTP servers: Python 3.12.13 documentation[EB/OL]. https://docs.python.org/3.12/library/http.server.html, 2026-03-07.",
        "[5] TABASSI E. Artificial Intelligence Risk Management Framework (AI RMF 1.0)[R]. Gaithersburg: National Institute of Standards and Technology, 2023. DOI:10.6028/NIST.AI.100-1.",
        "[6] AGGARWAL C C. Machine Learning for Text[M]. Cham: Springer, 2018.",
        "[7] HAN J, KAMBER M, PEI J. Data Mining: Concepts and Techniques[M]. 3rd ed. Waltham: Morgan Kaufmann, 2011.",
        "[8] 全国信息安全标准化技术委员会. GB/T 35273—2020 信息安全技术 个人信息安全规范[S]. 北京: 中国标准出版社, 2020.",
    ]
    for reference in references:
        paragraph = doc.add_paragraph()
        paragraph.paragraph_format.first_line_indent = Pt(-24)
        paragraph.paragraph_format.left_indent = Pt(24)
        paragraph.paragraph_format.line_spacing_rule = WD_LINE_SPACING.ONE_POINT_FIVE
        run = paragraph.add_run(reference)
        style_run(run, size=10.5, font="宋体")

    # 附录
    add_heading(doc, "附录", 1)
    add_heading(doc, "附录A 代码、视频与运行说明", 2)
    add_body(doc, "Git 仓库链接：待上传后填写（提交前将完整项目上传到可访问的 Git 仓库，并替换本句）。", bold_lead="Git 仓库链接：")
    add_body(doc, "演示视频链接：待上传后填写（录制约 5 分钟演示视频并上传网盘后替换本句）。", bold_lead="演示视频链接：")
    add_body(doc, "本地运行步骤：① 安装 Python 3.9 或以上版本；② 解压项目并进入根目录；③ Windows 用户双击“启动系统.bat”，其他系统执行“python app.py”；④ 浏览器访问 http://127.0.0.1:8765；⑤ 在终端按 Ctrl+C 停止服务。项目核心功能不依赖第三方库。")
    add_body(doc, "自动测试命令：python -m unittest discover -s tests -v；评估命令：python evaluate.py。后者会把 Top-1、Precision@3、Recall@3 和每个岗位前三名写入 docs/evaluation_results.json。")

    add_heading(doc, "附录B 主要文件说明", 2)
    add_table(
        doc,
        ["文件或目录", "说明"],
        [
            ["app.py", "本地 HTTP 服务、静态资源、参数校验和 JSON API"],
            ["matcher.py", "文本预处理、TF-IDF、技能抽取和综合评分"],
            ["repository.py", "岗位、简历和标注 CSV 读取与校验"],
            ["evaluate.py", "Top-1、Precision@3 和 Recall@3 计算"],
            ["data/", "6 个岗位、18 份匿名简历、人工标注和演示文本"],
            ["static/", "HTML 页面、CSS 视觉样式和 JavaScript 交互"],
            ["tests/", "算法、数据和接口的 11 项自动测试"],
            ["README.md", "环境、运行、演示、测试与目录说明"],
        ],
        [5.0, 12.5],
    )

    add_heading(doc, "附录C 五分钟演示提纲", 2)
    add_body(doc, "0:00～0:40 介绍问题、项目目标和离线特点；0:40～1:40 选择 Python 数据分析师和匿名简历，展示输入方式；1:40～2:40 点击分析，讲解总分、四维权重、匹配技能和复核要点；2:40～3:35 切换 Java 后端岗位，展示 18 人批量排名；3:35～4:20 讲解 TF-IDF、技能规则与人工复核边界；4:20～5:00 展示测试结果、项目目录、运行说明和改进方向。完整逐字稿位于 docs/演示视频讲解稿.md。")

    # 文档核心属性
    props = doc.core_properties
    props.title = "智能简历筛选与岗位匹配系统专业综合实训报告"
    props.subject = "专业综合实训"
    props.author = "赵子恒"
    props.keywords = "简历筛选, 岗位匹配, TF-IDF, Python, 可解释人工智能"
    props.comments = "依据《专业综合实训》任务书和学校报告模板生成"

    doc.save(str(OUTPUT))
    return OUTPUT


if __name__ == "__main__":
    result = build_report()
    print(f"报告已生成：{result}")
