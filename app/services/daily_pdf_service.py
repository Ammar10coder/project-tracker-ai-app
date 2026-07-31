import os
import logging
from datetime import datetime
from collections import defaultdict
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle

import paths
from app import config
from app.services.compare_service import get_daily_comparison
from app.services.drive_service import DriveManager
from app.services.email_service import send_email_with_pdf

logger = logging.getLogger(__name__)

# All local PDF reports are organized under this folder, one subfolder per employee:
# reports/<Employee_Name>/<Employee_Name>_report.pdf
REPORTS_ROOT = paths.REPORTS_DIR


def safe_str(val, default="Untitled Task"):
    """Ensures value is never None or empty and escapes special characters for ReportLab."""
    if not val:
        return default
    return str(val).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def generate_pdf_report(pdf_path="daily_report.pdf", employee_name="Ammar", comparison_data=None):
    """
    Generates a PDF progress report for a specific employee.
    """
    if comparison_data is None:
        comparison_data = []

    styles = getSampleStyleSheet()

    title_style = ParagraphStyle(
        'DocTitle',
        parent=styles['Heading1'],
        fontSize=20,
        leading=24,
        textColor=colors.HexColor('#1E293B'),
        spaceAfter=12
    )

    meta_style = ParagraphStyle(
        'MetaText',
        parent=styles['Normal'],
        fontSize=10,
        leading=14,
        textColor=colors.HexColor('#475569')
    )

    cell_style = ParagraphStyle(
        'CellText',
        parent=styles['Normal'],
        fontSize=9,
        leading=13,
        textColor=colors.HexColor('#1E293B')
    )

    header_cell_style = ParagraphStyle(
        'HeaderCellText',
        parent=styles['Normal'],
        fontSize=10,
        leading=12,
        textColor=colors.white,
        fontName='Helvetica-Bold'
    )

    story = [
        Paragraph(f"PROJECT STATUS DASHBOARD: {employee_name.upper()}", title_style),
        Paragraph(f"<b>Employee:</b> {employee_name} | <b>Chat Group:</b> company progress report", meta_style),
        Spacer(1, 15)
    ]

    # --- Metrics Section ---
    total_count = len(comparison_data)
    completed_count = sum(1 for t in comparison_data if t.get('label') == "Completed")
    progressed_count = sum(1 for t in comparison_data if t.get('label') in ["Progressed", "New"])
    stalled_count = sum(1 for t in comparison_data if t.get('label') == "Stalled")

    progress_pct = f"{int((completed_count / total_count) * 100)}%" if total_count > 0 else "0%"

    metrics_data = [
        ["Overall Progress", "Completed Tasks", "Progressed / New", "Stalled / Regressed"],
        [progress_pct, str(completed_count), str(progressed_count), str(stalled_count)]
    ]

    metrics_table = Table(metrics_data, colWidths=[120, 120, 120, 120])
    metrics_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#F1F5F9')),
        ('TEXTCOLOR', (0,0), (-1,0), colors.HexColor('#334155')),
        ('ALIGN', (0,0), (-1,-1), 'CENTER'),
        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
        ('BOTTOMPADDING', (0,0), (-1,-1), 8),
        ('TOPPADDING', (0,0), (-1,-1), 8),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#CBD5E1')),
    ]))
    story.append(metrics_table)
    story.append(Spacer(1, 20))

    # --- Detailed Task Classification Table ---
    story.append(Paragraph(f"<b>Day-Over-Day Task Breakdown ({employee_name})</b>", styles['Heading2']))
    story.append(Spacer(1, 8))

    table_data = [[
        Paragraph("Classification", header_cell_style),
        Paragraph("Assignee", header_cell_style),
        Paragraph("Task Description", header_cell_style),
        Paragraph("Yesterday", header_cell_style),
        Paragraph("Today", header_cell_style)
    ]]

    status_colors = {
        "Completed": "#16A34A",
        "Progressed": "#2563EB",
        "New": "#0891B2",
        "Stalled": "#D97706",
        "Regressed": "#DC2626",
        "Removed": "#6B7280"
    }

    if comparison_data:
        for item in comparison_data:
            label = safe_str(item.get('label'), "Unknown")
            color_hex = status_colors.get(label, '#1E293B')

            label_style = ParagraphStyle(
                'LabelStyle',
                parent=cell_style,
                fontName='Helvetica-Bold',
                textColor=colors.HexColor(color_hex)
            )

            task_title = safe_str(item.get('title'), "Untitled Task")
            y_prog = f"{item.get('yesterday_progress', 0)}%"
            t_prog = f"{item.get('today_progress', 0)}%"

            table_data.append([
                Paragraph(label, label_style),
                Paragraph(safe_str(employee_name), cell_style),
                Paragraph(task_title, cell_style),
                Paragraph(y_prog, cell_style),
                Paragraph(t_prog, cell_style)
            ])
    else:
        table_data.append([
            Paragraph("N/A", cell_style),
            Paragraph(safe_str(employee_name), cell_style),
            Paragraph("No active or historical task data found.", cell_style),
            Paragraph("0%", cell_style),
            Paragraph("0%", cell_style)
        ])

    task_table = Table(table_data, colWidths=[80, 90, 210, 50, 50])
    task_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#1E293B')),
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('TOPPADDING', (0,0), (-1,-1), 6),
        ('BOTTOMPADDING', (0,0), (-1,-1), 6),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#E2E8F0')),
    ]))

    story.append(task_table)

    doc = SimpleDocTemplate(
        pdf_path,
        pagesize=letter,
        rightMargin=40,
        leftMargin=40,
        topMargin=40,
        bottomMargin=40
    )
    doc.build(story)
    print(f"📄 Generated PDF report for [{employee_name}]: {pdf_path}")
    return pdf_path


