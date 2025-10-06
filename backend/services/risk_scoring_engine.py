"""
Risk Scoring Engine
Automated risk assessment and underwriting decision engine
"""

from decimal import Decimal
from typing import Optional, Dict, List, Tuple
from sqlalchemy.orm import Session
from uuid import UUID
from datetime import datetime

from models.loan import LoanApplication
from models.financial import RiskAssessment, FinancialRatios
from models.borrower import Borrower, Guarantor


class RiskScoringEngine:
    """
    Automated risk scoring and underwriting decision engine
    
    Scoring Scale: 0-100 (higher is better)
    - 90-100: Exceptional
    - 80-89: Good
    - 70-79: Acceptable
    - 60-69: Marginal
    - 0-59: Unacceptable
    """
    
    # Risk rating thresholds
    RISK_RATINGS = {
        'exceptional': (90, 100),
        'good': (80, 89),
        'acceptable': (70, 79),
        'marginal': (60, 69),
        'unacceptable': (0, 59)
    }
    
    # Component weights (must sum to 100)
    WEIGHTS = {
        'dscr': 25,          # Debt Service Coverage Ratio
        'credit': 20,        # Credit Score
        'ltv': 20,           # Loan-to-Value
        'tenure': 10,        # Years in Business / Time in Operation
        'profitability': 10, # Profit Margins
        'liquidity': 10,     # Liquidity Ratios
        'industry': 5        # Industry Risk
    }
    
    # ========================================================================
    # Component Scoring Methods
    # ========================================================================
    
    @staticmethod
    def score_dscr(dscr: Optional[Decimal], is_owner_occupied: bool = False) -> int:
        """
        Score DSCR (0-100)
        
        Owner-Occupied Benchmarks:
        - ≥ 1.50: 100 (Exceptional)
        - 1.40-1.49: 90 (Excellent)
        - 1.30-1.39: 80 (Good)
        - 1.25-1.29: 70 (Acceptable - typical minimum)
        - 1.20-1.24: 60 (Marginal)
        - 1.15-1.19: 50 (Weak)
        - < 1.15: 0-40 (Unacceptable)
        
        Investment Property Benchmarks:
        - ≥ 1.40: 100
        - 1.30-1.39: 90
        - 1.25-1.29: 80
        - 1.20-1.24: 70 (typical minimum)
        - 1.15-1.19: 60
        - 1.10-1.14: 50
        - < 1.10: 0-40
        """
        if dscr is None or dscr <= 0:
            return 0
        
        # Adjust thresholds based on property type
        if is_owner_occupied:
            if dscr >= Decimal('1.50'):
                return 100
            elif dscr >= Decimal('1.40'):
                return 90
            elif dscr >= Decimal('1.30'):
                return 80
            elif dscr >= Decimal('1.25'):
                return 70
            elif dscr >= Decimal('1.20'):
                return 60
            elif dscr >= Decimal('1.15'):
                return 50
            elif dscr >= Decimal('1.10'):
                return 40
            elif dscr >= Decimal('1.00'):
                return 20
            else:
                return 0
        else:
            # Investment property
            if dscr >= Decimal('1.40'):
                return 100
            elif dscr >= Decimal('1.30'):
                return 90
            elif dscr >= Decimal('1.25'):
                return 80
            elif dscr >= Decimal('1.20'):
                return 70
            elif dscr >= Decimal('1.15'):
                return 60
            elif dscr >= Decimal('1.10'):
                return 50
            elif dscr >= Decimal('1.00'):
                return 30
            else:
                return 0
    
    @staticmethod
    def score_credit(
        business_credit: Optional[int],
        personal_credit: Optional[int],
        weight_business: float = 0.6,
        weight_personal: float = 0.4
    ) -> int:
        """
        Score Credit (0-100)
        
        Business Credit (Paydex/Experian):
        - 80-100: Excellent (100 points)
        - 70-79: Good (85 points)
        - 60-69: Fair (70 points)
        - 50-59: Poor (50 points)
        - < 50: Very Poor (25 points)
        
        Personal Credit (FICO):
        - 740+: Excellent (100 points)
        - 700-739: Good (85 points)
        - 660-699: Fair (70 points)
        - 620-659: Poor (50 points)
        - < 620: Very Poor (25 points)
        """
        business_score = 0
        personal_score = 0
        
        # Score business credit
        if business_credit is not None:
            if business_credit >= 80:
                business_score = 100
            elif business_credit >= 70:
                business_score = 85
            elif business_credit >= 60:
                business_score = 70
            elif business_credit >= 50:
                business_score = 50
            else:
                business_score = 25
        
        # Score personal credit
        if personal_credit is not None:
            if personal_credit >= 740:
                personal_score = 100
            elif personal_credit >= 700:
                personal_score = 85
            elif personal_credit >= 660:
                personal_score = 70
            elif personal_credit >= 620:
                personal_score = 50
            else:
                personal_score = 25
        
        # Weighted average
        if business_credit is not None and personal_credit is not None:
            return int(business_score * weight_business + personal_score * weight_personal)
        elif business_credit is not None:
            return business_score
        elif personal_credit is not None:
            return personal_score
        else:
            return 50  # Neutral if no credit data
    
    @staticmethod
    def score_ltv(ltv: Optional[Decimal], is_owner_occupied: bool = False) -> int:
        """
        Score LTV (0-100)
        
        Owner-Occupied:
        - ≤ 65%: 100 (Excellent)
        - 66-70%: 90 (Very Good)
        - 71-75%: 80 (Good)
        - 76-80%: 70 (Acceptable - typical max)
        - 81-85%: 50 (High risk)
        - > 85%: 25 (Very high risk)
        
        Investment Property:
        - ≤ 60%: 100
        - 61-65%: 90
        - 66-70%: 80
        - 71-75%: 70 (typical max)
        - 76-80%: 50
        - > 80%: 25
        """
        if ltv is None or ltv <= 0:
            return 0
        
        if is_owner_occupied:
            if ltv <= 65:
                return 100
            elif ltv <= 70:
                return 90
            elif ltv <= 75:
                return 80
            elif ltv <= 80:
                return 70
            elif ltv <= 85:
                return 50
            else:
                return 25
        else:
            # Investment property
            if ltv <= 60:
                return 100
            elif ltv <= 65:
                return 90
            elif ltv <= 70:
                return 80
            elif ltv <= 75:
                return 70
            elif ltv <= 80:
                return 50
            else:
                return 25
    
    @staticmethod
    def score_tenure(years_in_business: Optional[Decimal]) -> int:
        """
        Score Years in Business / Tenure (0-100)
        
        - ≥ 10 years: 100 (Well-established)
        - 7-9 years: 90 (Established)
        - 5-6 years: 80 (Mature)
        - 3-4 years: 70 (Developing)
        - 2 years: 60 (Young)
        - 1 year: 40 (Startup)
        - < 1 year: 20 (Very new)
        """
        if years_in_business is None or years_in_business < 0:
            return 50  # Neutral if unknown
        
        if years_in_business >= 10:
            return 100
        elif years_in_business >= 7:
            return 90
        elif years_in_business >= 5:
            return 80
        elif years_in_business >= 3:
            return 70
        elif years_in_business >= 2:
            return 60
        elif years_in_business >= 1:
            return 40
        else:
            return 20
    
    @staticmethod
    def score_profitability(
        net_margin: Optional[Decimal],
        ebitda_margin: Optional[Decimal]
    ) -> int:
        """
        Score Profitability (0-100)
        
        Based on Net Margin and EBITDA Margin
        
        Net Margin:
        - ≥ 15%: Excellent (100)
        - 10-14%: Good (85)
        - 5-9%: Fair (70)
        - 2-4%: Marginal (50)
        - < 2%: Poor (25)
        
        EBITDA Margin:
        - ≥ 20%: Excellent (100)
        - 15-19%: Good (85)
        - 10-14%: Fair (70)
        - 5-9%: Marginal (50)
        - < 5%: Poor (25)
        """
        net_score = 50  # Default neutral
        ebitda_score = 50
        
        if net_margin is not None:
            if net_margin >= 15:
                net_score = 100
            elif net_margin >= 10:
                net_score = 85
            elif net_margin >= 5:
                net_score = 70
            elif net_margin >= 2:
                net_score = 50
            else:
                net_score = 25
        
        if ebitda_margin is not None:
            if ebitda_margin >= 20:
                ebitda_score = 100
            elif ebitda_margin >= 15:
                ebitda_score = 85
            elif ebitda_margin >= 10:
                ebitda_score = 70
            elif ebitda_margin >= 5:
                ebitda_score = 50
            else:
                ebitda_score = 25
        
        # Average of both margins
        return int((net_score + ebitda_score) / 2)
    
    @staticmethod
    def score_liquidity(
        current_ratio: Optional[Decimal],
        quick_ratio: Optional[Decimal]
    ) -> int:
        """
        Score Liquidity (0-100)
        
        Current Ratio:
        - ≥ 2.0: Excellent (100)
        - 1.5-1.9: Good (85)
        - 1.2-1.4: Fair (70)
        - 1.0-1.1: Marginal (50)
        - < 1.0: Poor (25)
        
        Quick Ratio:
        - ≥ 1.5: Excellent (100)
        - 1.2-1.4: Good (85)
        - 1.0-1.1: Fair (70)
        - 0.8-0.9: Marginal (50)
        - < 0.8: Poor (25)
        """
        current_score = 50
        quick_score = 50
        
        if current_ratio is not None:
            if current_ratio >= 2.0:
                current_score = 100
            elif current_ratio >= 1.5:
                current_score = 85
            elif current_ratio >= 1.2:
                current_score = 70
            elif current_ratio >= 1.0:
                current_score = 50
            else:
                current_score = 25
        
        if quick_ratio is not None:
            if quick_ratio >= 1.5:
                quick_score = 100
            elif quick_ratio >= 1.2:
                quick_score = 85
            elif quick_ratio >= 1.0:
                quick_score = 70
            elif quick_ratio >= 0.8:
                quick_score = 50
            else:
                quick_score = 25
        
        return int((current_score + quick_score) / 2)
    
    @staticmethod
    def score_industry(industry: Optional[str]) -> int:
        """
        Score Industry Risk (0-100)
        
        This is a simplified version. In production, this would use
        industry-specific risk ratings from RMA, BizStats, or proprietary data.
        
        Low Risk Industries (90-100):
        - Healthcare, Professional Services, Technology
        
        Medium Risk Industries (70-89):
        - Manufacturing, Wholesale, Real Estate
        
        Higher Risk Industries (50-69):
        - Retail, Hospitality, Construction
        
        High Risk Industries (30-49):
        - Restaurants, Bars, Entertainment
        """
        if not industry:
            return 70  # Neutral default
        
        industry_lower = industry.lower()
        
        # Low risk
        if any(x in industry_lower for x in ['healthcare', 'medical', 'professional services', 
                                               'technology', 'software', 'consulting', 'accounting']):
            return 95
        
        # Medium risk
        elif any(x in industry_lower for x in ['manufacturing', 'wholesale', 'real estate',
                                                 'distribution', 'logistics']):
            return 80
        
        # Higher risk
        elif any(x in industry_lower for x in ['retail', 'hospitality', 'construction',
                                                 'automotive']):
            return 60
        
        # High risk
        elif any(x in industry_lower for x in ['restaurant', 'bar', 'entertainment',
                                                 'nightclub', 'gaming']):
            return 40
        
        else:
            return 70  # Default neutral
    
    # ========================================================================
    # Overall Risk Assessment
    # ========================================================================
    
    @staticmethod
    def calculate_overall_score(component_scores: Dict[str, int]) -> int:
        """
        Calculate weighted overall risk score
        
        Formula: Σ (component_score × weight) / 100
        """
        total_score = 0
        
        for component, weight in RiskScoringEngine.WEIGHTS.items():
            score = component_scores.get(component, 50)  # Default to neutral if missing
            total_score += score * (weight / 100)
        
        return int(total_score)
    
    @staticmethod
    def get_risk_rating(overall_score: int) -> str:
        """
        Get risk rating based on overall score
        """
        for rating, (min_score, max_score) in RiskScoringEngine.RISK_RATINGS.items():
            if min_score <= overall_score <= max_score:
                return rating
        return 'unacceptable'
    
    @staticmethod
    def identify_risk_factors(
        component_scores: Dict[str, int],
        ratios: FinancialRatios,
        borrower: Optional[Borrower] = None
    ) -> List[str]:
        """
        Identify specific risk factors based on scores
        """
        risk_factors = []
        
        # DSCR risks
        if component_scores.get('dscr', 100) < 70:
            dscr = ratios.global_dscr or ratios.property_dscr or ratios.business_dscr
            if dscr and dscr < Decimal('1.25'):
                risk_factors.append(f"Low DSCR ({dscr:.2f}x) - below typical minimum of 1.25x")
        
        # Credit risks
        if component_scores.get('credit', 100) < 70:
            risk_factors.append("Credit score below acceptable thresholds")
        
        # LTV risks
        if component_scores.get('ltv', 100) < 70:
            if ratios.ltv and ratios.ltv > 75:
                risk_factors.append(f"High LTV ({ratios.ltv:.1f}%) - above typical maximum")
        
        # Tenure risks
        if component_scores.get('tenure', 100) < 70:
            if borrower and borrower.years_in_business and borrower.years_in_business < 3:
                risk_factors.append(f"Limited operating history ({borrower.years_in_business:.1f} years)")
        
        # Profitability risks
        if component_scores.get('profitability', 100) < 70:
            risk_factors.append("Weak profitability margins")
        
        # Liquidity risks
        if component_scores.get('liquidity', 100) < 70:
            if ratios.current_ratio and ratios.current_ratio < Decimal('1.2'):
                risk_factors.append(f"Low liquidity (Current Ratio: {ratios.current_ratio:.2f})")
        
        # Industry risks
        if component_scores.get('industry', 100) < 60:
            risk_factors.append("Higher-risk industry sector")
        
        return risk_factors
    
    @staticmethod
    def identify_mitigating_factors(
        component_scores: Dict[str, int],
        ratios: FinancialRatios,
        borrower: Optional[Borrower] = None,
        guarantor: Optional[Guarantor] = None
    ) -> List[str]:
        """
        Identify mitigating factors that reduce risk
        """
        mitigating_factors = []
        
        # Strong DSCR
        if component_scores.get('dscr', 0) >= 90:
            mitigating_factors.append("Strong debt service coverage")
        
        # Excellent credit
        if component_scores.get('credit', 0) >= 90:
            mitigating_factors.append("Excellent credit profile")
        
        # Low LTV
        if component_scores.get('ltv', 0) >= 90:
            if ratios.ltv and ratios.ltv <= 65:
                mitigating_factors.append(f"Conservative LTV ({ratios.ltv:.1f}%)")
        
        # Established business
        if component_scores.get('tenure', 0) >= 90:
            mitigating_factors.append("Well-established business with long operating history")
        
        # Strong profitability
        if component_scores.get('profitability', 0) >= 85:
            mitigating_factors.append("Strong profitability and margins")
        
        # Strong liquidity
        if component_scores.get('liquidity', 0) >= 85:
            mitigating_factors.append("Strong liquidity position")
        
        # Strong guarantor
        if guarantor:
            if guarantor.net_worth and guarantor.net_worth > 1000000:
                mitigating_factors.append(f"Strong guarantor net worth (${guarantor.net_worth:,.0f})")
            if guarantor.liquid_assets and guarantor.liquid_assets > 500000:
                mitigating_factors.append(f"Substantial liquid assets (${guarantor.liquid_assets:,.0f})")
        
        return mitigating_factors
    
    # ========================================================================
    # Main Assessment Function
    # ========================================================================
    
    @staticmethod
    def assess_loan_application(
        db: Session,
        loan_id: UUID
    ) -> RiskAssessment:
        """
        Perform comprehensive risk assessment on a loan application
        
        This is the main entry point that:
        1. Retrieves loan and related data
        2. Calculates component scores
        3. Calculates overall score
        4. Determines risk rating
        5. Identifies risk and mitigating factors
        6. Makes automated decision
        7. Saves assessment to database
        """
        # Get loan application with all related data
        loan = db.query(LoanApplication).filter(LoanApplication.id == loan_id).first()
        
        if not loan:
            raise ValueError("Loan application not found")
        
        # Get related entities
        borrower = loan.borrower
        guarantor = loan.guarantors[0] if loan.guarantors else None
        ratios = loan.financial_ratios
        
        if not ratios:
            raise ValueError("Financial ratios must be calculated before risk assessment")
        
        # Determine if owner-occupied
        is_owner_occupied = loan.loan_type.value == 'owner_occupied_cre'
        
        # Calculate component scores
        component_scores = {}
        
        # DSCR score
        primary_dscr = ratios.global_dscr if is_owner_occupied else ratios.property_dscr
        if not primary_dscr:
            primary_dscr = ratios.business_dscr
        component_scores['dscr'] = RiskScoringEngine.score_dscr(primary_dscr, is_owner_occupied)
        
        # Credit score
        business_credit = borrower.business_credit_score if borrower else None
        personal_credit = guarantor.credit_score if guarantor else None
        component_scores['credit'] = RiskScoringEngine.score_credit(business_credit, personal_credit)
        
        # LTV score
        component_scores['ltv'] = RiskScoringEngine.score_ltv(ratios.ltv, is_owner_occupied)
        
        # Tenure score
        years_in_business = borrower.years_in_business if borrower else None
        component_scores['tenure'] = RiskScoringEngine.score_tenure(years_in_business)
        
        # Profitability score
        component_scores['profitability'] = RiskScoringEngine.score_profitability(
            ratios.net_margin,
            ratios.ebitda_margin
        )
        
        # Liquidity score
        component_scores['liquidity'] = RiskScoringEngine.score_liquidity(
            ratios.current_ratio,
            ratios.quick_ratio
        )
        
        # Industry score
        industry = borrower.industry if borrower else None
        component_scores['industry'] = RiskScoringEngine.score_industry(industry)
        
        # Calculate overall score
        overall_score = RiskScoringEngine.calculate_overall_score(component_scores)
        
        # Get risk rating
        risk_rating = RiskScoringEngine.get_risk_rating(overall_score)
        
        # Identify risk factors
        risk_factors = RiskScoringEngine.identify_risk_factors(
            component_scores,
            ratios,
            borrower
        )
        
        # Identify mitigating factors
        mitigating_factors = RiskScoringEngine.identify_mitigating_factors(
            component_scores,
            ratios,
            borrower,
            guarantor
        )
        
        # Make automated decision
        automated_decision, max_loan_amount, recommended_terms, required_conditions = \
            RiskScoringEngine._make_automated_decision(
                overall_score,
                risk_rating,
                loan,
                ratios,
                component_scores
            )
        
        # Create risk assessment
        assessment = RiskAssessment(
            loan_application_id=loan_id,
            overall_risk_score=overall_score,
            risk_rating=risk_rating,
            dscr_score=component_scores['dscr'],
            credit_score_component=component_scores['credit'],
            ltv_score=component_scores['ltv'],
            tenure_score=component_scores['tenure'],
            profitability_score=component_scores['profitability'],
            liquidity_score=component_scores['liquidity'],
            industry_risk_score=component_scores['industry'],
            risk_factors=risk_factors,
            mitigating_factors=mitigating_factors,
            automated_decision=automated_decision,
            max_loan_amount=max_loan_amount,
            recommended_terms=recommended_terms,
            required_conditions=required_conditions,
            assessed_by='system',
            model_version='1.0'
        )
        
        # Save to database
        db.add(assessment)
        db.commit()
        db.refresh(assessment)
        
        return assessment
    
    @staticmethod
    def _make_automated_decision(
        overall_score: int,
        risk_rating: str,
        loan: LoanApplication,
        ratios: FinancialRatios,
        component_scores: Dict[str, int]
    ) -> Tuple[str, Optional[Decimal], Optional[str], Optional[str]]:
        """
        Make automated underwriting decision
        
        Returns: (decision, max_loan_amount, recommended_terms, required_conditions)
        """
        # Decision logic based on overall score
        if overall_score >= 80:
            # Approve
            decision = "approve"
            max_loan_amount = loan.loan_amount  # Approve full amount
            recommended_terms = "Standard terms approved"
            required_conditions = None
            
        elif overall_score >= 70:
            # Approve with conditions
            decision = "approve_with_conditions"
            max_loan_amount = loan.loan_amount
            recommended_terms = "Approve with standard conditions"
            
            conditions = []
            if component_scores.get('dscr', 100) < 80:
                conditions.append("Additional cash flow documentation required")
            if component_scores.get('credit', 100) < 80:
                conditions.append("Credit explanation letter required")
            if component_scores.get('liquidity', 100) < 70:
                conditions.append("Minimum liquidity reserves of 6 months PITI required")
            
            required_conditions = "; ".join(conditions) if conditions else "Standard conditions apply"
            
        elif overall_score >= 60:
            # Refer to underwriter
            decision = "refer"
            max_loan_amount = loan.loan_amount * Decimal('0.9')  # Suggest 90% of requested
            recommended_terms = "Refer to senior underwriter for manual review"
            required_conditions = "Manual underwriting required due to marginal risk profile"
            
        else:
            # Decline
            decision = "decline"
            max_loan_amount = None
            recommended_terms = "Decline - risk profile does not meet minimum standards"
            required_conditions = "Not applicable"
        
        return decision, max_loan_amount, recommended_terms, required_conditions
