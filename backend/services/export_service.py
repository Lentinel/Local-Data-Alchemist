"""导出服务：提供 PDF 报告和 Excel 文件清单导出功能。"""

import io
import csv
from datetime import datetime
from pathlib import Path

from fastapi import HTTPException
from fastapi.responses import StreamingResponse


def _format_size(size_bytes: int) -> str:
    """格式化文件大小。"""
    if size_bytes < 1024:
        return f"{size_bytes} B"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.1f} KB"
    elif size_bytes < 1024 * 1024 * 1024:
        return f"{size_bytes / (1024 * 1024):.1f} MB"
    else:
        return f"{size_bytes / (1024 * 1024 * 1024):.1f} GB"


def generate_pdf_report(
    target_path: str,
    files_info: list[dict],
    analysis: dict,
    plan: list[dict] = None,
    execution_results: list[dict] = None,
) -> StreamingResponse:
    """生成 PDF 整理报告。
    
    Args:
        target_path: 目标目录路径
        files_info: 文件信息列表
        analysis: 分析结果
        plan: 执行计划（可选）
        execution_results: 执行结果（可选）
        
    Returns:
        StreamingResponse 包含 PDF 文件
    """
    try:
        from reportlab.lib.pagesizes import A4
        from reportlab.lib import colors
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib.units import mm
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
        from reportlab.pdfbase import pdfmetrics
        from reportlab.pdfbase.ttfonts import TTFont
    except ImportError:
        raise HTTPException(status_code=500, detail="PDF 导出库未安装，请运行: pip install reportlab")

    # 尝试注册中文字体
    font_name = "Helvetica"
    try:
        # Windows 系统字体路径
        font_paths = [
            "C:/Windows/Fonts/msyh.ttc",
            "C:/Windows/Fonts/simsun.ttc",
            "C:/Windows/Fonts/simhei.ttf",
        ]
        for fp in font_paths:
            if Path(fp).exists():
                pdfmetrics.registerFont(TTFont("ChineseFont", fp))
                font_name = "ChineseFont"
                break
    except Exception:
        pass

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, topMargin=20 * mm, bottomMargin=20 * mm)
    
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        "CustomTitle",
        parent=styles["Title"],
        fontName=font_name,
        fontSize=18,
        spaceAfter=12,
    )
    heading_style = ParagraphStyle(
        "CustomHeading",
        parent=styles["Heading2"],
        fontName=font_name,
        fontSize=14,
        spaceBefore=12,
        spaceAfter=6,
    )
    body_style = ParagraphStyle(
        "CustomBody",
        parent=styles["Normal"],
        fontName=font_name,
        fontSize=10,
        spaceAfter=4,
    )
    
    elements = []
    
    # 标题
    elements.append(Paragraph("Local Data Alchemist - 整理报告", title_style))
    elements.append(Paragraph(f"生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", body_style))
    elements.append(Paragraph(f"目标目录: {target_path}", body_style))
    elements.append(Spacer(1, 12))
    
    # 概览
    elements.append(Paragraph("一、文件概览", heading_style))
    total_files = analysis.get("total_files", len(files_info))
    total_size = sum(f.get("size", 0) for f in files_info)
    elements.append(Paragraph(f"总文件数: {total_files}", body_style))
    elements.append(Paragraph(f"总大小: {_format_size(total_size)}", body_style))
    elements.append(Spacer(1, 6))
    
    # 分类统计
    categories = analysis.get("categories", [])
    if categories:
        elements.append(Paragraph("二、分类统计", heading_style))
        cat_data = [["分类", "文件数"]]
        for cat in categories:
            cat_data.append([cat.get("label", cat.get("key", "")), str(cat.get("count", 0))])
        
        cat_table = Table(cat_data, colWidths=[200, 100])
        cat_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.grey),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
            ("FONTNAME", (0, 0), (-1, -1), font_name),
            ("FONTSIZE", (0, 0), (-1, -1), 10),
            ("ALIGN", (1, 0), (1, -1), "CENTER"),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.Color(0.95, 0.95, 0.95)]),
        ]))
        elements.append(cat_table)
        elements.append(Spacer(1, 12))
    
    # 文件清单
    elements.append(Paragraph("三、文件清单", heading_style))
    file_data = [["文件名", "分类", "大小"]]
    for f in files_info[:50]:  # 最多显示50个文件
        file_data.append([
            f.get("name", "")[:40],
            f.get("category", "unknown"),
            _format_size(f.get("size", 0)),
        ])
    if len(files_info) > 50:
        file_data.append([f"... 还有 {len(files_info) - 50} 个文件", "", ""])
    
    file_table = Table(file_data, colWidths=[250, 100, 80])
    file_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.grey),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
        ("FONTNAME", (0, 0), (-1, -1), font_name),
        ("FONTSIZE", (0, 0), (-1, -1), 8),
        ("ALIGN", (2, 0), (2, -1), "RIGHT"),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.Color(0.95, 0.95, 0.95)]),
    ]))
    elements.append(file_table)
    elements.append(Spacer(1, 12))
    
    # 执行计划
    if plan:
        elements.append(Paragraph("四、执行计划", heading_style))
        plan_data = [["文件", "操作", "目标路径"]]
        for item in plan[:30]:
            action_labels = {
                "rename_and_move": "重命名移动",
                "move": "移动",
                "delete": "删除",
                "keep": "保留",
            }
            plan_data.append([
                item.get("file", "")[:35],
                action_labels.get(item.get("action", ""), item.get("action", "")),
                (item.get("target_path", "") or "-")[:35],
            ])
        if len(plan) > 30:
            plan_data.append([f"... 还有 {len(plan) - 30} 条操作", "", ""])
        
        plan_table = Table(plan_data, colWidths=[180, 80, 180])
        plan_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.Color(0.2, 0.6, 0.8)),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
            ("FONTNAME", (0, 0), (-1, -1), font_name),
            ("FONTSIZE", (0, 0), (-1, -1), 8),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.Color(0.93, 0.96, 1.0)]),
        ]))
        elements.append(plan_table)
        elements.append(Spacer(1, 12))
    
    # 执行结果
    if execution_results:
        elements.append(Paragraph("五、执行结果", heading_style))
        success_count = sum(1 for r in execution_results if r.get("status") == "success")
        failed_count = sum(1 for r in execution_results if r.get("status") in ("failed", "error"))
        elements.append(Paragraph(f"成功: {success_count}，失败: {failed_count}", body_style))
    
    # 建议
    recommendations = analysis.get("recommendations", [])
    if recommendations:
        section_num = "六" if execution_results else ("五" if plan else "四")
        elements.append(Paragraph(f"{section_num}、AI 建议", heading_style))
        for rec in recommendations:
            elements.append(Paragraph(f"• {rec}", body_style))
    
    doc.build(elements)
    buffer.seek(0)
    
    filename = f"alchemist_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
    return StreamingResponse(
        buffer,
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


def generate_excel_export(
    target_path: str,
    files_info: list[dict],
    plan: list[dict] = None,
) -> StreamingResponse:
    """生成 Excel 格式的文件清单。
    
    Args:
        target_path: 目标目录路径
        files_info: 文件信息列表
        plan: 执行计划（可选）
        
    Returns:
        StreamingResponse 包含 CSV 文件（Excel 兼容）
    """
    buffer = io.StringIO()
    writer = csv.writer(buffer)
    
    # 写入文件清单
    writer.writerow(["文件名", "相对路径", "扩展名", "分类", "大小(字节)", "大小(可读)"])
    for f in files_info:
        writer.writerow([
            f.get("name", ""),
            f.get("path", ""),
            f.get("extension", ""),
            f.get("category", "unknown"),
            f.get("size", 0),
            _format_size(f.get("size", 0)),
        ])
    
    # 如果有计划，添加计划 sheet
    if plan:
        writer.writerow([])
        writer.writerow(["--- 执行计划 ---"])
        writer.writerow(["文件", "操作", "目标路径", "理由", "置信度"])
        for item in plan:
            writer.writerow([
                item.get("file", ""),
                item.get("action", ""),
                item.get("target_path", "") or "-",
                item.get("reason", ""),
                item.get("confidence", ""),
            ])
    
    buffer.seek(0)
    content = buffer.getvalue().encode("utf-8-sig")  # BOM for Excel compatibility
    
    filename = f"alchemist_files_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    return StreamingResponse(
        io.BytesIO(content),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )
