"""
F500-Level Commercial Loan Underwriting Engine
Built to billion-dollar fintech standards
"""
from typing import Dict, List, Optional, Tuple
from decimal import Decimal, ROUND_HALF_UP
from datetime import datetime
from pydantic import BaseModel, Field
import json


class FinancialStatement(BaseModel):
    """Financial statement data"""
    revenue: Decimal
    gross_profit: Decimal
    operating_expenses: Decimal
    ebitda: Decimal
    depreciation: Decimal
    amortization: Decimal
    interest_expense: Decimal
    net_income: Decimal
    total_assets: Decimal
    total_liabilities: Decimal
    current_assets: Decimal
    current_liabilities: Decimal
    cash: Decimal
    accounts_receivable: Decimal
    inventory: Decimal
    period_end_date: datetime


class PropertyDetails(BaseModel):
    """Commercial property details"""
    property_type: str
    address: str
    appraised_value: Decimal
    purchase_price: Optional[Decimal] = None
    square_footage: Optional[int] = None
    year_built: Optional[int] = None
    occupancy_rate: Optional[Decimal] = None
    net_operating_income: Optional[Decimal] = None
    cap_rate: Optional[Decimal] = None


class BorrowerProfile(BaseModel):
    """Borrower profile"""
    name: str
    entity_type: str  # individual, llc, corporation, partnership
    credit_score: Optional[int] = None
    years_in_business: Optional[int] = None
    industry: Optional[str] = None
    annual_revenue: Decimal
    net_worth: Optional[Decimal] = None
    liquidity: Optional[Decimal] = None


class LoanRequest(BaseModel):
    """Loan request details"""
    loan_amount: Decimal
    interest_rate: Decimal
    term_months: int
    amortization_months: int
    loan_purpose: str
    loan_type: str  # owner_occupied, investment, equipment, working_capital
    down_payment: Optional[Decimal] = None


class UnderwritingResult(BaseModel):
    """Comprehensive underwriting results"""
    # Core Ratios
    dscr: Decimal
    dscr_stressed: Decimal
    ltv: Decimal
    debt_yield: Decimal
    
    # Cash Flow Analysis
    global_cash_flow: Decimal
    business_cash_flow: Decimal
    property_noi: Optional[Decimal] = None
    total_debt_service: Decimal
    monthly_payment: Decimal
    
    # Financial Ratios
    current_ratio: Optional[Decimal] = None
    quick_ratio: Optional[Decimal] = None
    debt_to_equity: Optional[Decimal] = None
    profit_margin: Optional[Decimal] = None
    roe: Optional[Decimal] = None  # Return on Equity
    
    # Risk Metrics
    risk_score: int  # 1-100
    risk_rating: str  # Excellent, Good, Fair, Poor
    probability_of_default: Decimal
    
    # Decision
    recommendation: str  # APPROVE, CONDITIONAL_APPROVE, DECLINE
    max_loan_amount: Decimal
    suggested_rate: Decimal
    required_conditions: List[str]
    
    # Flags and Warnings
    red_flags: List[str]
    yellow_flags: List[str]
    strengths: List[str]
    
    # Supporting Data
    calculations: Dict
    metadata: Dict


