"""
Financial Analysis Engine
The heart of UnderwritePro's automated underwriting
Calculates DSCR, LTV, DTI, Cap Rate, and 20+ financial ratios
"""

from decimal import Decimal, ROUND_HALF_UP
from typing import Optional, Dict, Tuple
from sqlalchemy.orm import Session
from uuid import UUID

from models.loan import LoanApplication
from models.borrower import Borrower
from models.guarantor import Guarantor
from models.property import Property, PropertyFinancials
from models.financial import FinancialStatement, FinancialRatios


class FinancialAnalysisEngine:
    """
    Automated financial analysis and ratio calculation engine
    """
    
    # ========================================================================
    # DSCR Calculations
    # ========================================================================
    
    @staticmethod
    def calculate_global_dscr(
        business_net_income: Decimal,
        personal_income: Decimal,
        existing_debt_payments: Decimal,
        proposed_debt_payment: Decimal,
        rent_savings: Decimal = Decimal('0')
    ) -> Optional[Decimal]:
        """
        Calculate Global DSCR (for owner-occupied properties)
        
        Formula: (Business Net Income + Personal Income + Rent Savings) / 
                 (Existing Debt Payments + Proposed Debt Payment)
        
        This method combines business and personal cash flow to assess
        total debt service coverage capability.
        """
        if not all([business_net_income is not None, personal_income is not None]):
            return None
        
        total_debt_payments = (existing_debt_payments or Decimal('0')) + (proposed_debt_payment or Decimal('0'))
        
        if total_debt_payments <= 0:
            return None
        
        total_income = (business_net_income or Decimal('0')) + \
                      (personal_income or Decimal('0')) + \
                      (rent_savings or Decimal('0'))
        
        dscr = total_income / total_debt_payments
        return dscr.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
    
    @staticmethod
    def calculate_business_dscr(
        ebitda: Decimal,
        existing_debt_payments: Decimal,
        proposed_debt_payment: Decimal
    ) -> Optional[Decimal]:
        """
        Calculate Business DSCR
        
        Formula: EBITDA / (Existing Debt Payments + Proposed Debt Payment)
        
        Measures business cash flow's ability to service debt.
        """
        if ebitda is None:
            return None
        
        total_debt_payments = (existing_debt_payments or Decimal('0')) + (proposed_debt_payment or Decimal('0'))
        
        if total_debt_payments <= 0:
            return None
        
        dscr = ebitda / total_debt_payments
        return dscr.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
    
    @staticmethod
    def calculate_property_dscr(
        noi: Decimal,
        proposed_debt_payment: Decimal
    ) -> Optional[Decimal]:
        """
        Calculate Property DSCR (for investment properties)
        
        Formula: NOI / Proposed Debt Payment
        
        Measures property cash flow's ability to service debt.
        This is the primary metric for non-owner-occupied properties.
        """
        if noi is None or proposed_debt_payment is None or proposed_debt_payment <= 0:
            return None
        
        dscr = noi / proposed_debt_payment
        return dscr.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
    
    @staticmethod
    def calculate_personal_dscr(
        personal_income: Decimal,
        monthly_debt_payments: Decimal,
        proposed_debt_payment: Decimal
    ) -> Optional[Decimal]:
        """
        Calculate Personal DSCR
        
        Formula: Personal Income / (Monthly Debt Payments + Proposed Debt Payment)
        
        Measures guarantor's personal ability to service debt.
        """
        if personal_income is None:
            return None
        
        total_debt_payments = (monthly_debt_payments or Decimal('0')) + (proposed_debt_payment or Decimal('0'))
        
        if total_debt_payments <= 0:
            return None
        
        # Convert annual income to monthly if needed
        monthly_income = personal_income / 12 if personal_income > 100000 else personal_income
        
        dscr = monthly_income / total_debt_payments
        return dscr.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
    
    # ========================================================================
    # Leverage Ratios
    # ========================================================================
    
    @staticmethod
    def calculate_ltv(
        loan_amount: Decimal,
        property_value: Decimal
    ) -> Optional[Decimal]:
        """
        Calculate Loan-to-Value (LTV)
        
        Formula: (Loan Amount / Property Value) * 100
        
        Key underwriting metric. Typical max:
        - Owner-occupied: 75-80%
        - Investment: 70-75%
        """
        if not all([loan_amount, property_value]) or property_value <= 0:
            return None
        
        ltv = (loan_amount / property_value) * 100
        return ltv.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
    
    @staticmethod
    def calculate_ltc(
        loan_amount: Decimal,
        total_project_cost: Decimal
    ) -> Optional[Decimal]:
        """
        Calculate Loan-to-Cost (LTC)
        
        Formula: (Loan Amount / Total Project Cost) * 100
        
        Used for construction and development loans.
        """
        if not all([loan_amount, total_project_cost]) or total_project_cost <= 0:
            return None
        
        ltc = (loan_amount / total_project_cost) * 100
        return ltc.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
    
    @staticmethod
    def calculate_dti(
        total_monthly_debt: Decimal,
        gross_monthly_income: Decimal
    ) -> Optional[Decimal]:
        """
        Calculate Debt-to-Income (DTI)
        
        Formula: (Total Monthly Debt / Gross Monthly Income) * 100
        
        Typical max: 43-50%
        """
        if not all([total_monthly_debt, gross_monthly_income]) or gross_monthly_income <= 0:
            return None
        
        dti = (total_monthly_debt / gross_monthly_income) * 100
        return dti.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
    
    @staticmethod
    def calculate_debt_to_ebitda(
        total_debt: Decimal,
        ebitda: Decimal
    ) -> Optional[Decimal]:
        """
        Calculate Debt-to-EBITDA
        
        Formula: Total Debt / EBITDA
        
        Measures leverage. Typical max: 3.0-4.0x
        """
        if not all([total_debt, ebitda]) or ebitda <= 0:
            return None
        
        ratio = total_debt / ebitda
        return ratio.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
    
    # ========================================================================
    # Liquidity Ratios
    # ========================================================================
    
    @staticmethod
    def calculate_current_ratio(
        current_assets: Decimal,
        current_liabilities: Decimal
    ) -> Optional[Decimal]:
        """
        Calculate Current Ratio
        
        Formula: Current Assets / Current Liabilities
        
        Measures short-term liquidity. Healthy: > 1.5
        """
        if not all([current_assets, current_liabilities]) or current_liabilities <= 0:
            return None
        
        ratio = current_assets / current_liabilities
        return ratio.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
    
    @staticmethod
    def calculate_quick_ratio(
        current_assets: Decimal,
        inventory: Decimal,
        current_liabilities: Decimal
    ) -> Optional[Decimal]:
        """
        Calculate Quick Ratio (Acid Test)
        
        Formula: (Current Assets - Inventory) / Current Liabilities
        
        Stricter liquidity measure. Healthy: > 1.0
        """
        if not all([current_assets, current_liabilities]) or current_liabilities <= 0:
            return None
        
        quick_assets = current_assets - (inventory or Decimal('0'))
        ratio = quick_assets / current_liabilities
        return ratio.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
    
    @staticmethod
    def calculate_cash_ratio(
        cash: Decimal,
        current_liabilities: Decimal
    ) -> Optional[Decimal]:
        """
        Calculate Cash Ratio
        
        Formula: Cash / Current Liabilities
        
        Most conservative liquidity measure.
        """
        if not all([cash, current_liabilities]) or current_liabilities <= 0:
            return None
        
        ratio = cash / current_liabilities
        return ratio.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
    
    # ========================================================================
    # Profitability Ratios
    # ========================================================================
    
    @staticmethod
    def calculate_gross_margin(
        gross_profit: Decimal,
        revenue: Decimal
    ) -> Optional[Decimal]:
        """
        Calculate Gross Margin
        
        Formula: (Gross Profit / Revenue) * 100
        """
        if not all([gross_profit, revenue]) or revenue <= 0:
            return None
        
        margin = (gross_profit / revenue) * 100
        return margin.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
    
    @staticmethod
    def calculate_operating_margin(
        operating_income: Decimal,
        revenue: Decimal
    ) -> Optional[Decimal]:
        """
        Calculate Operating Margin
        
        Formula: (Operating Income / Revenue) * 100
        """
        if not all([operating_income, revenue]) or revenue <= 0:
            return None
        
        margin = (operating_income / revenue) * 100
        return margin.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
    
    @staticmethod
    def calculate_net_margin(
        net_income: Decimal,
        revenue: Decimal
    ) -> Optional[Decimal]:
        """
        Calculate Net Margin
        
        Formula: (Net Income / Revenue) * 100
        """
        if not all([net_income, revenue]) or revenue <= 0:
            return None
        
        margin = (net_income / revenue) * 100
        return margin.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
    
    @staticmethod
    def calculate_ebitda_margin(
        ebitda: Decimal,
        revenue: Decimal
    ) -> Optional[Decimal]:
        """
        Calculate EBITDA Margin
        
        Formula: (EBITDA / Revenue) * 100
        """
        if not all([ebitda, revenue]) or revenue <= 0:
            return None
        
        margin = (ebitda / revenue) * 100
        return margin.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
    
    @staticmethod
    def calculate_roa(
        net_income: Decimal,
        total_assets: Decimal
    ) -> Optional[Decimal]:
        """
        Calculate Return on Assets (ROA)
        
        Formula: (Net Income / Total Assets) * 100
        """
        if not all([net_income, total_assets]) or total_assets <= 0:
            return None
        
        roa = (net_income / total_assets) * 100
        return roa.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
    
    @staticmethod
    def calculate_roe(
        net_income: Decimal,
        shareholders_equity: Decimal
    ) -> Optional[Decimal]:
        """
        Calculate Return on Equity (ROE)
        
        Formula: (Net Income / Shareholders Equity) * 100
        """
        if not all([net_income, shareholders_equity]) or shareholders_equity <= 0:
            return None
        
        roe = (net_income / shareholders_equity) * 100
        return roe.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
    
    # ========================================================================
    # Investment Property Ratios
    # ========================================================================
    
    @staticmethod
    def calculate_cap_rate(
        noi: Decimal,
        property_value: Decimal
    ) -> Optional[Decimal]:
        """
        Calculate Capitalization Rate (Cap Rate)
        
        Formula: (NOI / Property Value) * 100
        
        Key metric for investment properties.
        Higher cap rate = higher return (and typically higher risk)
        """
        if not all([noi, property_value]) or property_value <= 0:
            return None
        
        cap_rate = (noi / property_value) * 100
        return cap_rate.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
    
    @staticmethod
    def calculate_debt_yield(
        noi: Decimal,
        loan_amount: Decimal
    ) -> Optional[Decimal]:
        """
        Calculate Debt Yield
        
        Formula: (NOI / Loan Amount) * 100
        
        Lender's risk metric. Typical min: 10-12%
        """
        if not all([noi, loan_amount]) or loan_amount <= 0:
            return None
        
        debt_yield = (noi / loan_amount) * 100
        return debt_yield.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
    
    @staticmethod
    def calculate_cash_on_cash_return(
        annual_cash_flow: Decimal,
        equity_invested: Decimal
    ) -> Optional[Decimal]:
        """
        Calculate Cash-on-Cash Return
        
        Formula: (Annual Cash Flow / Equity Invested) * 100
        """
        if not all([annual_cash_flow, equity_invested]) or equity_invested <= 0:
            return None
        
        return_rate = (annual_cash_flow / equity_invested) * 100
        return return_rate.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
    
    @staticmethod
    def calculate_break_even_occupancy(
        operating_expenses: Decimal,
        debt_service: Decimal,
        gross_potential_rent: Decimal
    ) -> Optional[Decimal]:
        """
        Calculate Break-Even Occupancy
        
        Formula: ((Operating Expenses + Debt Service) / Gross Potential Rent) * 100
        
        Shows minimum occupancy needed to cover expenses.
        """
        if not all([operating_expenses, debt_service, gross_potential_rent]) or gross_potential_rent <= 0:
            return None
        
        beo = ((operating_expenses + debt_service) / gross_potential_rent) * 100
        return beo.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
    
    @staticmethod
    def calculate_operating_expense_ratio(
        operating_expenses: Decimal,
        effective_gross_income: Decimal
    ) -> Optional[Decimal]:
        """
        Calculate Operating Expense Ratio
        
        Formula: (Operating Expenses / Effective Gross Income) * 100
        
        Measures operating efficiency.
        """
        if not all([operating_expenses, effective_gross_income]) or effective_gross_income <= 0:
            return None
        
        oer = (operating_expenses / effective_gross_income) * 100
        return oer.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
    
    # ========================================================================
    # Comprehensive Analysis
    # ========================================================================
    
    @staticmethod
    def analyze_loan_application(
        db: Session,
        loan_id: UUID
    ) -> FinancialRatios:
        """
        Perform comprehensive financial analysis on a loan application
        
        This is the main entry point that calculates all ratios and
        saves them to the database.
        """
        # Get loan application with all related data
        loan = db.query(LoanApplication).filter(LoanApplication.id == loan_id).first()
        
        if not loan:
            raise ValueError("Loan application not found")
        
        # Get related entities
        borrower = loan.borrower
        guarantor = loan.guarantors[0] if loan.guarantors else None
        property_info = loan.property_info
        property_financials = property_info.financials[0] if property_info and property_info.financials else None
        financial_statement = loan.financial_statements[0] if loan.financial_statements else None
        
        # Calculate proposed debt payment (monthly)
        proposed_payment = FinancialAnalysisEngine._calculate_monthly_payment(
            loan.loan_amount,
            loan.requested_rate or Decimal('7.5'),
            loan.requested_term or 120
        )
        
        # Initialize ratios object
        ratios = FinancialRatios(loan_application_id=loan_id)
        
        # Determine calculation method based on loan type
        is_owner_occupied = loan.loan_type.value == 'owner_occupied_cre'
        is_investment = loan.loan_type.value in ['investment_property', 'multi_family']
        
        # Calculate DSCR ratios
        if is_owner_occupied and financial_statement and guarantor:
            # Global DSCR for owner-occupied
            ratios.global_dscr = FinancialAnalysisEngine.calculate_global_dscr(
                business_net_income=financial_statement.net_income or Decimal('0'),
                personal_income=guarantor.annual_income or Decimal('0'),
                existing_debt_payments=Decimal('0'),  # Would come from credit report
                proposed_debt_payment=proposed_payment
            )
            ratios.calculation_method = "global_dscr"
        
        if is_investment and property_financials:
            # Property DSCR for investment properties
            ratios.property_dscr = FinancialAnalysisEngine.calculate_property_dscr(
                noi=property_financials.net_operating_income or Decimal('0'),
                proposed_debt_payment=proposed_payment
            )
            ratios.calculation_method = "property_noi"
        
        if financial_statement:
            # Business DSCR
            ratios.business_dscr = FinancialAnalysisEngine.calculate_business_dscr(
                ebitda=financial_statement.ebitda or Decimal('0'),
                existing_debt_payments=Decimal('0'),
                proposed_debt_payment=proposed_payment
            )
        
        # Calculate LTV
        if property_info:
            property_value = property_info.appraised_value or property_info.purchase_price
            if property_value:
                ratios.ltv = FinancialAnalysisEngine.calculate_ltv(
                    loan.loan_amount,
                    property_value
                )
        
        # Calculate other ratios if financial statement exists
        if financial_statement:
            ratios.gross_margin = FinancialAnalysisEngine.calculate_gross_margin(
                financial_statement.gross_profit,
                financial_statement.revenue
            )
            ratios.operating_margin = FinancialAnalysisEngine.calculate_operating_margin(
                financial_statement.ebitda,
                financial_statement.revenue
            )
            ratios.net_margin = FinancialAnalysisEngine.calculate_net_margin(
                financial_statement.net_income,
                financial_statement.revenue
            )
            ratios.ebitda_margin = FinancialAnalysisEngine.calculate_ebitda_margin(
                financial_statement.ebitda,
                financial_statement.revenue
            )
            ratios.current_ratio = FinancialAnalysisEngine.calculate_current_ratio(
                financial_statement.total_current_assets,
                financial_statement.total_current_liabilities
            )
            ratios.quick_ratio = FinancialAnalysisEngine.calculate_quick_ratio(
                financial_statement.total_current_assets,
                financial_statement.inventory,
                financial_statement.total_current_liabilities
            )
            ratios.roa = FinancialAnalysisEngine.calculate_roa(
                financial_statement.net_income,
                financial_statement.total_assets
            )
            ratios.roe = FinancialAnalysisEngine.calculate_roe(
                financial_statement.net_income,
                financial_statement.shareholders_equity
            )
        
        # Calculate investment property ratios
        if property_financials and property_info:
            ratios.cap_rate = FinancialAnalysisEngine.calculate_cap_rate(
                property_financials.net_operating_income,
                property_info.appraised_value or property_info.purchase_price
            )
            ratios.debt_yield = FinancialAnalysisEngine.calculate_debt_yield(
                property_financials.net_operating_income,
                loan.loan_amount
            )
            ratios.operating_expense_ratio = FinancialAnalysisEngine.calculate_operating_expense_ratio(
                property_financials.total_operating_expenses,
                property_financials.effective_gross_income
            )
        
        # Save to database
        db.add(ratios)
        db.commit()
        db.refresh(ratios)
        
        return ratios
    
    @staticmethod
    def _calculate_monthly_payment(
        principal: Decimal,
        annual_rate: Decimal,
        term_months: int
    ) -> Decimal:
        """
        Calculate monthly payment using standard amortization formula
        
        Formula: P * [r(1+r)^n] / [(1+r)^n - 1]
        where:
        P = principal
        r = monthly interest rate
        n = number of payments
        """
        if annual_rate <= 0:
            return principal / term_months
        
        monthly_rate = (annual_rate / 100) / 12
        
        # Convert to float for calculation, then back to Decimal
        r = float(monthly_rate)
        n = term_months
        p = float(principal)
        
        payment = p * (r * (1 + r)**n) / ((1 + r)**n - 1)
        
        return Decimal(str(payment)).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
