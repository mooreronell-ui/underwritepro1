import math
from typing import Dict, List, Optional
from pydantic import BaseModel

class LoanTerms(BaseModel):
    """Loan terms for underwriting"""
    loan_amount: float
    interest_rate: float
    amortization_months: int
    balloon_months: Optional[int] = None

class FinancialData(BaseModel):
    """Financial data extracted from documents"""
    business_revenue: float = 0
    business_net_income: float = 0
    depreciation: float = 0
    amortization: float = 0
    interest_expense: float = 0
    one_time_expenses: float = 0
    personal_agi: float = 0
    personal_debt_annual: float = 0
    k1_income: float = 0
    rental_income: float = 0
    other_income: float = 0

class UnderwritingRequest(BaseModel):
    """Request for underwriting calculation"""
    loan_terms: LoanTerms
    financial_data: FinancialData
    appraised_value: float
    include_addbacks: bool = True
    stress_test: bool = False

class DSCRResult(BaseModel):
    """DSCR calculation result"""
    dscr: float
    global_cash_flow: float
    annual_debt_service: float
    monthly_payment: float
    business_cash_flow: float
    personal_cash_flow: float
    total_addbacks: float

class UnderwritingResult(BaseModel):
    """Complete underwriting result"""
    dscr_base: float
    dscr_stressed: Optional[float]
    ltv: float
    global_cash_flow: float
    annual_debt_service: float
    monthly_payment: float
    liquidity_months: float
    business_cash_flow: float
    personal_income: float
    addbacks: Dict[str, float]
    flags: List[str]
    strengths: List[str]
    risks: List[str]
    mitigants: List[str]
    recommendation: str
    calculation_trace: Dict

