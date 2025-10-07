"""
Enterprise PDF Report Generation System
Bank-Quality Credit Memos and Executive Summaries for Commercial Lending
"""
from typing import Dict, List, Optional
from decimal import Decimal
from datetime import datetime
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import (
    SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer,
    PageBreak, Image, KeepTogether
)
from reportlab.lib.enums import TA_CENTER, TA_RIGHT, TA_LEFT, TA_JUSTIFY
from reportlab.pdfgen import canvas
import io


class ReportGeneratorPro:
    """
    Enterprise-grade PDF report generation
    Produces bank-quality credit memos and executive summaries
    """
    
    def __init__(self):
        self.styles = getSampleStyleSheet()
        self._setup_custom_styles()
    
    def _setup_custom_styles(self):
        """Setup custom paragraph styles"""
        # Title style
        self.styles.add(ParagraphStyle(
            name='CustomTitle',
            parent=self.styles['Heading1'],
            fontSize=24,
            textColor=colors.HexColor('#1a1a1a'),
            spaceAfter=30,
            alignment=TA_CENTER,
            fontName='Helvetica-Bold'
        ))
        
        # Subtitle style
        self.styles.add(ParagraphStyle(
            name='CustomSubtitle',
            parent=self.styles['Heading2'],
            fontSize=16,
            textColor=colors.HexColor('#2c3e50'),
            spaceAfter=12,
            spaceBefore=12,
            fontName='Helvetica-Bold'
        ))
        
        # Section header style
        self.styles.add(ParagraphStyle(
            name='SectionHeader',
            parent=self.styles['Heading3'],
            fontSize=14,
            textColor=colors.HexColor('#34495e'),
            spaceAfter=10,
            spaceBefore=15,
            fontName='Helvetica-Bold',
            borderWidth=0,
            borderPadding=5,
            borderColor=colors.HexColor('#3498db'),
            borderRadius=None,
            backColor=colors.HexColor('#ecf0f1')
        ))
        
        # Body text style
        self.styles.add(ParagraphStyle(
            name='CustomBody',
            parent=self.styles['BodyText'],
            fontSize=11,
            textColor=colors.HexColor('#2c3e50'),
            alignment=TA_JUSTIFY,
            spaceAfter=8,
            leading=14
        ))
        
        # Recommendation style
        self.styles.add(ParagraphStyle(
            name='Recommendation',
            parent=self.styles['BodyText'],
            fontSize=13,
            textColor=colors.white,
            alignment=TA_CENTER,
            spaceAfter=15,
            spaceBefore=15,
            fontName='Helvetica-Bold'
        ))
    
    def generate_credit_memo(
        self,
        loan_data: Dict,
        borrower_data: Dict,
        property_data: Optional[Dict],
        underwriting_results: Dict,
        financial_analysis: Dict,
        output_path: str
    ) -> str:
        """
        Generate comprehensive credit memo PDF
        
        Args:
            loan_data: Loan request details
            borrower_data: Borrower information
            property_data: Property details (if applicable)
            underwriting_results: Underwriting analysis results
            financial_analysis: Financial statement analysis
            output_path: Path to save PDF
            
        Returns:
            Path to generated PDF
        """
        # Create PDF document
        doc = SimpleDocTemplate(
            output_path,
            pagesize=letter,
            rightMargin=0.75*inch,
            leftMargin=0.75*inch,
            topMargin=1*inch,
            bottomMargin=0.75*inch
        )
        
        # Build document content
        story = []
        
        # Add header
        story.extend(self._build_header(loan_data, borrower_data))
        
        # Add executive summary
        story.extend(self._build_executive_summary(
            loan_data, underwriting_results
        ))
        
        story.append(PageBreak())
        
        # Add borrower profile
        story.extend(self._build_borrower_profile(borrower_data))
        
        # Add loan request details
        story.extend(self._build_loan_details(loan_data))
        
        # Add property information (if applicable)
        if property_data:
            story.extend(self._build_property_section(property_data))
        
        story.append(PageBreak())
        
        # Add financial analysis
        story.extend(self._build_financial_analysis(financial_analysis))
        
        # Add underwriting analysis
        story.extend(self._build_underwriting_analysis(underwriting_results))
        
        story.append(PageBreak())
        
        # Add risk assessment
        story.extend(self._build_risk_assessment(underwriting_results))
        
        # Add recommendation
        story.extend(self._build_recommendation(underwriting_results))
        
        # Add conditions and requirements
        if underwriting_results.get('required_conditions'):
            story.extend(self._build_conditions(underwriting_results))
        
        # Add appendix
        story.append(PageBreak())
        story.extend(self._build_appendix(underwriting_results))
        
        # Build PDF
        doc.build(story, onFirstPage=self._add_page_number, onLaterPages=self._add_page_number)
        
        return output_path
    
    def generate_executive_summary(
        self,
        loan_data: Dict,
        borrower_data: Dict,
        underwriting_results: Dict,
        output_path: str
    ) -> str:
        """
        Generate concise executive summary PDF (1-2 pages)
        
        Args:
            loan_data: Loan request details
            borrower_data: Borrower information
            underwriting_results: Underwriting results
            output_path: Path to save PDF
            
        Returns:
            Path to generated PDF
        """
        doc = SimpleDocTemplate(
            output_path,
            pagesize=letter,
            rightMargin=0.75*inch,
            leftMargin=0.75*inch,
            topMargin=1*inch,
            bottomMargin=0.75*inch
        )
        
        story = []
        
        # Header
        story.append(Paragraph("EXECUTIVE SUMMARY", self.styles['CustomTitle']))
        story.append(Spacer(1, 0.2*inch))
        
        # Key details table
        story.extend(self._build_summary_table(loan_data, borrower_data, underwriting_results))
        
        # Recommendation box
        story.extend(self._build_recommendation(underwriting_results))
        
        # Key metrics
        story.extend(self._build_key_metrics_summary(underwriting_results))
        
        # Strengths and concerns
        story.extend(self._build_strengths_concerns_summary(underwriting_results))
        
        doc.build(story, onFirstPage=self._add_page_number, onLaterPages=self._add_page_number)
        
        return output_path
    
    def _build_header(self, loan_data: Dict, borrower_data: Dict) -> List:
        """Build document header"""
        elements = []
        
        # Title
        elements.append(Paragraph("COMMERCIAL LOAN CREDIT MEMO", self.styles['CustomTitle']))
        elements.append(Spacer(1, 0.1*inch))
        
        # Subtitle with borrower and date
        subtitle = f"{borrower_data.get('name', 'N/A')} | {datetime.now().strftime('%B %d, %Y')}"
        elements.append(Paragraph(subtitle, self.styles['CustomSubtitle']))
        elements.append(Spacer(1, 0.3*inch))
        
        # Horizontal line
        elements.append(Spacer(1, 0.1*inch))
        
        return elements
    
    def _build_executive_summary(self, loan_data: Dict, underwriting_results: Dict) -> List:
        """Build executive summary section"""
        elements = []
        
        elements.append(Paragraph("EXECUTIVE SUMMARY", self.styles['SectionHeader']))
        elements.append(Spacer(1, 0.1*inch))
        
        # Summary text
        loan_amount = loan_data.get('loan_amount', 0)
        loan_type = loan_data.get('loan_type', 'commercial loan').replace('_', ' ').title()
        recommendation = underwriting_results.get('recommendation', 'PENDING')
        dscr = underwriting_results.get('dscr', 0)
        ltv = underwriting_results.get('ltv', 0)
        
        summary_text = f"""
        This credit memo presents the underwriting analysis for a ${loan_amount:,.2f} {loan_type} request. 
        The analysis includes comprehensive financial review, risk assessment, and debt service coverage evaluation. 
        Based on the underwriting analysis, the recommendation is to <b>{recommendation}</b> this loan request.
        <br/><br/>
        Key metrics include a Debt Service Coverage Ratio (DSCR) of {dscr:.2f}x and Loan-to-Value (LTV) ratio of {ltv:.1%}. 
        The detailed analysis and supporting documentation are provided in the sections that follow.
        """
        
        elements.append(Paragraph(summary_text, self.styles['CustomBody']))
        elements.append(Spacer(1, 0.2*inch))
        
        return elements
    
    def _build_borrower_profile(self, borrower_data: Dict) -> List:
        """Build borrower profile section"""
        elements = []
        
        elements.append(Paragraph("BORROWER PROFILE", self.styles['SectionHeader']))
        elements.append(Spacer(1, 0.1*inch))
        
        # Borrower details table
        data = [
            ['Borrower Name:', borrower_data.get('name', 'N/A')],
            ['Entity Type:', borrower_data.get('entity_type', 'N/A').upper()],
            ['Industry:', borrower_data.get('industry', 'N/A')],
            ['Years in Business:', str(borrower_data.get('years_in_business', 'N/A'))],
            ['Credit Score:', str(borrower_data.get('credit_score', 'N/A'))],
            ['Annual Revenue:', f"${borrower_data.get('annual_revenue', 0):,.2f}"],
        ]
        
        table = Table(data, colWidths=[2*inch, 4*inch])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#ecf0f1')),
            ('TEXTCOLOR', (0, 0), (-1, -1), colors.HexColor('#2c3e50')),
            ('ALIGN', (0, 0), (0, -1), 'RIGHT'),
            ('ALIGN', (1, 0), (1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTNAME', (1, 0), (1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
            ('TOPPADDING', (0, 0), (-1, -1), 8),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ]))
        
        elements.append(table)
        elements.append(Spacer(1, 0.2*inch))
        
        return elements
    
    def _build_loan_details(self, loan_data: Dict) -> List:
        """Build loan details section"""
        elements = []
        
        elements.append(Paragraph("LOAN REQUEST DETAILS", self.styles['SectionHeader']))
        elements.append(Spacer(1, 0.1*inch))
        
        data = [
            ['Loan Amount:', f"${loan_data.get('loan_amount', 0):,.2f}"],
            ['Loan Type:', loan_data.get('loan_type', 'N/A').replace('_', ' ').title()],
            ['Loan Purpose:', loan_data.get('loan_purpose', 'N/A')],
            ['Interest Rate:', f"{loan_data.get('interest_rate', 0):.3%}"],
            ['Term:', f"{loan_data.get('term_months', 0)} months"],
            ['Amortization:', f"{loan_data.get('amortization_months', 0)} months"],
        ]
        
        table = Table(data, colWidths=[2*inch, 4*inch])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#ecf0f1')),
            ('TEXTCOLOR', (0, 0), (-1, -1), colors.HexColor('#2c3e50')),
            ('ALIGN', (0, 0), (0, -1), 'RIGHT'),
            ('ALIGN', (1, 0), (1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTNAME', (1, 0), (1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
            ('TOPPADDING', (0, 0), (-1, -1), 8),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ]))
        
        elements.append(table)
        elements.append(Spacer(1, 0.2*inch))
        
        return elements
    
    def _build_property_section(self, property_data: Dict) -> List:
        """Build property information section"""
        elements = []
        
        elements.append(Paragraph("PROPERTY INFORMATION", self.styles['SectionHeader']))
        elements.append(Spacer(1, 0.1*inch))
        
        data = [
            ['Property Type:', property_data.get('property_type', 'N/A').title()],
            ['Address:', property_data.get('address', 'N/A')],
            ['Appraised Value:', f"${property_data.get('appraised_value', 0):,.2f}"],
            ['Square Footage:', f"{property_data.get('square_footage', 0):,} sq ft"],
            ['Year Built:', str(property_data.get('year_built', 'N/A'))],
            ['Occupancy Rate:', f"{property_data.get('occupancy_rate', 0):.1%}"],
        ]
        
        table = Table(data, colWidths=[2*inch, 4*inch])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#ecf0f1')),
            ('TEXTCOLOR', (0, 0), (-1, -1), colors.HexColor('#2c3e50')),
            ('ALIGN', (0, 0), (0, -1), 'RIGHT'),
            ('ALIGN', (1, 0), (1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTNAME', (1, 0), (1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
            ('TOPPADDING', (0, 0), (-1, -1), 8),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ]))
        
        elements.append(table)
        elements.append(Spacer(1, 0.2*inch))
        
        return elements
    
    def _build_financial_analysis(self, financial_analysis: Dict) -> List:
        """Build financial analysis section"""
        elements = []
        
        elements.append(Paragraph("FINANCIAL ANALYSIS", self.styles['SectionHeader']))
        elements.append(Spacer(1, 0.1*inch))
        
        # Financial metrics table
        data = [
            ['Metric', 'Value', 'Industry Benchmark', 'Assessment'],
            ['Current Ratio', 
             f"{financial_analysis.get('current_ratio', 0):.2f}",
             '> 1.5',
             self._assess_metric(financial_analysis.get('current_ratio', 0), 1.5, 'higher')],
            ['Debt-to-Equity',
             f"{financial_analysis.get('debt_to_equity', 0):.2f}",
             '< 2.0',
             self._assess_metric(financial_analysis.get('debt_to_equity', 0), 2.0, 'lower')],
            ['Profit Margin',
             f"{financial_analysis.get('profit_margin', 0):.1%}",
             '> 10%',
             self._assess_metric(financial_analysis.get('profit_margin', 0), 0.10, 'higher')],
            ['ROE',
             f"{financial_analysis.get('roe', 0):.1%}",
             '> 15%',
             self._assess_metric(financial_analysis.get('roe', 0), 0.15, 'higher')],
        ]
        
        table = Table(data, colWidths=[2*inch, 1.2*inch, 1.5*inch, 1.3*inch])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#3498db')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 11),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 10),
            ('TOPPADDING', (0, 0), (-1, 0), 10),
            ('BACKGROUND', (0, 1), (-1, -1), colors.white),
            ('TEXTCOLOR', (0, 1), (-1, -1), colors.HexColor('#2c3e50')),
            ('FONTNAME', (0, 1), (0, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 1), (-1, -1), 10),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f8f9fa')]),
        ]))
        
        elements.append(table)
        elements.append(Spacer(1, 0.2*inch))
        
        return elements
    
    def _build_underwriting_analysis(self, underwriting_results: Dict) -> List:
        """Build underwriting analysis section"""
        elements = []
        
        elements.append(Paragraph("UNDERWRITING ANALYSIS", self.styles['SectionHeader']))
        elements.append(Spacer(1, 0.1*inch))
        
        # Key underwriting metrics
        data = [
            ['Metric', 'Value', 'Minimum Required', 'Status'],
            ['DSCR (Current)',
             f"{underwriting_results.get('dscr', 0):.2f}x",
             '1.25x',
             '✓ Pass' if underwriting_results.get('dscr', 0) >= 1.25 else '✗ Fail'],
            ['DSCR (Stressed)',
             f"{underwriting_results.get('dscr_stressed', 0):.2f}x",
             '1.15x',
             '✓ Pass' if underwriting_results.get('dscr_stressed', 0) >= 1.15 else '✗ Fail'],
            ['LTV Ratio',
             f"{underwriting_results.get('ltv', 0):.1%}",
             '< 80%',
             '✓ Pass' if underwriting_results.get('ltv', 0) <= 0.80 else '✗ Fail'],
            ['Debt Yield',
             f"{underwriting_results.get('debt_yield', 0):.1%}",
             '> 10%',
             '✓ Pass' if underwriting_results.get('debt_yield', 0) >= 0.10 else '✗ Fail'],
        ]
        
        table = Table(data, colWidths=[2*inch, 1.5*inch, 1.5*inch, 1*inch])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#2ecc71')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 11),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 10),
            ('TOPPADDING', (0, 0), (-1, 0), 10),
            ('BACKGROUND', (0, 1), (-1, -1), colors.white),
            ('TEXTCOLOR', (0, 1), (-1, -1), colors.HexColor('#2c3e50')),
            ('FONTNAME', (0, 1), (0, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 1), (-1, -1), 10),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f8f9fa')]),
        ]))
        
        elements.append(table)
        elements.append(Spacer(1, 0.2*inch))
        
        # Cash flow analysis
        elements.append(Paragraph("Cash Flow Analysis", self.styles['Heading4']))
        
        cash_flow_text = f"""
        <b>Global Cash Flow:</b> ${underwriting_results.get('global_cash_flow', 0):,.2f}<br/>
        <b>Annual Debt Service:</b> ${underwriting_results.get('total_debt_service', 0):,.2f}<br/>
        <b>Monthly Payment:</b> ${underwriting_results.get('monthly_payment', 0):,.2f}<br/>
        """
        
        elements.append(Paragraph(cash_flow_text, self.styles['CustomBody']))
        elements.append(Spacer(1, 0.2*inch))
        
        return elements
    
    def _build_risk_assessment(self, underwriting_results: Dict) -> List:
        """Build risk assessment section"""
        elements = []
        
        elements.append(Paragraph("RISK ASSESSMENT", self.styles['SectionHeader']))
        elements.append(Spacer(1, 0.1*inch))
        
        # Risk score display
        risk_score = underwriting_results.get('risk_score', 0)
        risk_rating = underwriting_results.get('risk_rating', 'Unknown')
        pod = underwriting_results.get('probability_of_default', 0)
        
        risk_text = f"""
        <b>Risk Score:</b> {risk_score}/100<br/>
        <b>Risk Rating:</b> {risk_rating}<br/>
        <b>Probability of Default:</b> {pod:.1%}<br/>
        """
        
        elements.append(Paragraph(risk_text, self.styles['CustomBody']))
        elements.append(Spacer(1, 0.15*inch))
        
        # Strengths
        strengths = underwriting_results.get('strengths', [])
        if strengths:
            elements.append(Paragraph("<b>Strengths:</b>", self.styles['Heading4']))
            for strength in strengths:
                elements.append(Paragraph(f"• {strength}", self.styles['CustomBody']))
            elements.append(Spacer(1, 0.1*inch))
        
        # Yellow flags
        yellow_flags = underwriting_results.get('yellow_flags', [])
        if yellow_flags:
            elements.append(Paragraph("<b>Areas of Concern:</b>", self.styles['Heading4']))
            for flag in yellow_flags:
                elements.append(Paragraph(f"• {flag}", self.styles['CustomBody']))
            elements.append(Spacer(1, 0.1*inch))
        
        # Red flags
        red_flags = underwriting_results.get('red_flags', [])
        if red_flags:
            elements.append(Paragraph("<b>Critical Issues:</b>", self.styles['Heading4']))
            for flag in red_flags:
                elements.append(Paragraph(f"• {flag}", self.styles['CustomBody']))
            elements.append(Spacer(1, 0.1*inch))
        
        return elements
    
    def _build_recommendation(self, underwriting_results: Dict) -> List:
        """Build recommendation section"""
        elements = []
        
        elements.append(Spacer(1, 0.2*inch))
        
        recommendation = underwriting_results.get('recommendation', 'PENDING')
        
        # Color code recommendation
        if recommendation == 'APPROVE':
            bg_color = colors.HexColor('#2ecc71')
            text = "RECOMMENDATION: APPROVE"
        elif recommendation == 'CONDITIONAL_APPROVE':
            bg_color = colors.HexColor('#f39c12')
            text = "RECOMMENDATION: CONDITIONAL APPROVAL"
        else:
            bg_color = colors.HexColor('#e74c3c')
            text = "RECOMMENDATION: DECLINE"
        
        # Create recommendation box
        rec_table = Table([[text]], colWidths=[6*inch])
        rec_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), bg_color),
            ('TEXTCOLOR', (0, 0), (-1, -1), colors.white),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 16),
            ('TOPPADDING', (0, 0), (-1, -1), 15),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 15),
        ]))
        
        elements.append(rec_table)
        elements.append(Spacer(1, 0.2*inch))
        
        # Add suggested terms if approved
        if recommendation in ['APPROVE', 'CONDITIONAL_APPROVE']:
            suggested_rate = underwriting_results.get('suggested_rate', 0)
            max_loan = underwriting_results.get('max_loan_amount', 0)
            
            terms_text = f"""
            <b>Suggested Interest Rate:</b> {suggested_rate:.3%}<br/>
            <b>Maximum Loan Amount:</b> ${max_loan:,.2f}<br/>
            """
            
            elements.append(Paragraph(terms_text, self.styles['CustomBody']))
        
        return elements
    
    def _build_conditions(self, underwriting_results: Dict) -> List:
        """Build conditions section"""
        elements = []
        
        conditions = underwriting_results.get('required_conditions', [])
        
        if conditions:
            elements.append(Spacer(1, 0.2*inch))
            elements.append(Paragraph("CONDITIONS FOR APPROVAL", self.styles['SectionHeader']))
            elements.append(Spacer(1, 0.1*inch))
            
            for i, condition in enumerate(conditions, 1):
                elements.append(Paragraph(f"{i}. {condition}", self.styles['CustomBody']))
            
            elements.append(Spacer(1, 0.1*inch))
        
        return elements
    
    def _build_appendix(self, underwriting_results: Dict) -> List:
        """Build appendix section"""
        elements = []
        
        elements.append(Paragraph("APPENDIX: CALCULATION METHODOLOGY", self.styles['SectionHeader']))
        elements.append(Spacer(1, 0.1*inch))
        
        methodology_text = """
        <b>Debt Service Coverage Ratio (DSCR):</b><br/>
        DSCR = Net Operating Income / Annual Debt Service<br/>
        Minimum acceptable: 1.25x<br/><br/>
        
        <b>Loan-to-Value Ratio (LTV):</b><br/>
        LTV = Loan Amount / Appraised Property Value<br/>
        Maximum acceptable: 80% (owner-occupied), 75% (investment)<br/><br/>
        
        <b>Debt Yield:</b><br/>
        Debt Yield = Net Operating Income / Loan Amount<br/>
        Minimum acceptable: 10%<br/><br/>
        
        <b>Risk Scoring Methodology:</b><br/>
        Risk score is calculated based on multiple factors including DSCR, LTV, credit score, 
        business tenure, and financial ratios. Scores range from 0-100, with higher scores 
        indicating lower risk.<br/>
        """
        
        elements.append(Paragraph(methodology_text, self.styles['CustomBody']))
        
        return elements
    
    def _build_summary_table(self, loan_data: Dict, borrower_data: Dict, underwriting_results: Dict) -> List:
        """Build summary table for executive summary"""
        elements = []
        
        data = [
            ['Borrower:', borrower_data.get('name', 'N/A')],
            ['Loan Amount:', f"${loan_data.get('loan_amount', 0):,.2f}"],
            ['Loan Type:', loan_data.get('loan_type', 'N/A').replace('_', ' ').title()],
            ['DSCR:', f"{underwriting_results.get('dscr', 0):.2f}x"],
            ['LTV:', f"{underwriting_results.get('ltv', 0):.1%}"],
            ['Risk Rating:', underwriting_results.get('risk_rating', 'N/A')],
        ]
        
        table = Table(data, colWidths=[2*inch, 4*inch])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#3498db')),
            ('TEXTCOLOR', (0, 0), (0, -1), colors.white),
            ('TEXTCOLOR', (1, 0), (1, -1), colors.HexColor('#2c3e50')),
            ('ALIGN', (0, 0), (0, -1), 'RIGHT'),
            ('ALIGN', (1, 0), (1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTNAME', (1, 0), (1, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 11),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 10),
            ('TOPPADDING', (0, 0), (-1, -1), 10),
            ('GRID', (0, 0), (-1, -1), 1, colors.grey),
        ]))
        
        elements.append(table)
        elements.append(Spacer(1, 0.3*inch))
        
        return elements
    
    def _build_key_metrics_summary(self, underwriting_results: Dict) -> List:
        """Build key metrics summary"""
        elements = []
        
        elements.append(Paragraph("KEY UNDERWRITING METRICS", self.styles['SectionHeader']))
        elements.append(Spacer(1, 0.1*inch))
        
        data = [
            ['DSCR (Current)', f"{underwriting_results.get('dscr', 0):.2f}x"],
            ['DSCR (Stressed)', f"{underwriting_results.get('dscr_stressed', 0):.2f}x"],
            ['LTV Ratio', f"{underwriting_results.get('ltv', 0):.1%}"],
            ['Debt Yield', f"{underwriting_results.get('debt_yield', 0):.1%}"],
            ['Risk Score', f"{underwriting_results.get('risk_score', 0)}/100"],
        ]
        
        table = Table(data, colWidths=[3*inch, 3*inch])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#ecf0f1')),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 11),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
            ('TOPPADDING', (0, 0), (-1, -1), 8),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ]))
        
        elements.append(table)
        elements.append(Spacer(1, 0.2*inch))
        
        return elements
    
    def _build_strengths_concerns_summary(self, underwriting_results: Dict) -> List:
        """Build strengths and concerns summary"""
        elements = []
        
        # Strengths
        strengths = underwriting_results.get('strengths', [])
        if strengths:
            elements.append(Paragraph("STRENGTHS", self.styles['SectionHeader']))
            for strength in strengths[:3]:  # Top 3
                elements.append(Paragraph(f"• {strength}", self.styles['CustomBody']))
            elements.append(Spacer(1, 0.15*inch))
        
        # Concerns
        concerns = underwriting_results.get('yellow_flags', []) + underwriting_results.get('red_flags', [])
        if concerns:
            elements.append(Paragraph("AREAS OF CONCERN", self.styles['SectionHeader']))
            for concern in concerns[:3]:  # Top 3
                elements.append(Paragraph(f"• {concern}", self.styles['CustomBody']))
        
        return elements
    
    def _assess_metric(self, value: float, benchmark: float, direction: str) -> str:
        """Assess metric against benchmark"""
        if direction == 'higher':
            if value >= benchmark:
                return "✓ Good"
            else:
                return "⚠ Below"
        else:  # lower
            if value <= benchmark:
                return "✓ Good"
            else:
                return "⚠ Above"
    
    def _add_page_number(self, canvas, doc):
        """Add page number to each page"""
        page_num = canvas.getPageNumber()
        text = f"Page {page_num}"
        canvas.saveState()
        canvas.setFont('Helvetica', 9)
        canvas.setFillColor(colors.grey)
        canvas.drawRightString(7.5*inch, 0.5*inch, text)
        canvas.drawString(0.75*inch, 0.5*inch, f"Generated: {datetime.now().strftime('%Y-%m-%d')}")
        canvas.restoreState()
