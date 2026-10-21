#!/usr/bin/env python3
"""
convert_continuity_sheet.py
把 ai-continuity-sheet 输出的 Markdown 文件转换为 Excel (.xlsx)
用法：python3 convert_continuity_sheet.py <输入文件.md> [输出文件.xlsx]
"""

import re
import sys
from pathlib import Path

try:
    from openpyxl import Workbook
    from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
    from openpyxl.utils import get_column_letter
except ImportError:
    print("缺少依赖，请先运行：pip install openpyxl")
    sys.exit(1)


# ── 样式常量 ──────────────────────────────────────────────
HEADER_FILL_MAIN   = PatternFill("solid", fgColor="2C3E50")   # 主表表头：深蓝灰
HEADER_FILL_DIR    = PatternFill("solid", fgColor="4A235A")   # 导演表表头：深紫
HEADER_FONT        = Font(color="FFFFFF", bold=True, name="微软雅黑", size=10)
CELL_FONT          = Font(name="微软雅黑", size=10)
WRAP_ALIGN         = Alignment(wrap_text=True, vertical="top")
THIN               = Side(border_style="thin", color="CCCCCC")
CELL_BORDER        = Border(left=THIN, right=THIN, top=THIN, bottom=THIN)

# 剧本原文块样式
SCRIPT_FILL        = PatternFill("solid", fgColor="FBF7E9")   # 浅米黄底
SCRIPT_FONT        = Font(name="微软雅黑", size=10, color="4A3B2A")
SCRIPT_ALIGN       = Alignment(wrap_text=True, vertical="top", horizontal="left")

# 统一场记表列宽（字符单位）
UNIFIED_COL_WIDTHS = {
    "集数": 8, "场次": 8, "片段": 8, "出场人物": 18,
    "场景": 28, "道具": 22, "摄影": 32,
    "灯光/色卡": 20, "台词": 28, "时长": 8,
    "微表情情绪指导": 32, "动作表演指导": 32, "剧情大纲": 26,
}


def parse_md_table(lines: list[str]) -> tuple[list[str], list[list[str]]]:
    """解析 Markdown 表格，返回 (headers, rows)"""
    headers: list[str] = []
    rows: list[list[str]] = []
    for line in lines:
        line = line.strip()
        if not line.startswith("|"):
            continue
        cells = [c.strip() for c in line.strip("|").split("|")]
        if all(re.fullmatch(r"[-: ]+", c) for c in cells if c):
            continue  # 分隔行
        if not headers:
            headers = cells
        else:
            # 补齐列数
            while len(cells) < len(headers):
                cells.append("")
            rows.append(cells[: len(headers)])
    return headers, rows


def extract_script_text(md_text: str) -> str:
    """
    从 Markdown 中提取剧本原文块。
    识别以「剧本原文」「原始剧本」「剧本」为标题的代码块或段落。
    返回纯文本，没有则返回空字符串。
    """
    # 优先匹配代码围栏块：```script / ```text / ``` 下的剧本原文节
    sections = re.split(r"\n(?=#{1,3}\s)", md_text)
    for sec in sections:
        first_line = sec.splitlines()[0] if sec.splitlines() else ""
        if re.search(r"剧本原文|原始剧本|剧本文本", first_line):
            # 提取代码围栏内容
            fenced = re.search(r"```[^\n]*\n(.*?)```", sec, re.DOTALL)
            if fenced:
                return fenced.group(1).strip()
            # 无围栏则取标题后所有非表格文本
            lines = sec.splitlines()[1:]
            text_lines = [l for l in lines if not l.startswith("|") and not l.startswith("#")]
            result = "\n".join(text_lines).strip()
            if result:
                return result
    return ""


def extract_tables(md_text: str) -> dict[str, tuple[list[str], list[list[str]]]]:
    """
    从 Markdown 文本中提取统一场记表（或兼容旧版两张表格式）。
    返回 {"场记表": (headers, rows)} 或旧格式的两张表。
    """
    result: dict[str, tuple[list[str], list[list[str]]]] = {}
    sections = re.split(r"\n(?=#{1,3}\s)", md_text)
    for sec in sections:
        sec_lines = sec.splitlines()
        title_line = sec_lines[0] if sec_lines else ""
        if "场记表" in title_line or "统一" in title_line:
            key = "场记表"
        elif "主表" in title_line or "制作参考" in title_line:
            key = "主表"
        elif "导演" in title_line or "表演参考" in title_line:
            key = "导演创作表"
        else:
            continue
        headers, rows = parse_md_table(sec_lines[1:])
        if headers:
            result[key] = (headers, rows)

    # 兼容：如果有主表和导演创作表，尝试合并为单张表
    if "场记表" not in result and "主表" in result and "导演创作表" in result:
        main_h, main_r = result["主表"]
        dir_h, dir_r = result["导演创作表"]
        # 去掉导演表的前三列（集数/场次/片段，与主表重复）
        extra_h = dir_h[3:]
        merged_h = main_h + extra_h
        merged_r = []
        for i, row in enumerate(main_r):
            dir_row = dir_r[i] if i < len(dir_r) else []
            extra = dir_row[3:] if len(dir_row) > 3 else [""] * len(extra_h)
            merged_r.append(row + extra)
        result["场记表"] = (merged_h, merged_r)

    return result


def write_sheet(ws, headers: list[str], rows: list[list[str]],
                col_widths: dict[str, int], header_fill: PatternFill,
                script_text: str = "") -> None:
    """把数据写入一个工作表并应用样式"""
    num_cols = len(headers)

    # ── 第一行：剧本原文（合并所有列） ──────────────────────
    if script_text:
        ws.append([script_text] + [""] * (num_cols - 1))
        ws.merge_cells(start_row=1, start_column=1,
                       end_row=1, end_column=num_cols)
        script_cell = ws.cell(row=1, column=1)
        script_cell.fill = SCRIPT_FILL
        script_cell.font = SCRIPT_FONT
        script_cell.alignment = SCRIPT_ALIGN
        script_cell.border = CELL_BORDER
        # 行高按内容估算（每 100 字约 15pt，最低 60pt）
        estimated_height = max(60, (len(script_text) // 100 + 1) * 15)
        ws.row_dimensions[1].height = estimated_height
        header_row = 2
    else:
        header_row = 1

    # ── 表头行 ──────────────────────────────────────────────
    ws.append(headers)
    for col_idx, header in enumerate(headers, start=1):
        cell = ws.cell(row=header_row, column=col_idx)
        cell.fill = header_fill
        cell.font = HEADER_FONT
        cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
        cell.border = CELL_BORDER
        width = col_widths.get(header, 16)
        ws.column_dimensions[get_column_letter(col_idx)].width = width

    # ── 数据行 ──────────────────────────────────────────────
    for row_data in rows:
        ws.append(row_data)
        row_idx = ws.max_row
        for col_idx in range(1, num_cols + 1):
            cell = ws.cell(row=row_idx, column=col_idx)
            cell.font = CELL_FONT
            cell.alignment = WRAP_ALIGN
            cell.border = CELL_BORDER

    # 冻结表头行（含剧本行时冻结第3行起，否则第2行起）
    freeze_row = header_row + 1
    ws.freeze_panes = f"A{freeze_row}"
    ws.row_dimensions[header_row].height = 28


def convert(md_path: Path, xlsx_path: Path) -> None:
    md_text = md_path.read_text(encoding="utf-8")
    tables = extract_tables(md_text)
    script_text = extract_script_text(md_text)

    if script_text:
        print(f"  ✔ 剧本原文：{len(script_text)} 字，写入首行合并单元格")
    else:
        print("  ℹ 未找到剧本原文块，跳过首行合并单元格")

    if not tables:
        print("❌ 未在 Markdown 文件中找到场记表，请检查文件格式。")
        sys.exit(1)

    wb = Workbook()
    wb.remove(wb.active)  # 移除默认空 sheet

    if "场记表" in tables:
        headers, rows = tables["场记表"]
        ws = wb.create_sheet("场记表")
        write_sheet(ws, headers, rows, UNIFIED_COL_WIDTHS, HEADER_FILL_MAIN, script_text)
        print(f"  ✔ 场记表：{len(rows)} 行")
    else:
        # 兼容旧格式：分别处理主表和导演创作表
        if "主表" in tables:
            headers, rows = tables["主表"]
            ws_main = wb.create_sheet("主表（制作参考）")
            write_sheet(ws_main, headers, rows, UNIFIED_COL_WIDTHS, HEADER_FILL_MAIN, script_text)
            print(f"  ✔ 主表：{len(rows)} 行")

        if "导演创作表" in tables:
            headers, rows = tables["导演创作表"]
            ws_dir = wb.create_sheet("导演创作表（表演参考）")
            write_sheet(ws_dir, headers, rows, UNIFIED_COL_WIDTHS, HEADER_FILL_DIR, script_text)
            print(f"  ✔ 导演创作表：{len(rows)} 行")

    wb.save(xlsx_path)
    print(f"\n已保存至：{xlsx_path}")


def main() -> None:
    if len(sys.argv) < 2:
        print("用法：python3 convert_continuity_sheet.py <输入文件.md> [输出文件.xlsx]")
        sys.exit(1)

    md_path = Path(sys.argv[1])
    if not md_path.exists():
        print(f"❌ 找不到文件：{md_path}")
        sys.exit(1)

    xlsx_path = Path(sys.argv[2]) if len(sys.argv) >= 3 else md_path.with_suffix(".xlsx")
    print(f"转换：{md_path} → {xlsx_path}")
    convert(md_path, xlsx_path)


if __name__ == "__main__":
    main()