def build_and_send_24h_pdf_report(target_employee=None):
    """
    Generates PDF reports per employee, saves each one into its own local
    folder (reports/<Employee_Name>/<Employee_Name>_report.pdf), and
    uploads them to their respective Google Drive folders:
    e.g., kelvin6k / Mohammad Hamdaan / Mohammad_Hamdaan_report.pdf

    If `target_employee` is provided (e.g. from a manual /report_now
    command), only that employee's report is generated and sent —
    everyone else's existing task history is left untouched.

    If `target_employee` is None (e.g. the 9 PM nightly job), reports
    are generated for every employee with recorded task activity, as
    intended for the full daily team report.
    """
    all_comparison_data = get_daily_comparison()

    # Group comparison tasks by assignee/employee name.
    # 'sender_name' is now populated correctly by compare_service.py.
    grouped_tasks = defaultdict(list)
    for task in all_comparison_data:
        emp_name = task.get('sender_name') or task.get('assignee') or task.get('employee_name') or "Unknown Employee"
        grouped_tasks[emp_name].append(task)

    if target_employee:
        # Case-insensitive match against whoever triggered the command.
        match_key = None
        for emp_name in grouped_tasks.keys():
            if emp_name.strip().lower() == target_employee.strip().lower():
                match_key = emp_name
                break

        if match_key:
            grouped_tasks = {match_key: grouped_tasks[match_key]}
        else:
            # No recorded tasks yet for this person today — still generate
            # a (mostly empty) report for them rather than doing nothing.
            grouped_tasks = {target_employee: []}

    # Ensure we only process if tasks actually exist
    if not grouped_tasks:
        print("⚠️ No tasks found for any employee. Skipping report generation.")
        return

    drive_mgr = DriveManager()

    for emp_name, emp_tasks in grouped_tasks.items():
        clean_name = emp_name.replace(" ", "_")

        # Create a dedicated local folder per employee: reports/<Employee_Name>/
        employee_folder = os.path.join(REPORTS_ROOT, clean_name)
        os.makedirs(employee_folder, exist_ok=True)

        pdf_file_path = os.path.join(employee_folder, f"{clean_name}_report.pdf")

        # 1. Generate specific PDF for this employee, saved into their folder
        generate_pdf_report(
            pdf_path=pdf_file_path,
            employee_name=emp_name,
            comparison_data=emp_tasks
        )

        # 2. Dispatch via Email
        try:
            send_email_with_pdf(pdf_file_path)
            print(f"✉️ PDF report for {emp_name} emailed successfully.")
        except Exception as e:
            print(f"⚠️ Email send failed for {emp_name}: {e}")

        # 3. Upload into Google Drive under kelvin6k / [emp_name] /
        try:
            drive_mgr.upload_employee_report(
                file_path=pdf_file_path,
                employee_name=emp_name,
            )
            print(f"Uploaded {pdf_file_path} to Drive under /{emp_name}/")
        except Exception as e:
            print(f"Google Drive upload failed for {emp_name}: {e}")


# ==========================================
# COMBINED "EVERYONE" REPORT (single PDF, sent to Ammar only)
# ==========================================
def generate_combined_pdf_report(pdf_path="daily_report_combined.pdf", grouped_tasks=None):
    """
    Builds ONE PDF containing every employee's Project Status Dashboard,
    formatted to match the reference screenshot exactly:
      - "PROJECT STATUS DASHBOARD" title
      - "Chat Group: company progress report | Target: Daily Comparison Analysis"
      - Metrics row: Overall Progress / Completed Tasks / Progressed-New / Stalled-Regressed
      - "Day-Over-Day Task Progress Breakdown" table: Classification | Task Description | Yesterday | Today
    One section per employee, stacked in a single file.
    """
    if grouped_tasks is None:
        grouped_tasks = {}

    styles = getSampleStyleSheet()

    title_style = ParagraphStyle(
        'DocTitle', parent=styles['Heading1'], fontSize=22, leading=26,
        textColor=colors.HexColor('#1E293B'), spaceAfter=8
    )
    meta_style = ParagraphStyle(
        'MetaText', parent=styles['Normal'], fontSize=10, leading=14,
        textColor=colors.HexColor('#475569')
    )
    employee_heading_style = ParagraphStyle(
        'EmployeeHeading', parent=styles['Heading2'], fontSize=14, leading=18,
        textColor=colors.HexColor('#1E293B'), spaceBefore=18, spaceAfter=6
    )
    section_heading_style = ParagraphStyle(
        'SectionHeading', parent=styles['Heading2'], fontSize=12, leading=16,
        textColor=colors.HexColor('#0F172A'), spaceBefore=10, spaceAfter=6
    )
    cell_style = ParagraphStyle(
        'CellText', parent=styles['Normal'], fontSize=9, leading=13,
        textColor=colors.HexColor('#1E293B')
    )
    header_cell_style = ParagraphStyle(
        'HeaderCellText', parent=styles['Normal'], fontSize=10, leading=12,
        textColor=colors.white, fontName='Helvetica-Bold'
    )

    status_colors = {
        "Completed": "#16A34A",
        "Progressed": "#2563EB",
        "New": "#0891B2",
        "Stalled": "#D97706",
        "Regressed": "#DC2626",
        "Removed": "#6B7280"
    }

    story = [
        Paragraph("PROJECT STATUS DASHBOARD", title_style),
        Paragraph(
            "<b>Chat Group:</b> company progress report | <b>Target:</b> Daily Comparison Analysis",
            meta_style
        ),
        Spacer(1, 15)
    ]

    if not grouped_tasks:
        story.append(Paragraph("No employee activity recorded for this period.", cell_style))

    employee_names = sorted(grouped_tasks.keys())

    for idx, emp_name in enumerate(employee_names):
        comparison_data = grouped_tasks[emp_name]

        if idx > 0:
            story.append(Spacer(1, 10))

        story.append(Paragraph(safe_str(emp_name), employee_heading_style))

        # --- Per-employee metrics row ---
        total_count = len(comparison_data)
        completed_count = sum(1 for t in comparison_data if t.get('label') == "Completed")
        progressed_count = sum(1 for t in comparison_data if t.get('label') in ["Progressed", "New"])
        stalled_count = sum(1 for t in comparison_data if t.get('label') in ["Stalled", "Regressed"])
        progress_pct = f"{int((completed_count / total_count) * 100)}%" if total_count > 0 else "0%"

        metrics_data = [
            ["Overall Progress", "Completed Tasks", "Progressed / New", "Stalled / Regressed"],
            [progress_pct, str(completed_count), str(progressed_count), str(stalled_count)]
        ]
        metrics_table = Table(metrics_data, colWidths=[120, 120, 120, 120])
        metrics_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#F1F5F9')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.HexColor('#334155')),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
            ('TOPPADDING', (0, 0), (-1, -1), 8),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#CBD5E1')),
        ]))
        story.append(metrics_table)
        story.append(Spacer(1, 12))

        # --- Day-Over-Day Task Progress Breakdown table ---
        story.append(Paragraph("Day-Over-Day Task Progress Breakdown", section_heading_style))

        table_data = [[
            Paragraph("Classification", header_cell_style),
            Paragraph("Task Description", header_cell_style),
            Paragraph("Yesterday", header_cell_style),
            Paragraph("Today", header_cell_style)
        ]]

        if comparison_data:
            for item in comparison_data:
                label = safe_str(item.get('label'), "Unknown")
                color_hex = status_colors.get(label, '#1E293B')
                label_style = ParagraphStyle(
                    'LabelStyle', parent=cell_style, fontName='Helvetica-Bold',
                    textColor=colors.HexColor(color_hex)
                )
                task_title = safe_str(item.get('title'), "Untitled Task")
                y_prog = f"{item.get('yesterday_progress', 0)}%"
                t_prog = f"{item.get('today_progress', 0)}%"
                table_data.append([
                    Paragraph(label, label_style),
                    Paragraph(task_title, cell_style),
                    Paragraph(y_prog, cell_style),
                    Paragraph(t_prog, cell_style)
                ])
        else:
            table_data.append([
                Paragraph("N/A", cell_style),
                Paragraph("No active or historical task data found.", cell_style),
                Paragraph("0%", cell_style),
                Paragraph("0%", cell_style)
            ])

        task_table = Table(table_data, colWidths=[90, 300, 55, 55])
        task_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1E293B')),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('TOPPADDING', (0, 0), (-1, -1), 6),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#E2E8F0')),
        ]))
        story.append(task_table)

    doc = SimpleDocTemplate(
        pdf_path, pagesize=letter,
        rightMargin=40, leftMargin=40, topMargin=40, bottomMargin=40
    )
    doc.build(story)
    print(f"📄 Generated combined PDF report for everyone: {pdf_path}")
    return pdf_path


def build_and_send_combined_daily_report(recipient_email=None):
    """
    Generates ONE combined PDF covering every employee's daily task
    comparison (same visual format as the individual reports) and emails
    it only to `recipient_email` (Ammar). Intended to run once a day at
    9:00 AM via the scheduler in run_automation.py.
    """
    if recipient_email is None:
        cfg = config.load()
        recipient_email = cfg.get("REPORT_RECIPIENT_EMAIL") or cfg.get("GMAIL_USER")

    all_comparison_data = get_daily_comparison()

    grouped_tasks = defaultdict(list)
    for task in all_comparison_data:
        emp_name = task.get('sender_name') or task.get('assignee') or task.get('employee_name') or "Unknown Employee"
        grouped_tasks[emp_name].append(task)

    os.makedirs(REPORTS_ROOT, exist_ok=True)
    today_str = datetime.now().strftime("%Y-%m-%d")
    pdf_path = os.path.join(REPORTS_ROOT, f"Team_Daily_Report_{today_str}.pdf")

    generate_combined_pdf_report(pdf_path=pdf_path, grouped_tasks=grouped_tasks)

    try:
        send_email_with_pdf(pdf_path, recipient_email=recipient_email)
        print(f"✉️ Combined team report emailed to {recipient_email}.")
    except Exception as e:
        print(f"⚠️ Email send failed for combined report: {e}")

    return pdf_path


# Backward Compatibility Aliases
generate_and_send_daily_pdf = build_and_send_24h_pdf_report

if __name__ == "__main__":
    build_and_send_combined_daily_report()