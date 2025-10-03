from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
from reportlab.lib.enums import TA_CENTER, TA_RIGHT, TA_LEFT
from datetime import datetime
from typing import Dict, List
import os

class ReportGenerator:
    """Generate F500-level PDF reports"""
    
    @staticmethod
    def generate_executive_summary(
        deal_data: Dict,
        underwriting_result: Dict,
        output_path: str,
        logo_path: str = None
    ) -> str:
        """Generate Executive Summary PDF"""
        
        doc = SimpleDocTemplate(output_path, pagesize=letter,
                              rightMargin=0.75*inch, leftMargin=0.75*inch,
                              topMargin=0.75*inch, bottomMargin=0.75*inch)
        
        story = []
        styles = getSampleStyleSheet()
        
        # Custom styles
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=24,
            textColor=colors.HexColor('#0A3D91'),
            spaceAfter=30,
            alignment=TA_CENTER
        )
        
        heading_style = ParagraphStyle(
            'CustomHeading',
            parent=styles['Heading2'],
            fontSize=14,
            textColor=colors.HexColor('#0A3D91'),
            spaceAfter=12,
            spaceBefore=12
        )
        
        # Title
        story.append(Paragraph("EXECUTIVE SUMMARY", title_style))
        story.append(Paragraph(f"Commercial Loan Underwriting Analysis", styles['Normal']))
        story.append(Spacer(1, 0.3*inch))
        
        # Deal Information
        story.append(Paragraph("Deal Information", heading_style))
        deal_info = [
            ["Borrower:", deal_data.get('borrower_name', 'N/A')],
            ["Deal Type:", deal_data.get('deal_type', 'N/A').upper()],
            ["Loan Amount:", f"${deal_data.get('loan_amount', 0):,.2f}"],
            ["Appraised Value:", f"${deal_data.get('appraised_value', 0):,.2f}"],
            ["Interest Rate:", f"{deal_data.get('interest_rate', 0)*100:.3f}%"],
            ["Amortization:", f"{deal_data.get('amortization_months', 0)} months"],
            ["Date:", datetime.now().strftime("%B %d, %Y")]
        ]
        
        deal_table = Table(deal_info, colWidths=[2*inch, 4*inch])
        deal_table.setStyle(TableStyle([
            ('FONT', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONT', (1, 0), (1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ]))
        story.append(deal_table)
        story.append(Spacer(1, 0.3*inch))
        
        # Underwriting Metrics
        story.append(Paragraph("Key Underwriting Metrics", heading_style))
        
        dscr = underwriting_result.get('dscr_base', 0)
        ltv = underwriting_result.get('ltv', 0)
        
        # Color code based on thresholds
        dscr_color = colors.green if dscr >= 1.5 else (colors.orange if dscr >= 1.2 else colors.red)
        ltv_color = colors.green if ltv <= 0.70 else (colors.orange if ltv <= 0.80 else colors.red)
        
        metrics = [
            ["Metric", "Value", "Status"],
            ["DSCR (Base)", f"{dscr:.2f}x", "Strong" if dscr >= 1.5 else ("Acceptable" if dscr >= 1.2 else "Weak")],
            ["LTV", f"{ltv:.1%}", "Conservative" if ltv <= 0.70 else ("Acceptable" if ltv <= 0.80 else "Exception")],
            ["Global Cash Flow", f"${underwriting_result.get('global_cash_flow', 0):,.2f}", ""],
            ["Annual Debt Service", f"${underwriting_result.get('annual_debt_service', 0):,.2f}", ""],
            ["Monthly Payment", f"${underwriting_result.get('monthly_payment', 0):,.2f}", ""]
        ]
        
        metrics_table = Table(metrics, colWidths=[2.5*inch, 1.5*inch, 2*inch])
        metrics_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#0A3D91')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 11),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.grey),
            ('FONTSIZE', (0, 1), (-1, -1), 10),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#F5F5F5')])
        ]))
        story.append(metrics_table)
        story.append(Spacer(1, 0.3*inch))
        
        # Recommendation
        story.append(Paragraph("Recommendation", heading_style))
        recommendation = underwriting_result.get('recommendation', 'N/A')
        rec_style = ParagraphStyle('Recommendation', parent=styles['Normal'], fontSize=12, 
                                   textColor=colors.HexColor('#0A3D91'), fontName='Helvetica-Bold')
        story.append(Paragraph(recommendation, rec_style))
        story.append(Spacer(1, 0.2*inch))
        
        # Strengths
        strengths = underwriting_result.get('strengths', [])
        if strengths:
            story.append(Paragraph("Strengths", heading_style))
            for strength in strengths:
                story.append(Paragraph(f"• {strength}", styles['Normal']))
            story.append(Spacer(1, 0.2*inch))
        
        # Risks
        risks = underwriting_result.get('risks', [])
        if risks:
            story.append(Paragraph("Risks", heading_style))
            for risk in risks:
                story.append(Paragraph(f"• {risk}", styles['Normal']))
            story.append(Spacer(1, 0.2*inch))
        
        # Mitigants
        mitigants = underwriting_result.get('mitigants', [])
        if mitigants:
            story.append(Paragraph("Recommended Mitigants", heading_style))
            for mitigant in mitigants:
                story.append(Paragraph(f"• {mitigant}", styles['Normal']))
        
        # Build PDF
        doc.build(story)
        return output_path
    
    @staticmethod
    def generate_credit_memo(
        deal_data: Dict,
        underwriting_result: Dict,
        financial_data: Dict,
        output_path: str,
        logo_path: str = None
    ) -> str:
        """Generate comprehensive Credit Memo PDF"""
        
        doc = SimpleDocTemplate(output_path, pagesize=letter,
                              rightMargin=0.75*inch, leftMargin=0.75*inch,
                              topMargin=0.75*inch, bottomMargin=0.75*inch)
        
        story = []
        styles = getSampleStyleSheet()
        
        # Custom styles
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=20,
            textColor=colors.HexColor('#0A3D91'),
            spaceAfter=20,
            alignment=TA_CENTER
        )
        
        heading_style = ParagraphStyle(
            'CustomHeading',
            parent=styles['Heading2'],
            fontSize=13,
            textColor=colors.HexColor('#0A3D91'),
            spaceAfter=10,
            spaceBefore=15
        )
        
        # Title Page
        story.append(Paragraph("CREDIT MEMORANDUM", title_style))
        story.append(Spacer(1, 0.5*inch))
        story.append(Paragraph(f"Borrower: {deal_data.get('borrower_name', 'N/A')}", styles['Normal']))
        story.append(Paragraph(f"Loan Amount: ${deal_data.get('loan_amount', 0):,.2f}", styles['Normal']))
        story.append(Paragraph(f"Date: {datetime.now().strftime('%B %d, %Y')}", styles['Normal']))
        story.append(PageBreak())
        
        # Executive Summary Section
        story.append(Paragraph("I. EXECUTIVE SUMMARY", heading_style))
        recommendation = underwriting_result.get('recommendation', 'N/A')
        story.append(Paragraph(f"<b>Recommendation:</b> {recommendation}", styles['Normal']))
        story.append(Spacer(1, 0.1*inch))
        
        summary_text = f"""
        This credit memorandum presents the underwriting analysis for a {deal_data.get('deal_type', 'N/A')} 
        transaction for {deal_data.get('borrower_name', 'N/A')}. The proposed loan amount of 
        ${deal_data.get('loan_amount', 0):,.2f} represents an LTV of {underwriting_result.get('ltv', 0):.1%} 
        based on an appraised value of ${deal_data.get('appraised_value', 0):,.2f}. 
        The global debt service coverage ratio is {underwriting_result.get('dscr_base', 0):.2f}x.
        """
        story.append(Paragraph(summary_text, styles['Normal']))
        story.append(Spacer(1, 0.2*inch))
        
        # Transaction Structure
        story.append(Paragraph("II. TRANSACTION STRUCTURE", heading_style))
        structure_data = [
            ["Loan Amount:", f"${deal_data.get('loan_amount', 0):,.2f}"],
            ["Interest Rate:", f"{deal_data.get('interest_rate', 0)*100:.3f}%"],
            ["Amortization:", f"{deal_data.get('amortization_months', 0)} months ({deal_data.get('amortization_months', 0)//12} years)"],
            ["Balloon:", f"{deal_data.get('balloon_months', 0)} months" if deal_data.get('balloon_months') else "Fully Amortizing"],
            ["Monthly Payment:", f"${underwriting_result.get('monthly_payment', 0):,.2f}"],
            ["Annual Debt Service:", f"${underwriting_result.get('annual_debt_service', 0):,.2f}"]
        ]
        
        structure_table = Table(structure_data, colWidths=[2.5*inch, 3.5*inch])
        structure_table.setStyle(TableStyle([
            ('FONT', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ]))
        story.append(structure_table)
        story.append(Spacer(1, 0.2*inch))
        
        # Financial Analysis
        story.append(Paragraph("III. FINANCIAL ANALYSIS", heading_style))
        
        story.append(Paragraph("<b>A. Cash Flow Analysis</b>", styles['Normal']))
        story.append(Spacer(1, 0.1*inch))
        
        cf_data = [
            ["Component", "Amount"],
            ["Business Net Income", f"${financial_data.get('business_net_income', 0):,.2f}"],
            ["Add: Depreciation", f"${financial_data.get('depreciation', 0):,.2f}"],
            ["Add: Amortization", f"${financial_data.get('amortization', 0):,.2f}"],
            ["Business Cash Flow", f"${underwriting_result.get('business_cash_flow', 0):,.2f}"],
            ["Personal Income", f"${underwriting_result.get('personal_income', 0):,.2f}"],
            ["Global Cash Flow", f"${underwriting_result.get('global_cash_flow', 0):,.2f}"]
        ]
        
        cf_table = Table(cf_data, colWidths=[3*inch, 2*inch])
        cf_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#0A3D91')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('GRID', (0, 0), (-1, -1), 1, colors.grey),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#F5F5F5')]),
            ('LINEABOVE', (0, -2), (-1, -2), 2, colors.black),
            ('FONT', (0, -1), (-1, -1), 'Helvetica-Bold')
        ]))
        story.append(cf_table)
        story.append(Spacer(1, 0.2*inch))
        
        # Underwriting Metrics
        story.append(Paragraph("<b>B. Underwriting Metrics</b>", styles['Normal']))
        story.append(Spacer(1, 0.1*inch))
        
        dscr_text = f"""
        <b>Debt Service Coverage Ratio (DSCR):</b> {underwriting_result.get('dscr_base', 0):.2f}x<br/>
        Calculation: ${underwriting_result.get('global_cash_flow', 0):,.2f} / ${underwriting_result.get('annual_debt_service', 0):,.2f} = {underwriting_result.get('dscr_base', 0):.2f}x
        """
        story.append(Paragraph(dscr_text, styles['Normal']))
        story.append(Spacer(1, 0.1*inch))
        
        ltv_text = f"""
        <b>Loan-to-Value (LTV):</b> {underwriting_result.get('ltv', 0):.1%}<br/>
        Calculation: ${deal_data.get('loan_amount', 0):,.2f} / ${deal_data.get('appraised_value', 0):,.2f} = {underwriting_result.get('ltv', 0):.1%}
        """
        story.append(Paragraph(ltv_text, styles['Normal']))
        story.append(Spacer(1, 0.3*inch))
        
        # Strengths, Weaknesses, Mitigants
        story.append(Paragraph("IV. CREDIT ASSESSMENT", heading_style))
        
        strengths = underwriting_result.get('strengths', [])
        if strengths:
            story.append(Paragraph("<b>Strengths:</b>", styles['Normal']))
            for i, strength in enumerate(strengths, 1):
                story.append(Paragraph(f"{i}. {strength}", styles['Normal']))
            story.append(Spacer(1, 0.1*inch))
        
        risks = underwriting_result.get('risks', [])
        if risks:
            story.append(Paragraph("<b>Risks:</b>", styles['Normal']))
            for i, risk in enumerate(risks, 1):
                story.append(Paragraph(f"{i}. {risk}", styles['Normal']))
            story.append(Spacer(1, 0.1*inch))
        
        mitigants = underwriting_result.get('mitigants', [])
        if mitigants:
            story.append(Paragraph("<b>Recommended Mitigants:</b>", styles['Normal']))
            for i, mitigant in enumerate(mitigants, 1):
                story.append(Paragraph(f"{i}. {mitigant}", styles['Normal']))
        
        story.append(Spacer(1, 0.3*inch))
        
        # Recommendation
        story.append(Paragraph("V. RECOMMENDATION", heading_style))
        story.append(Paragraph(recommendation, styles['Normal']))
        
        # Build PDF
        doc.build(story)
        return output_path
    
    @staticmethod
    def generate_stip_sheet(
        deal_data: Dict,
        output_path: str
    ) -> str:
        """Generate Stipulation Sheet (document checklist)"""
        
        doc = SimpleDocTemplate(output_path, pagesize=letter,
                              rightMargin=0.75*inch, leftMargin=0.75*inch,
                              topMargin=0.75*inch, bottomMargin=0.75*inch)
        
        story = []
        styles = getSampleStyleSheet()
        
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=18,
            textColor=colors.HexColor('#0A3D91'),
            spaceAfter=20,
            alignment=TA_CENTER
        )
        
        story.append(Paragraph("LOAN STIPULATION SHEET", title_style))
        story.append(Paragraph(f"Borrower: {deal_data.get('borrower_name', 'N/A')}", styles['Normal']))
        story.append(Paragraph(f"Date: {datetime.now().strftime('%B %d, %Y')}", styles['Normal']))
        story.append(Spacer(1, 0.3*inch))
        
        # Required Documents
        stips = [
            ["Status", "Required Document", "Notes"],
            ["☐", "Business Tax Returns (3 years)", "1120/1120S/1065 with all schedules"],
            ["☐", "Personal Tax Returns (3 years)", "1040 with all schedules"],
            ["☐", "YTD Profit & Loss Statement", "Current year through most recent month"],
            ["☐", "YTD Balance Sheet", "Current year through most recent month"],
            ["☐", "Business Bank Statements (3 months)", "All business accounts"],
            ["☐", "Personal Bank Statements (3 months)", "All personal accounts"],
            ["☐", "Personal Financial Statement", "Signed and dated"],
            ["☐", "Purchase Agreement", "Fully executed (if purchase)"],
            ["☐", "Appraisal", "Completed by approved appraiser"],
            ["☐", "Property Insurance", "Proof of coverage"],
            ["☐", "Articles of Organization", "LLC/Corp formation documents"],
            ["☐", "Operating Agreement", "Current and signed"],
            ["☐", "Business License", "Current and valid"],
            ["☐", "Credit Authorization", "Signed by all guarantors"]
        ]
        
        stip_table = Table(stips, colWidths=[0.5*inch, 3*inch, 3*inch])
        stip_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#0A3D91')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (0, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('GRID', (0, 0), (-1, -1), 1, colors.grey),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#F5F5F5')]),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 10)
        ]))
        story.append(stip_table)
        
        # Build PDF
        doc.build(story)
        return output_path
