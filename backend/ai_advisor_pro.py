"""
Enterprise AI Advisor System
Real LLM Integration for Intelligent Underwriting Assistance
"""
from typing import Dict, List, Optional
from openai import OpenAI
import os
import json
from datetime import datetime


class AIAdvisorPro:
    """
    Production-grade AI advisor using real LLM
    Provides intelligent underwriting assistance and document analysis
    """
    
    def __init__(self):
        # Initialize OpenAI client (API key from environment)
        self.client = OpenAI()
        
        # System prompts for different AI personas
        self.system_prompts = {
            "underwriting_advisor": """You are Cassie, an expert commercial loan underwriting advisor with 20+ years of experience. 
You provide accurate, professional guidance on commercial lending, underwriting standards, risk assessment, and loan structuring.
You explain complex financial concepts clearly and provide actionable recommendations.
Always cite industry standards (FDIC, OCC, SBA guidelines) when relevant.""",
            
            "document_analyzer": """You are Sage, a document analysis specialist for commercial lending.
You extract key information from financial documents, identify red flags, and provide insights on data quality and completeness.
You're detail-oriented and highlight any inconsistencies or concerns.""",
            
            "risk_assessor": """You are Titan, a risk assessment expert for commercial loans.
You evaluate credit risk, market risk, and operational risk. You provide probability of default estimates and risk mitigation strategies.
You're conservative but fair in your assessments.""",
            
            "deal_structurer": """You are Remy, a loan structuring specialist.
You recommend optimal loan terms, pricing, and structures based on risk profile and market conditions.
You balance lender protection with borrower needs."""
        }
    
    def ask_underwriting_question(
        self,
        question: str,
        context: Optional[Dict] = None,
        conversation_history: Optional[List[Dict]] = None
    ) -> Dict:
        """
        Answer underwriting questions with context awareness
        
        Args:
            question: User's question
            context: Optional context (loan data, borrower info, etc.)
            conversation_history: Previous conversation messages
            
        Returns:
            Dict with answer, confidence, and sources
        """
        try:
            # Build messages
            messages = [
                {"role": "system", "content": self.system_prompts["underwriting_advisor"]}
            ]
            
            # Add conversation history if available
            if conversation_history:
                messages.extend(conversation_history[-5:])  # Last 5 messages for context
            
            # Add context if available
            if context:
                context_str = self._format_context(context)
                messages.append({
                    "role": "system",
                    "content": f"Current loan context:\n{context_str}"
                })
            
            # Add user question
            messages.append({"role": "user", "content": question})
            
            # Call OpenAI API
            response = self.client.chat.completions.create(
                model="gpt-4.1-mini",  # Using available model
                messages=messages,
                temperature=0.3,  # Lower temperature for more consistent answers
                max_tokens=500
            )
            
            answer = response.choices[0].message.content
            
            return {
                "answer": answer,
                "confidence": 0.95,  # High confidence with real LLM
                "model": "gpt-4.1-mini",
                "timestamp": datetime.now().isoformat(),
                "tokens_used": response.usage.total_tokens
            }
            
        except Exception as e:
            # Fallback to knowledge base if API fails
            return self._fallback_answer(question)
    
    def analyze_document_with_ai(
        self,
        document_text: str,
        document_type: str,
        extracted_data: Optional[Dict] = None
    ) -> Dict:
        """
        Use AI to analyze document and provide insights
        
        Args:
            document_text: Raw text from document
            document_type: Type of document
            extracted_data: Already extracted structured data
            
        Returns:
            Dict with analysis, findings, and recommendations
        """
        try:
            messages = [
                {"role": "system", "content": self.system_prompts["document_analyzer"]},
                {"role": "user", "content": f"""Analyze this {document_type} document and provide:
1. Key financial metrics and their significance
2. Any red flags or concerns
3. Data quality assessment
4. Missing information that should be requested
5. Overall assessment

Document text:
{document_text[:3000]}  # Limit to avoid token limits

{f"Already extracted data: {json.dumps(extracted_data, default=str)}" if extracted_data else ""}
"""}
            ]
            
            response = self.client.chat.completions.create(
                model="gpt-4.1-mini",
                messages=messages,
                temperature=0.2,
                max_tokens=800
            )
            
            analysis = response.choices[0].message.content
            
            return {
                "analysis": analysis,
                "document_type": document_type,
                "model": "gpt-4.1-mini",
                "timestamp": datetime.now().isoformat(),
                "tokens_used": response.usage.total_tokens
            }
            
        except Exception as e:
            return {
                "analysis": f"AI analysis unavailable: {str(e)}",
                "error": True
            }
    
    def assess_risk_with_ai(
        self,
        loan_data: Dict,
        borrower_data: Dict,
        financial_data: Dict,
        underwriting_results: Dict
    ) -> Dict:
        """
        Use AI to provide comprehensive risk assessment
        
        Args:
            loan_data: Loan request details
            borrower_data: Borrower information
            financial_data: Financial analysis
            underwriting_results: Underwriting calculations
            
        Returns:
            Dict with risk assessment and recommendations
        """
        try:
            # Format data for AI
            data_summary = f"""
Loan Request:
- Amount: ${loan_data.get('loan_amount', 0):,.2f}
- Type: {loan_data.get('loan_type', 'N/A')}
- Purpose: {loan_data.get('loan_purpose', 'N/A')}
- Term: {loan_data.get('term_months', 0)} months

Borrower:
- Name: {borrower_data.get('name', 'N/A')}
- Credit Score: {borrower_data.get('credit_score', 'N/A')}
- Years in Business: {borrower_data.get('years_in_business', 'N/A')}
- Annual Revenue: ${borrower_data.get('annual_revenue', 0):,.2f}

Underwriting Metrics:
- DSCR: {underwriting_results.get('dscr', 0):.2f}x
- DSCR (Stressed): {underwriting_results.get('dscr_stressed', 0):.2f}x
- LTV: {underwriting_results.get('ltv', 0):.1%}
- Debt Yield: {underwriting_results.get('debt_yield', 0):.1%}
- Risk Score: {underwriting_results.get('risk_score', 0)}/100

Financial Metrics:
- Current Ratio: {financial_data.get('current_ratio', 'N/A')}
- Profit Margin: {financial_data.get('profit_margin', 'N/A')}
- Debt-to-Equity: {financial_data.get('debt_to_equity', 'N/A')}
"""
            
            messages = [
                {"role": "system", "content": self.system_prompts["risk_assessor"]},
                {"role": "user", "content": f"""Provide a comprehensive risk assessment for this commercial loan:

{data_summary}

Please provide:
1. Overall risk rating (Low/Medium/High) with justification
2. Key risk factors and their severity
3. Mitigating factors
4. Recommended risk mitigation strategies
5. Probability of default estimate
6. Recommended pricing premium (if any)
"""}
            ]
            
            response = self.client.chat.completions.create(
                model="gpt-4.1-mini",
                messages=messages,
                temperature=0.2,
                max_tokens=800
            )
            
            assessment = response.choices[0].message.content
            
            return {
                "assessment": assessment,
                "model": "gpt-4.1-mini",
                "timestamp": datetime.now().isoformat(),
                "tokens_used": response.usage.total_tokens
            }
            
        except Exception as e:
            return {
                "assessment": f"AI risk assessment unavailable: {str(e)}",
                "error": True
            }
    
    def suggest_loan_structure(
        self,
        loan_data: Dict,
        borrower_data: Dict,
        underwriting_results: Dict,
        market_conditions: Optional[Dict] = None
    ) -> Dict:
        """
        Use AI to suggest optimal loan structure
        
        Args:
            loan_data: Loan request details
            borrower_data: Borrower information
            underwriting_results: Underwriting results
            market_conditions: Current market data
            
        Returns:
            Dict with suggested loan structure and terms
        """
        try:
            data_summary = f"""
Requested Loan:
- Amount: ${loan_data.get('loan_amount', 0):,.2f}
- Type: {loan_data.get('loan_type', 'N/A')}
- Rate: {loan_data.get('interest_rate', 0):.3%}
- Term: {loan_data.get('term_months', 0)} months

Borrower Profile:
- Credit Score: {borrower_data.get('credit_score', 'N/A')}
- Risk Rating: {underwriting_results.get('risk_rating', 'N/A')}

Underwriting Results:
- DSCR: {underwriting_results.get('dscr', 0):.2f}x
- LTV: {underwriting_results.get('ltv', 0):.1%}
- Risk Score: {underwriting_results.get('risk_score', 0)}/100
- Recommendation: {underwriting_results.get('recommendation', 'N/A')}
"""
            
            messages = [
                {"role": "system", "content": self.system_prompts["deal_structurer"]},
                {"role": "user", "content": f"""Based on this loan request and underwriting results, suggest an optimal loan structure:

{data_summary}

Please provide:
1. Recommended loan amount (if different from requested)
2. Suggested interest rate with justification
3. Optimal term and amortization
4. Required down payment
5. Recommended covenants or conditions
6. Alternative structures to consider
7. Pricing rationale
"""}
            ]
            
            response = self.client.chat.completions.create(
                model="gpt-4.1-mini",
                messages=messages,
                temperature=0.3,
                max_tokens=800
            )
            
            suggestions = response.choices[0].message.content
            
            return {
                "suggestions": suggestions,
                "model": "gpt-4.1-mini",
                "timestamp": datetime.now().isoformat(),
                "tokens_used": response.usage.total_tokens
            }
            
        except Exception as e:
            return {
                "suggestions": f"AI structuring suggestions unavailable: {str(e)}",
                "error": True
            }
    
    def generate_underwriting_summary(
        self,
        loan_data: Dict,
        borrower_data: Dict,
        underwriting_results: Dict,
        document_analysis: Optional[List[Dict]] = None
    ) -> str:
        """
        Generate AI-powered executive summary for underwriting
        
        Args:
            loan_data: Loan request details
            borrower_data: Borrower information
            underwriting_results: Underwriting results
            document_analysis: Analysis of submitted documents
            
        Returns:
            Executive summary text
        """
        try:
            data_summary = f"""
Loan: ${loan_data.get('loan_amount', 0):,.2f} {loan_data.get('loan_type', 'N/A')}
Borrower: {borrower_data.get('name', 'N/A')}
DSCR: {underwriting_results.get('dscr', 0):.2f}x
LTV: {underwriting_results.get('ltv', 0):.1%}
Risk Rating: {underwriting_results.get('risk_rating', 'N/A')}
Recommendation: {underwriting_results.get('recommendation', 'N/A')}

Strengths: {', '.join(underwriting_results.get('strengths', [])[:3])}
Concerns: {', '.join(underwriting_results.get('yellow_flags', [])[:3])}
"""
            
            messages = [
                {"role": "system", "content": "You are an expert at writing concise, professional executive summaries for commercial loan underwriting."},
                {"role": "user", "content": f"""Write a 3-4 sentence executive summary for this loan underwriting:

{data_summary}

The summary should be suitable for senior management review and clearly state the recommendation with key supporting points."""}
            ]
            
            response = self.client.chat.completions.create(
                model="gpt-4.1-mini",
                messages=messages,
                temperature=0.3,
                max_tokens=200
            )
            
            return response.choices[0].message.content
            
        except Exception as e:
            return f"Executive summary generation failed: {str(e)}"
    
    def _format_context(self, context: Dict) -> str:
        """Format context dictionary into readable string"""
        formatted = []
        for key, value in context.items():
            if isinstance(value, (int, float)):
                if key.endswith('_amount') or key.endswith('_value'):
                    formatted.append(f"{key}: ${value:,.2f}")
                elif key.endswith('_rate') or key.endswith('_ratio'):
                    formatted.append(f"{key}: {value:.2%}")
                else:
                    formatted.append(f"{key}: {value}")
            else:
                formatted.append(f"{key}: {value}")
        return "\n".join(formatted)
    
    def _fallback_answer(self, question: str) -> Dict:
        """Fallback knowledge base when API is unavailable"""
        question_lower = question.lower()
        
        knowledge_base = {
            "documents": "For commercial loans, you typically need: 1) Business tax returns (2-3 years), 2) Personal tax returns of guarantors, 3) Business financial statements (P&L, Balance Sheet), 4) Rent roll (for investment properties), 5) Purchase agreement, 6) Property appraisal, 7) Business plan, 8) Personal financial statement (PFS)",
            "ltv": "Loan-to-Value (LTV) is calculated as: LTV = (Loan Amount / Appraised Property Value) × 100. For example, a $750,000 loan on a $1,000,000 property = 75% LTV. Most commercial lenders require LTV below 80% for owner-occupied and 75% for investment properties.",
            "dscr": "Debt Service Coverage Ratio (DSCR) measures cash flow available to cover debt payments. Formula: DSCR = Net Operating Income / Annual Debt Service. A DSCR of 1.25 means the property generates 25% more income than needed for debt payments. Most lenders require minimum 1.20-1.25 DSCR.",
            "credit": "Credit score requirements vary by loan type. For SBA 7(a) loans, minimum is typically 680. For conventional commercial loans, 680-700+ is preferred. For owner-occupied CRE, 700+ is ideal. Lower scores may require higher down payments or personal guarantees."
        }
        
        if "document" in question_lower:
            answer = knowledge_base["documents"]
        elif "ltv" in question_lower or "loan-to-value" in question_lower:
            answer = knowledge_base["ltv"]
        elif "dscr" in question_lower or "debt service" in question_lower:
            answer = knowledge_base["dscr"]
        elif "credit" in question_lower:
            answer = knowledge_base["credit"]
        else:
            answer = "I'm an AI advisor specialized in commercial loan underwriting. I can help with questions about documents, financial ratios, credit requirements, and underwriting standards. Please ask a specific question."
        
        return {
            "answer": answer,
            "confidence": 0.85,
            "model": "fallback",
            "timestamp": datetime.now().isoformat()
        }