class UnderwritingEngine:
    """F500-level underwriting engine"""
    
    # Thresholds (configurable per lender)
    DSCR_MIN = 1.20
    DSCR_STRONG = 1.50
    LTV_MAX = 0.80
    LTV_CONSERVATIVE = 0.70
    LIQUIDITY_MIN_MONTHS = 3
    LIQUIDITY_STRONG_MONTHS = 6
    
    @staticmethod
    def calculate_payment(principal: float, annual_rate: float, months: int) -> float:
        """Calculate monthly payment using amortization formula"""
        if months == 0 or principal == 0:
            return 0
        
        monthly_rate = annual_rate / 12.0
        if monthly_rate == 0:
            return principal / months
        
        payment = principal * (monthly_rate * (1 + monthly_rate) ** months) / \
                  ((1 + monthly_rate) ** months - 1)
        return payment
    
    @staticmethod
    def calculate_dscr(
        loan_terms: LoanTerms,
        financial_data: FinancialData,
        include_addbacks: bool = True
    ) -> DSCRResult:
        """Calculate Debt Service Coverage Ratio with global cash flow"""
        
        # Calculate monthly payment
        monthly_payment = UnderwritingEngine.calculate_payment(
            loan_terms.loan_amount,
            loan_terms.interest_rate,
            loan_terms.amortization_months
        )
        annual_debt_service = monthly_payment * 12
        
        # Business cash flow
        business_cf = financial_data.business_net_income
        
        # Addbacks (non-cash expenses)
        total_addbacks = 0
        if include_addbacks:
            total_addbacks = (
                financial_data.depreciation +
                financial_data.amortization +
                financial_data.one_time_expenses
            )
        
        business_cash_flow = business_cf + total_addbacks
        
        # Personal cash flow
        personal_cash_flow = (
            financial_data.personal_agi +
            financial_data.k1_income +
            financial_data.rental_income +
            financial_data.other_income -
            financial_data.personal_debt_annual
        )
        
        # Global cash flow
        global_cf = business_cash_flow + personal_cash_flow
        
        # DSCR
        dscr = global_cf / annual_debt_service if annual_debt_service > 0 else 0
        
        return DSCRResult(
            dscr=round(dscr, 2),
            global_cash_flow=round(global_cf, 2),
            annual_debt_service=round(annual_debt_service, 2),
            monthly_payment=round(monthly_payment, 2),
            business_cash_flow=round(business_cash_flow, 2),
            personal_cash_flow=round(personal_cash_flow, 2),
            total_addbacks=round(total_addbacks, 2)
        )
    
    @staticmethod
    def calculate_ltv(loan_amount: float, appraised_value: float) -> float:
        """Calculate Loan-to-Value ratio"""
        if appraised_value == 0:
            return 0
        return round(loan_amount / appraised_value, 4)
    
    @staticmethod
    def stress_test_dscr(
        loan_terms: LoanTerms,
        financial_data: FinancialData,
        rate_increase: float = 0.02,  # 200 basis points
        income_decrease: float = 0.10  # 10% decrease
    ) -> DSCRResult:
        """Stress test DSCR with adverse scenarios"""
        
        # Stressed loan terms
        stressed_terms = LoanTerms(
            loan_amount=loan_terms.loan_amount,
            interest_rate=loan_terms.interest_rate + rate_increase,
            amortization_months=loan_terms.amortization_months,
            balloon_months=loan_terms.balloon_months
        )
        
        # Stressed financial data
        stressed_financials = financial_data.copy()
        stressed_financials.business_net_income *= (1 - income_decrease)
        stressed_financials.business_revenue *= (1 - income_decrease)
        
        return UnderwritingEngine.calculate_dscr(stressed_terms, stressed_financials)
    
    @staticmethod
    def analyze_flags(dscr: float, ltv: float, liquidity_months: float) -> List[str]:
        """Generate underwriting flags based on thresholds"""
        flags = []
        
        # DSCR flags
        if dscr < UnderwritingEngine.DSCR_MIN:
            flags.append(f"DSCR_WEAK: {dscr:.2f} below minimum {UnderwritingEngine.DSCR_MIN}")
        elif dscr >= UnderwritingEngine.DSCR_STRONG:
            flags.append(f"DSCR_STRONG: {dscr:.2f}")
        else:
            flags.append(f"DSCR_ACCEPTABLE: {dscr:.2f}")
        
        # LTV flags
        if ltv > UnderwritingEngine.LTV_MAX:
            flags.append(f"LTV_EXCEPTION: {ltv:.2%} exceeds maximum {UnderwritingEngine.LTV_MAX:.0%}")
        elif ltv <= UnderwritingEngine.LTV_CONSERVATIVE:
            flags.append(f"LTV_CONSERVATIVE: {ltv:.2%}")
        else:
            flags.append(f"LTV_ACCEPTABLE: {ltv:.2%}")
        
        # Liquidity flags
        if liquidity_months < UnderwritingEngine.LIQUIDITY_MIN_MONTHS:
            flags.append(f"LIQUIDITY_WEAK: {liquidity_months:.1f} months below minimum {UnderwritingEngine.LIQUIDITY_MIN_MONTHS}")
        elif liquidity_months >= UnderwritingEngine.LIQUIDITY_STRONG_MONTHS:
            flags.append(f"LIQUIDITY_STRONG: {liquidity_months:.1f} months")
        else:
            flags.append(f"LIQUIDITY_ACCEPTABLE: {liquidity_months:.1f} months")
        
        return flags
    
    @staticmethod
    def generate_narrative(
        dscr_base: float,
        dscr_stressed: Optional[float],
        ltv: float,
        liquidity_months: float,
        financial_data: FinancialData
    ) -> tuple[List[str], List[str], List[str], str]:
        """Generate F500-level narrative: Strengths, Risks, Mitigants, Recommendation"""
        
        strengths = []
        risks = []
        mitigants = []
        
        # Analyze strengths
        if dscr_base >= UnderwritingEngine.DSCR_STRONG:
            strengths.append(f"Strong debt service coverage of {dscr_base:.2f}x provides substantial cushion")
        
        if ltv <= UnderwritingEngine.LTV_CONSERVATIVE:
            strengths.append(f"Conservative LTV of {ltv:.1%} provides significant equity cushion")
        
        if liquidity_months >= UnderwritingEngine.LIQUIDITY_STRONG_MONTHS:
            strengths.append(f"Strong liquidity position with {liquidity_months:.1f} months of debt service coverage")
        
        if financial_data.business_revenue > 1000000:
            strengths.append(f"Established business with revenue of ${financial_data.business_revenue:,.0f}")
        
        # Analyze risks
        if dscr_base < UnderwritingEngine.DSCR_MIN:
            risks.append(f"DSCR of {dscr_base:.2f}x below policy minimum of {UnderwritingEngine.DSCR_MIN:.2f}x")
        
        if dscr_stressed and dscr_stressed < 1.0:
            risks.append(f"Stressed DSCR of {dscr_stressed:.2f}x falls below 1.0x under adverse conditions")
        
        if ltv > UnderwritingEngine.LTV_MAX:
            risks.append(f"LTV of {ltv:.1%} exceeds policy maximum of {UnderwritingEngine.LTV_MAX:.0%}")
        
        if liquidity_months < UnderwritingEngine.LIQUIDITY_MIN_MONTHS:
            risks.append(f"Liquidity of {liquidity_months:.1f} months below minimum {UnderwritingEngine.LIQUIDITY_MIN_MONTHS} months")
        
        # Suggest mitigants
        if ltv > UnderwritingEngine.LTV_MAX:
            mitigants.append(f"Require additional equity to bring LTV to {UnderwritingEngine.LTV_MAX:.0%} or below")
        
        if dscr_base < UnderwritingEngine.DSCR_MIN:
            mitigants.append("Consider personal guarantee or additional collateral")
            mitigants.append("Require quarterly financial reporting")
        
        if liquidity_months < UnderwritingEngine.LIQUIDITY_MIN_MONTHS:
            mitigants.append(f"Require minimum liquidity covenant of {UnderwritingEngine.LIQUIDITY_MIN_MONTHS} months debt service")
        
        # Generate recommendation
        approve_count = sum([
            dscr_base >= UnderwritingEngine.DSCR_MIN,
            ltv <= UnderwritingEngine.LTV_MAX,
            liquidity_months >= UnderwritingEngine.LIQUIDITY_MIN_MONTHS
        ])
        
        if approve_count == 3:
            recommendation = "APPROVE - All underwriting criteria met"
        elif approve_count == 2:
            recommendation = "APPROVE WITH CONDITIONS - Address identified risks through mitigants"
        elif approve_count == 1:
            recommendation = "EXCEPTION REQUIRED - Multiple policy exceptions, requires senior approval"
        else:
            recommendation = "DECLINE - Does not meet minimum underwriting standards"
        
        return strengths, risks, mitigants, recommendation
    
    @staticmethod
    def underwrite(request: UnderwritingRequest) -> UnderwritingResult:
        """Complete underwriting analysis"""
        
        # Base case DSCR
        dscr_result = UnderwritingEngine.calculate_dscr(
            request.loan_terms,
            request.financial_data,
            request.include_addbacks
        )
        
        # Stressed case (if requested)
        dscr_stressed = None
        if request.stress_test:
            stressed_result = UnderwritingEngine.stress_test_dscr(
                request.loan_terms,
                request.financial_data
            )
            dscr_stressed = stressed_result.dscr
        
        # LTV
        ltv = UnderwritingEngine.calculate_ltv(
            request.loan_terms.loan_amount,
            request.appraised_value
        )
        
        # Liquidity (simplified - would need bank statement data)
        liquidity_months = 0  # Placeholder - calculate from bank statements
        
        # Flags
        flags = UnderwritingEngine.analyze_flags(
            dscr_result.dscr,
            ltv,
            liquidity_months
        )
        
        # Narrative
        strengths, risks, mitigants, recommendation = UnderwritingEngine.generate_narrative(
            dscr_result.dscr,
            dscr_stressed,
            ltv,
            liquidity_months,
            request.financial_data
        )
        
        # Addbacks breakdown
        addbacks = {
            "depreciation": request.financial_data.depreciation,
            "amortization": request.financial_data.amortization,
            "one_time_expenses": request.financial_data.one_time_expenses,
            "total": dscr_result.total_addbacks
        }
        
        # Calculation trace for audit
        calculation_trace = {
            "loan_amount": request.loan_terms.loan_amount,
            "interest_rate": request.loan_terms.interest_rate,
            "amortization_months": request.loan_terms.amortization_months,
            "monthly_payment": dscr_result.monthly_payment,
            "annual_debt_service": dscr_result.annual_debt_service,
            "business_net_income": request.financial_data.business_net_income,
            "addbacks": addbacks,
            "business_cash_flow": dscr_result.business_cash_flow,
            "personal_cash_flow": dscr_result.personal_cash_flow,
            "global_cash_flow": dscr_result.global_cash_flow,
            "dscr_calculation": f"{dscr_result.global_cash_flow:.2f} / {dscr_result.annual_debt_service:.2f} = {dscr_result.dscr:.2f}",
            "ltv_calculation": f"{request.loan_terms.loan_amount:.2f} / {request.appraised_value:.2f} = {ltv:.4f}"
        }
        
        return UnderwritingResult(
            dscr_base=dscr_result.dscr,
            dscr_stressed=dscr_stressed,
            ltv=ltv,
            global_cash_flow=dscr_result.global_cash_flow,
            annual_debt_service=dscr_result.annual_debt_service,
            monthly_payment=dscr_result.monthly_payment,
            liquidity_months=liquidity_months,
            business_cash_flow=dscr_result.business_cash_flow,
            personal_income=dscr_result.personal_cash_flow,
            addbacks=addbacks,
            flags=flags,
            strengths=strengths,
            risks=risks,
            mitigants=mitigants,
            recommendation=recommendation,
            calculation_trace=calculation_trace
        )
