"""Service for generating clinical audit reports in PDF format."""

import io
from datetime import datetime
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
import logging

logger = logging.getLogger(__name__)

def generate_audit_report(session_id: str, state: dict) -> bytes:
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter,
                            rightMargin=50, leftMargin=50,
                            topMargin=50, bottomMargin=50)
    
    styles = getSampleStyleSheet()
    title_style = styles['Title']
    heading_style = styles['Heading2']
    normal_style = styles['Normal']
    
    Story = []
    
    # Header
    Story.append(Paragraph("Nova Guard Clinical Audit Report", title_style))
    Story.append(Spacer(1, 12))
    
    Story.append(Paragraph(f"<b>Session ID:</b> {session_id}", normal_style))
    Story.append(Paragraph(f"<b>Generated At:</b> {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC", normal_style))
    Story.append(Spacer(1, 20))
    
    # 1. Patient Profile
    profile = state.get("patient_profile")
    if profile:
        Story.append(Paragraph("Patient Profile (De-Identified)", heading_style))
        Story.append(Paragraph(f"<b>ID:</b> {profile.get('name', 'Unknown')}", normal_style))
        Story.append(Paragraph(f"<b>Age:</b> {profile.get('age_years', 'N/A')} | <b>Weight:</b> {profile.get('weight', 'N/A')} kg | <b>eGFR:</b> {profile.get('egfr', 'N/A')}", normal_style))
        
        # Medical Conditions
        conditions = [c.get("condition") for c in profile.get("medical_conditions", [])]
        if conditions:
            Story.append(Paragraph(f"<b>Conditions:</b> {', '.join(conditions)}", normal_style))
            
        Story.append(Spacer(1, 12))
        
    # 2. Prescriptions
    prescriptions = state.get("prescriptions", [])
    if prescriptions:
        Story.append(Paragraph("Analyzed Prescriptions", heading_style))
        for rx in prescriptions:
            # handle case where rx is a dict or a Pydantic model
            drug = getattr(rx, 'drug_name', None) or (rx.get('drug_name', 'Unknown') if isinstance(rx, dict) else 'Unknown')
            dose = getattr(rx, 'dose', None) or (rx.get('dose', 'Unknown') if isinstance(rx, dict) else 'Unknown')
            freq = getattr(rx, 'frequency', None) or (rx.get('frequency', 'Unknown') if isinstance(rx, dict) else 'Unknown')
            Story.append(Paragraph(f"• <b>{drug}</b> {dose} {freq}", normal_style))
        Story.append(Spacer(1, 12))
        
    # 3. Verdict
    verdict = state.get("verdict")
    if verdict:
        status = getattr(verdict, 'status', None) or (verdict.get('status', 'Unknown') if isinstance(verdict, dict) else 'Unknown')
        reasoning = getattr(verdict, 'reasoning', None) or (verdict.get('reasoning', '') if isinstance(verdict, dict) else '')
        
        Story.append(Paragraph("Clinical Verdict", heading_style))
        
        color_hex = "#ef4444" if status == "red" else ("#eab308" if status == "yellow" else "#22c55e")
        
        Story.append(Paragraph(f"<font color='{color_hex}'><b>STATUS: {status.upper()}</b></font>", normal_style))
        Story.append(Paragraph(f"<b>Reasoning:</b> {reasoning}", normal_style))
        Story.append(Spacer(1, 12))
        
    # 4. Safety Flags
    flags = state.get("safety_flags", [])
    if flags:
        Story.append(Paragraph("Safety Flags", heading_style))
        
        data = [["Severity", "Category", "Message"]]
        for f in flags:
            sev = getattr(f, 'severity', None) or (f.get('severity', '') if isinstance(f, dict) else '')
            cat = getattr(f, 'category', None) or (f.get('category', '') if isinstance(f, dict) else '')
            msg = getattr(f, 'message', None) or (f.get('message', '') if isinstance(f, dict) else '')
            
            # Use Paragraph for message to allow text wrapping inside the table cell
            p_msg = Paragraph(msg.replace("**", ""), normal_style)
            data.append([sev.upper(), cat.replace("_", " ").title(), p_msg])
            
        t = Table(data, colWidths=[60, 100, 340])
        t.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,0), colors.HexColor("#1e293b")),
            ('TEXTCOLOR', (0,0), (-1,0), colors.whitesmoke),
            ('ALIGN', (0,0), (-1,-1), 'LEFT'),
            ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
            ('FONTSIZE', (0,0), (-1,0), 10),
            ('BOTTOMPADDING', (0,0), (-1,0), 8),
            ('TOPPADDING', (0,0), (-1,0), 8),
            ('BACKGROUND', (0,1), (-1,-1), colors.white),
            ('GRID', (0,0), (-1,-1), 1, colors.HexColor("#e2e8f0")),
            ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ]))
        Story.append(t)
    else:
        Story.append(Paragraph("No safety flags triggered.", normal_style))
        
    doc.build(Story)
    return buffer.getvalue()