class UnderwritingEnginePro:
    """
    Enterprise-grade commercial loan underwriting engine
    Implements F500-level standards and best practices
    """
    
    # Industry standard thresholds
    MIN_DSCR = Decimal("1.25")
    MIN_DSCR_STRESSED = Decimal("1.15")
    MAX_LTV_OWNER_OCCUPIED = Decimal("0.80")
    MAX_LTV_INVESTMENT = Decimal("0.75")
    MIN_DEBT_YIELD = Decimal("0.10")  # 10%
    MIN_CREDIT_SCORE = 680
    MIN_LIQUIDITY_MONTHS = 6
    STRESS_TEST_RATE_INCREASE = Decimal("0.02")  # 2% rate increase
    
    def __init__(self):
        self.calculation_log = []
    
    def underwrite(
        self,
        loan_request: LoanRequest,
        borrower: BorrowerProfile,
        property_details: Optional[PropertyDetails] = None,
        financial_statements: Optional[List[FinancialStatement]] = None,
        existing_debt_service: Decimal = Decimal("0")
    ) -> UnderwritingResult:
        """
        Perform comprehensive underwriting analysis
        
        Args:
            loan_request: Loan request details
            borrower: Borrower profile
            property_details: Property information (for CRE loans)
            financial_statements: Historical financial statements
            existing_debt_service: Existing monthly debt obligations
            
        Returns:
            UnderwritingResult with complete analysis
        """
        self.calculation_log = []
        
        # Calculate monthly payment
        monthly_payment = self._calculate_monthly_payment(
            loan_request.loan_amount,
            loan_request.interest_rate,
            loan_request.amortization_months
        )
        
        # Calculate annual debt service
        annual_debt_service = monthly_payment * 12
        total_debt_service = annual_debt_service + (existing_debt_service * 12)
        
        # Calculate cash flows
        business_cash_flow = self._calculate_business_cash_flow(
            financial_statements
        ) if financial_statements else borrower.annual_revenue * Decimal("0.15")
        
        property_noi = None
        if property_details and property_details.net_operating_income:
            property_noi = property_details.net_operating_income
        
        global_cash_flow = business_cash_flow + (property_noi or Decimal("0"))
        
        # Calculate DSCR
        dscr = self._calculate_dscr(global_cash_flow, total_debt_service)
        
        # Calculate stressed DSCR (with 2% rate increase)
        stressed_rate = loan_request.interest_rate + self.STRESS_TEST_RATE_INCREASE
        stressed_payment = self._calculate_monthly_payment(
            loan_request.loan_amount,
            stressed_rate,
            loan_request.amortization_months
        )
        stressed_annual_ds = stressed_payment * 12 + (existing_debt_service * 12)
        dscr_stressed = self._calculate_dscr(global_cash_flow, stressed_annual_ds)
        
        # Calculate LTV
        property_value = property_details.appraised_value if property_details else loan_request.loan_amount / Decimal("0.75")
        ltv = loan_request.loan_amount / property_value
        
        # Calculate Debt Yield
        debt_yield = global_cash_flow / loan_request.loan_amount
        
        # Calculate financial ratios
        financial_ratios = self._calculate_financial_ratios(financial_statements)
        
        # Risk assessment
        risk_score, risk_rating, probability_of_default = self._assess_risk(
            dscr=dscr,
            ltv=ltv,
            debt_yield=debt_yield,
            credit_score=borrower.credit_score,
            years_in_business=borrower.years_in_business,
            financial_ratios=financial_ratios
        )
        
        # Identify flags
        red_flags, yellow_flags, strengths = self._identify_flags(
            dscr=dscr,
            dscr_stressed=dscr_stressed,
            ltv=ltv,
            debt_yield=debt_yield,
            credit_score=borrower.credit_score,
            loan_type=loan_request.loan_type,
            financial_ratios=financial_ratios
        )
        
        # Make recommendation
        recommendation, max_loan_amount, suggested_rate, conditions = self._make_recommendation(
            dscr=dscr,
            dscr_stressed=dscr_stressed,
            ltv=ltv,
            debt_yield=debt_yield,
            risk_score=risk_score,
            red_flags=red_flags,
            loan_request=loan_request,
            property_value=property_value,
            global_cash_flow=global_cash_flow
        )
        
        # Compile results
        return UnderwritingResult(
            dscr=dscr,
            dscr_stressed=dscr_stressed,
            ltv=ltv,
            debt_yield=debt_yield,
            global_cash_flow=global_cash_flow,
            business_cash_flow=business_cash_flow,
            property_noi=property_noi,
            total_debt_service=total_debt_service,
            monthly_payment=monthly_payment,
            current_ratio=financial_ratios.get("current_ratio"),
            quick_ratio=financial_ratios.get("quick_ratio"),
            debt_to_equity=financial_ratios.get("debt_to_equity"),
            profit_margin=financial_ratios.get("profit_margin"),
            roe=financial_ratios.get("roe"),
            risk_score=risk_score,
            risk_rating=risk_rating,
            probability_of_default=probability_of_default,
            recommendation=recommendation,
            max_loan_amount=max_loan_amount,
            suggested_rate=suggested_rate,
            required_conditions=conditions,
            red_flags=red_flags,
            yellow_flags=yellow_flags,
            strengths=strengths,
            calculations=self._get_calculation_details(),
            metadata={
                "underwriting_date": datetime.now().isoformat(),
                "engine_version": "2.0.0-pro",
                "calculation_log": self.calculation_log
            }
        )
    
    def _calculate_monthly_payment(
        self,
        principal: Decimal,
        annual_rate: Decimal,
        term_months: int
    ) -> Decimal:
        """Calculate monthly loan payment"""
        if annual_rate == 0:
            return principal / term_months
        
        monthly_rate = annual_rate / 12
        payment = principal * (
            monthly_rate * (1 + monthly_rate) ** term_months
        ) / (
            (1 + monthly_rate) ** term_months - 1
        )
        
        self.calculation_log.append({
            "step": "monthly_payment",
            "formula": "P * (r * (1+r)^n) / ((1+r)^n - 1)",
            "inputs": {
                "principal": float(principal),
                "annual_rate": float(annual_rate),
                "term_months": term_months
            },
            "result": float(payment)
        })
        
        return payment.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    
    def _calculate_business_cash_flow(
        self,
        financial_statements: List[FinancialStatement]
    ) -> Decimal:
        """Calculate normalized business cash flow"""
        if not financial_statements:
            return Decimal("0")
        
        # Use most recent statement
        latest = financial_statements[0]
        
        # Cash Flow = EBITDA - Taxes (estimated) - CapEx (estimated)
        # For simplicity, use Net Income + D&A as proxy
        cash_flow = latest.net_income + latest.depreciation + latest.amortization
        
        self.calculation_log.append({
            "step": "business_cash_flow",
            "formula": "Net Income + Depreciation + Amortization",
            "inputs": {
                "net_income": float(latest.net_income),
                "depreciation": float(latest.depreciation),
                "amortization": float(latest.amortization)
            },
            "result": float(cash_flow)
        })
        
        return cash_flow
    
    def _calculate_dscr(
        self,
        cash_flow: Decimal,
        debt_service: Decimal
    ) -> Decimal:
        """Calculate Debt Service Coverage Ratio"""
        if debt_service == 0:
            return Decimal("999")  # Effectively infinite
        
        dscr = cash_flow / debt_service
        
        self.calculation_log.append({
            "step": "dscr",
            "formula": "Cash Flow / Annual Debt Service",
            "inputs": {
                "cash_flow": float(cash_flow),
                "debt_service": float(debt_service)
            },
            "result": float(dscr)
        })
        
        return dscr.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    
    def _calculate_financial_ratios(
        self,
        financial_statements: Optional[List[FinancialStatement]]
    ) -> Dict:
        """Calculate comprehensive financial ratios"""
        if not financial_statements:
            return {}
        
        latest = financial_statements[0]
        ratios = {}
        
        # Current Ratio
        if latest.current_liabilities > 0:
            ratios["current_ratio"] = (
                latest.current_assets / latest.current_liabilities
            ).quantize(Decimal("0.01"))
        
        # Quick Ratio
        if latest.current_liabilities > 0:
            quick_assets = latest.current_assets - latest.inventory
            ratios["quick_ratio"] = (
                quick_assets / latest.current_liabilities
            ).quantize(Decimal("0.01"))
        
        # Debt to Equity
        equity = latest.total_assets - latest.total_liabilities
        if equity > 0:
            ratios["debt_to_equity"] = (
                latest.total_liabilities / equity
            ).quantize(Decimal("0.01"))
        
        # Profit Margin
        if latest.revenue > 0:
            ratios["profit_margin"] = (
                latest.net_income / latest.revenue
            ).quantize(Decimal("0.01"))
        
        # Return on Equity
        if equity > 0:
            ratios["roe"] = (
                latest.net_income / equity
            ).quantize(Decimal("0.01"))
        
        return ratios
    
    def _assess_risk(
        self,
        dscr: Decimal,
        ltv: Decimal,
        debt_yield: Decimal,
        credit_score: Optional[int],
        years_in_business: Optional[int],
        financial_ratios: Dict
    ) -> Tuple[int, str, Decimal]:
        """
        Assess overall risk and calculate probability of default
        Returns: (risk_score, risk_rating, probability_of_default)
        """
        score = 100  # Start at perfect score
        
        # DSCR impact (40 points)
        if dscr < Decimal("1.0"):
            score -= 40
        elif dscr < Decimal("1.15"):
            score -= 30
        elif dscr < Decimal("1.25"):
            score -= 15
        elif dscr < Decimal("1.35"):
            score -= 5
        
        # LTV impact (25 points)
        if ltv > Decimal("0.85"):
            score -= 25
        elif ltv > Decimal("0.80"):
            score -= 15
        elif ltv > Decimal("0.75"):
            score -= 8
        elif ltv > Decimal("0.70"):
            score -= 3
        
        # Credit score impact (20 points)
        if credit_score:
            if credit_score < 640:
                score -= 20
            elif credit_score < 680:
                score -= 15
            elif credit_score < 700:
                score -= 8
            elif credit_score < 720:
                score -= 3
        
        # Business tenure impact (10 points)
        if years_in_business:
            if years_in_business < 2:
                score -= 10
            elif years_in_business < 3:
                score -= 5
            elif years_in_business < 5:
                score -= 2
        
        # Financial ratios impact (5 points)
        if financial_ratios.get("current_ratio"):
            if financial_ratios["current_ratio"] < Decimal("1.0"):
                score -= 5
            elif financial_ratios["current_ratio"] < Decimal("1.5"):
                score -= 2
        
        # Ensure score is in valid range
        score = max(0, min(100, score))
        
        # Determine rating
        if score >= 85:
            rating = "Excellent"
            pod = Decimal("0.02")  # 2% default probability
        elif score >= 70:
            rating = "Good"
            pod = Decimal("0.05")  # 5% default probability
        elif score >= 55:
            rating = "Fair"
            pod = Decimal("0.12")  # 12% default probability
        else:
            rating = "Poor"
            pod = Decimal("0.25")  # 25% default probability
        
        return score, rating, pod
    
    def _identify_flags(
        self,
        dscr: Decimal,
        dscr_stressed: Decimal,
        ltv: Decimal,
        debt_yield: Decimal,
        credit_score: Optional[int],
        loan_type: str,
        financial_ratios: Dict
    ) -> Tuple[List[str], List[str], List[str]]:
        """Identify red flags, yellow flags, and strengths"""
        red_flags = []
        yellow_flags = []
        strengths = []
        
        # DSCR analysis
        if dscr < Decimal("1.0"):
            red_flags.append("DSCR below 1.0 - Insufficient cash flow to cover debt")
        elif dscr < Decimal("1.15"):
            red_flags.append("DSCR below 1.15 - Minimal coverage")
        elif dscr < Decimal("1.25"):
            yellow_flags.append("DSCR below industry standard of 1.25")
        elif dscr >= Decimal("1.50"):
            strengths.append(f"Strong DSCR of {dscr:.2f} - Excellent cash flow coverage")
        
        # Stressed DSCR
        if dscr_stressed < Decimal("1.0"):
            red_flags.append("Stressed DSCR below 1.0 - Cannot handle rate increases")
        elif dscr_stressed < Decimal("1.15"):
            yellow_flags.append("Stressed DSCR marginal - Limited buffer for rate increases")
        
        # LTV analysis
        max_ltv = self.MAX_LTV_OWNER_OCCUPIED if loan_type == "owner_occupied" else self.MAX_LTV_INVESTMENT
        if ltv > Decimal("0.85"):
            red_flags.append(f"LTV of {ltv:.1%} exceeds maximum acceptable level")
        elif ltv > max_ltv:
            yellow_flags.append(f"LTV of {ltv:.1%} exceeds standard maximum for {loan_type}")
        elif ltv <= Decimal("0.65"):
            strengths.append(f"Conservative LTV of {ltv:.1%} - Strong equity position")
        
        # Debt Yield
        if debt_yield < Decimal("0.08"):
            red_flags.append(f"Debt yield of {debt_yield:.1%} below minimum threshold")
        elif debt_yield < self.MIN_DEBT_YIELD:
            yellow_flags.append(f"Debt yield of {debt_yield:.1%} below standard minimum")
        elif debt_yield >= Decimal("0.15"):
            strengths.append(f"Strong debt yield of {debt_yield:.1%} - Excellent return on loan")
        
        # Credit score
        if credit_score:
            if credit_score < 640:
                red_flags.append(f"Credit score of {credit_score} below acceptable minimum")
            elif credit_score < self.MIN_CREDIT_SCORE:
                yellow_flags.append(f"Credit score of {credit_score} below standard minimum")
            elif credit_score >= 740:
                strengths.append(f"Excellent credit score of {credit_score}")
        
        # Financial ratios
        if financial_ratios.get("current_ratio"):
            if financial_ratios["current_ratio"] < Decimal("1.0"):
                red_flags.append("Current ratio below 1.0 - Liquidity concerns")
            elif financial_ratios["current_ratio"] < Decimal("1.5"):
                yellow_flags.append("Current ratio below 1.5 - Limited liquidity buffer")
            elif financial_ratios["current_ratio"] >= Decimal("2.0"):
                strengths.append(f"Strong current ratio of {financial_ratios['current_ratio']:.2f}")
        
        if financial_ratios.get("profit_margin"):
            if financial_ratios["profit_margin"] < Decimal("0.05"):
                yellow_flags.append("Profit margin below 5% - Thin margins")
            elif financial_ratios["profit_margin"] >= Decimal("0.15"):
                strengths.append(f"Strong profit margin of {financial_ratios['profit_margin']:.1%}")
        
        return red_flags, yellow_flags, strengths
    
    def _make_recommendation(
        self,
        dscr: Decimal,
        dscr_stressed: Decimal,
        ltv: Decimal,
        debt_yield: Decimal,
        risk_score: int,
        red_flags: List[str],
        loan_request: LoanRequest,
        property_value: Decimal,
        global_cash_flow: Decimal
    ) -> Tuple[str, Decimal, Decimal, List[str]]:
        """
        Make final underwriting recommendation
        Returns: (recommendation, max_loan_amount, suggested_rate, conditions)
        """
        conditions = []
        
        # Automatic decline conditions
        if len(red_flags) >= 3:
            return "DECLINE", Decimal("0"), loan_request.interest_rate, [
                "Multiple critical deficiencies identified",
                "Recommend restructuring loan request"
            ]
        
        if dscr < Decimal("1.0"):
            return "DECLINE", Decimal("0"), loan_request.interest_rate, [
                "Insufficient cash flow to support debt service",
                "Recommend reducing loan amount or increasing cash flow"
            ]
        
        # Calculate maximum supportable loan amount
        max_loan_by_dscr = (global_cash_flow / self.MIN_DSCR) / Decimal("0.12")  # Assuming 12% payment rate
        max_loan_by_ltv = property_value * self.MAX_LTV_OWNER_OCCUPIED
        max_loan_amount = min(max_loan_by_dscr, max_loan_by_ltv)
        
        # Risk-based pricing
        if risk_score >= 85:
            suggested_rate = loan_request.interest_rate - Decimal("0.0025")  # 25 bps discount
        elif risk_score >= 70:
            suggested_rate = loan_request.interest_rate
        elif risk_score >= 55:
            suggested_rate = loan_request.interest_rate + Decimal("0.005")  # 50 bps premium
        else:
            suggested_rate = loan_request.interest_rate + Decimal("0.01")  # 100 bps premium
        
        # Determine recommendation
        if risk_score >= 70 and dscr >= self.MIN_DSCR and dscr_stressed >= self.MIN_DSCR_STRESSED:
            if len(red_flags) == 0:
                return "APPROVE", loan_request.loan_amount, suggested_rate, conditions
            else:
                conditions.extend([
                    "Address identified red flags before closing",
                    "Provide additional documentation as requested"
                ])
                return "CONDITIONAL_APPROVE", loan_request.loan_amount, suggested_rate, conditions
        
        elif risk_score >= 55 and dscr >= Decimal("1.15"):
            conditions = [
                "Increase down payment to improve LTV" if ltv > Decimal("0.75") else "",
                "Provide personal guarantee",
                "Maintain minimum liquidity reserves of 6 months DSCR",
                "Quarterly financial reporting required",
                "Consider reducing loan amount to improve debt service coverage"
            ]
            conditions = [c for c in conditions if c]  # Remove empty strings
            
            # Suggest reduced loan amount
            recommended_amount = min(loan_request.loan_amount, max_loan_amount * Decimal("0.9"))
            return "CONDITIONAL_APPROVE", recommended_amount, suggested_rate, conditions
        
        else:
            return "DECLINE", Decimal("0"), suggested_rate, [
                "Risk profile exceeds acceptable thresholds",
                "Consider: (1) Increasing down payment, (2) Reducing loan amount, (3) Improving business cash flow",
                "Reapply after addressing identified deficiencies"
            ]
    
    def _get_calculation_details(self) -> Dict:
        """Get detailed calculation breakdown"""
        return {
            "calculation_steps": len(self.calculation_log),
            "formulas_used": [step["formula"] for step in self.calculation_log],
            "detailed_log": self.calculation_log
        }
