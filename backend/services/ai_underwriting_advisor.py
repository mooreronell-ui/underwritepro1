"""
AI Underwriting Advisor
Specialized AI assistant with real commercial lending knowledge
"""

from typing import Optional, List, Dict
from openai import OpenAI
import os


class AIUnderwritingAdvisor:
    """
    AI-powered underwriting advisor with specialized knowledge
    
    This is NOT generic ChatGPT - it's a specialized advisor trained on:
    - Commercial lending best practices
    - Underwriting guidelines
    - Financial ratio interpretation
    - Risk assessment methodologies
    - Regulatory requirements
    """
    
    # System prompt with comprehensive underwriting knowledge
    SYSTEM_PROMPT = """You are an expert commercial loan underwriting advisor with 20+ years of experience. You provide accurate, actionable guidance on commercial lending, underwriting, and risk assessment.

**Your Expertise:**
- Commercial Real Estate (CRE) lending - owner-occupied and investment properties
- SBA loans (7(a) and 504 programs)
- Equipment financing and business acquisition loans
- Financial statement analysis and ratio interpretation
- Risk assessment and credit decisioning
- Regulatory compliance (FDIC, OCC, NCUA guidelines)

**Key Underwriting Concepts You Know:**

**DSCR (Debt Service Coverage Ratio):**
- Global DSCR: (Business Net Income + Personal Income + Rent Savings) / Total Debt Payments
  - Used for owner-occupied properties
  - Typical minimum: 1.25x
  - Combines business and personal cash flow
  
- Property DSCR: NOI / Proposed Debt Payment
  - Used for investment properties
  - Typical minimum: 1.20-1.25x
  - Property cash flow only
  
- Business DSCR: EBITDA / Total Debt Payments
  - Used for all loan types as secondary measure
  
**LTV (Loan-to-Value):**
- Owner-occupied CRE: Typical max 75-80%
- Investment property: Typical max 70-75%
- Lower LTV = lower risk for lender

**Credit Standards:**
- Business credit (Paydex/Experian): 70+ preferred
- Personal credit (FICO): 680+ preferred, 720+ for best terms
- Credit history more important than score alone

**Financial Analysis:**
- Profitability: Net margin 5%+, EBITDA margin 10%+
- Liquidity: Current ratio 1.5+, Quick ratio 1.0+
- Leverage: Debt-to-EBITDA < 4.0x
- Tenure: 2+ years in business preferred, 5+ years ideal

**Property Analysis:**
- Cap Rate: 6-10% typical for commercial properties
- Debt Yield: 10-12% minimum for lenders
- Occupancy: 85%+ for stabilized properties
- Operating Expense Ratio: 30-50% typical

**Risk Ratings:**
- Exceptional (90-100): Minimal risk, best terms
- Good (80-89): Low risk, standard terms
- Acceptable (70-79): Moderate risk, may require conditions
- Marginal (60-69): Higher risk, requires manual review
- Unacceptable (0-59): Decline or significant restructuring needed

**Your Communication Style:**
- Direct and professional
- Use specific numbers and thresholds
- Explain the "why" behind underwriting decisions
- Provide actionable recommendations
- Reference industry standards when relevant

**What You DON'T Do:**
- Make final credit decisions (you advise, humans decide)
- Provide legal advice
- Guarantee loan approval
- Discuss specific lender pricing (rates vary by lender)

Answer questions clearly and concisely. If asked about a specific loan scenario, provide analysis based on the information given and ask for any missing critical data points."""

    def __init__(self):
        """Initialize AI advisor with OpenAI client"""
        self.client = OpenAI()  # Uses OPENAI_API_KEY from environment
        self.model = "gpt-4.1-mini"  # Fast, cost-effective, high-quality
    
    def ask(
        self,
        question: str,
        context: Optional[Dict] = None,
        conversation_history: Optional[List[Dict]] = None
    ) -> str:
        """
        Ask the AI advisor a question
        
        Args:
            question: User's question
            context: Optional loan/borrower context for more specific advice
            conversation_history: Optional previous messages for context
        
        Returns:
            AI advisor's response
        """
        # Build messages
        messages = [{"role": "system", "content": self.SYSTEM_PROMPT}]
        
        # Add conversation history if provided
        if conversation_history:
            messages.extend(conversation_history)
        
        # Add context if provided
        if context:
            context_str = self._format_context(context)
            messages.append({
                "role": "system",
                "content": f"Current loan context:\n{context_str}"
            })
        
        # Add user question
        messages.append({"role": "user", "content": question})
        
        # Get response from AI
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=0.7,
                max_tokens=1000
            )
            
            return response.choices[0].message.content
            
        except Exception as e:
            return f"I apologize, but I'm having trouble processing your question right now. Please try again. Error: {str(e)}"
    
    def analyze_loan(self, loan_data: Dict) -> str:
        """
        Provide comprehensive analysis of a loan application
        
        Args:
            loan_data: Dictionary with loan details, ratios, risk assessment
        
        Returns:
            Detailed analysis and recommendations
        """
        prompt = f"""Please provide a comprehensive analysis of this commercial loan application:

**Loan Details:**
- Loan Type: {loan_data.get('loan_type')}
- Loan Amount: ${loan_data.get('loan_amount'):,.2f}
- Property Type: {loan_data.get('property_type')}

**Financial Ratios:**
- DSCR: {loan_data.get('dscr', 'N/A')}
- LTV: {loan_data.get('ltv', 'N/A')}%
- Debt Yield: {loan_data.get('debt_yield', 'N/A')}%
- Current Ratio: {loan_data.get('current_ratio', 'N/A')}
- Net Margin: {loan_data.get('net_margin', 'N/A')}%

**Borrower Profile:**
- Years in Business: {loan_data.get('years_in_business', 'N/A')}
- Industry: {loan_data.get('industry', 'N/A')}
- Business Credit: {loan_data.get('business_credit', 'N/A')}
- Personal Credit: {loan_data.get('personal_credit', 'N/A')}

**Risk Assessment:**
- Overall Risk Score: {loan_data.get('risk_score', 'N/A')}/100
- Risk Rating: {loan_data.get('risk_rating', 'N/A')}

Please provide:
1. Strengths of this application
2. Weaknesses or concerns
3. Recommended decision (approve/conditions/refer/decline)
4. Suggested conditions or mitigations if applicable
5. Key considerations for the underwriter"""

        return self.ask(prompt)
    
    def explain_ratio(self, ratio_name: str, value: Optional[float] = None) -> str:
        """
        Explain a specific financial ratio
        
        Args:
            ratio_name: Name of the ratio (e.g., "DSCR", "LTV", "Cap Rate")
            value: Optional current value to provide context
        
        Returns:
            Explanation of the ratio and its significance
        """
        prompt = f"Please explain the {ratio_name} ratio in commercial lending."
        
        if value is not None:
            prompt += f" The current value is {value}. Is this good, acceptable, or concerning?"
        
        prompt += " Keep the explanation concise but informative."
        
        return self.ask(prompt)
    
    def suggest_improvements(self, loan_data: Dict, weak_areas: List[str]) -> str:
        """
        Suggest ways to improve a loan application
        
        Args:
            loan_data: Current loan details
            weak_areas: List of weak components (e.g., ["dscr", "liquidity"])
        
        Returns:
            Specific recommendations to strengthen the application
        """
        prompt = f"""This loan application has weaknesses in: {', '.join(weak_areas)}.

Current metrics:
- DSCR: {loan_data.get('dscr', 'N/A')}
- LTV: {loan_data.get('ltv', 'N/A')}%
- Current Ratio: {loan_data.get('current_ratio', 'N/A')}
- Loan Amount: ${loan_data.get('loan_amount'):,.2f}

What specific steps can the borrower take to strengthen this application? Provide actionable recommendations."""

        return self.ask(prompt)
    
    def compare_scenarios(self, scenario_a: Dict, scenario_b: Dict) -> str:
        """
        Compare two loan scenarios
        
        Args:
            scenario_a: First scenario details
            scenario_b: Second scenario details
        
        Returns:
            Comparison analysis
        """
        prompt = f"""Please compare these two loan scenarios:

**Scenario A:**
- Loan Amount: ${scenario_a.get('loan_amount'):,.2f}
- Term: {scenario_a.get('term')} months
- DSCR: {scenario_a.get('dscr')}
- LTV: {scenario_a.get('ltv')}%

**Scenario B:**
- Loan Amount: ${scenario_b.get('loan_amount'):,.2f}
- Term: {scenario_b.get('term')} months
- DSCR: {scenario_b.get('dscr')}
- LTV: {scenario_b.get('ltv')}%

Which scenario is stronger from an underwriting perspective and why?"""

        return self.ask(prompt)
    
    def _format_context(self, context: Dict) -> str:
        """Format context dictionary into readable string"""
        lines = []
        for key, value in context.items():
            if value is not None:
                lines.append(f"- {key.replace('_', ' ').title()}: {value}")
        return "\n".join(lines)
    
    # ========================================================================
    # Pre-defined Q&A for Common Questions
    # ========================================================================
    
    @staticmethod
    def get_quick_answer(question_key: str) -> Optional[str]:
        """
        Get pre-defined answers for common questions (faster than API call)
        
        Args:
            question_key: Key for the question
        
        Returns:
            Pre-defined answer or None if not found
        """
        quick_answers = {
            "what_is_dscr": """**Debt Service Coverage Ratio (DSCR)** measures a borrower's ability to service debt.

**Formula:** Cash Flow / Debt Payments

**Types:**
- **Global DSCR** (owner-occupied): (Business + Personal Income) / Total Debt
- **Property DSCR** (investment): Property NOI / Proposed Payment
- **Business DSCR**: EBITDA / Total Debt

**Minimums:**
- Owner-occupied: 1.25x typical
- Investment property: 1.20-1.25x typical

**Interpretation:**
- 1.50+: Excellent
- 1.25-1.49: Good
- 1.15-1.24: Marginal
- <1.15: Insufficient coverage""",

            "what_is_ltv": """**Loan-to-Value (LTV)** measures loan amount relative to property value.

**Formula:** (Loan Amount / Property Value) × 100

**Typical Maximums:**
- Owner-occupied CRE: 75-80%
- Investment property: 70-75%
- SBA 7(a): 85-90%
- SBA 504: 90%

**Why It Matters:**
- Lower LTV = more borrower equity = less lender risk
- Higher LTV = less cushion if property value declines

**Sweet Spot:** 65-75% for best terms""",

            "what_documents_needed": """**Required Documents for Commercial Loans:**

**Business Documents:**
- 3 years business tax returns (1120, 1120S, 1065)
- YTD Profit & Loss and Balance Sheet
- Business bank statements (3-6 months)
- Business credit report
- Articles of incorporation / Operating agreement

**Personal Documents (Guarantors):**
- Personal tax returns (1040) - 2-3 years
- Personal financial statement
- Personal credit report
- Government-issued ID

**Property Documents:**
- Purchase agreement (if acquisition)
- Appraisal or property valuation
- Rent roll (if investment property)
- Operating statements (if investment property)
- Environmental Phase I (for some properties)

**Additional:**
- Business plan or use of proceeds
- Insurance certificates
- Lease agreements""",

            "how_calculate_noi": """**Net Operating Income (NOI)** is the property's annual income after operating expenses.

**Formula:**
NOI = Effective Gross Income - Operating Expenses

**Step-by-Step:**
1. Start with Gross Potential Rent (all units at market rent)
2. Subtract Vacancy Loss (typically 5-10%)
3. Add Other Income (parking, laundry, etc.)
4. = **Effective Gross Income (EGI)**
5. Subtract Operating Expenses:
   - Property taxes
   - Insurance
   - Property management
   - Utilities
   - Repairs & maintenance
   - Reserves
6. = **Net Operating Income (NOI)**

**Important:** NOI does NOT include:
- Debt service (loan payments)
- Depreciation
- Income taxes
- Capital improvements

**Why It Matters:**
- Used to calculate Property DSCR
- Used to calculate Cap Rate
- Used to calculate Debt Yield"""
        }
        
        return quick_answers.get(question_key)
