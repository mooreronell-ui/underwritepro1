"""
Underwriting API Routes
Risk assessment, AI advisor, and automated decisions
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import Optional, List
from uuid import UUID
from pydantic import BaseModel

from database_config import get_db
from services.risk_scoring_engine import RiskScoringEngine
from services.ai_underwriting_advisor import AIUnderwritingAdvisor
from services.financial_analysis_engine import FinancialAnalysisEngine
from models.financial import RiskAssessment


router = APIRouter(prefix="/api/underwriting", tags=["underwriting"])


# ========================================================================
# Request/Response Models
# ========================================================================

class RiskAssessmentRequest(BaseModel):
    """Request to perform risk assessment"""
    loan_application_id: UUID


class AIQuestionRequest(BaseModel):
    """Request to ask AI advisor a question"""
    question: str
    loan_application_id: Optional[UUID] = None


class AIAnalysisRequest(BaseModel):
    """Request for AI loan analysis"""
    loan_application_id: UUID


class RatioExplanationRequest(BaseModel):
    """Request for ratio explanation"""
    ratio_name: str
    value: Optional[float] = None


# ========================================================================
# Risk Assessment Endpoints
# ========================================================================

@router.post("/assess/{loan_id}", status_code=status.HTTP_200_OK)
def assess_loan_risk(
    loan_id: UUID,
    db: Session = Depends(get_db)
):
    """
    Perform comprehensive risk assessment on a loan application
    
    This endpoint:
    1. Calculates all financial ratios (if not already done)
    2. Scores each risk component
    3. Calculates overall risk score
    4. Determines risk rating
    5. Makes automated underwriting decision
    6. Identifies risk and mitigating factors
    
    Returns complete risk assessment with automated decision.
    """
    try:
        # First ensure financial ratios are calculated
        try:
            FinancialAnalysisEngine.analyze_loan_application(db, loan_id)
        except Exception as e:
            # Ratios might already exist, continue
            pass
        
        # Perform risk assessment
        assessment = RiskScoringEngine.assess_loan_application(db, loan_id)
        
        return {
            "success": True,
            "assessment": {
                "loan_application_id": str(assessment.loan_application_id),
                "overall_risk_score": assessment.overall_risk_score,
                "risk_rating": assessment.risk_rating,
                "component_scores": {
                    "dscr": assessment.dscr_score,
                    "credit": assessment.credit_score_component,
                    "ltv": assessment.ltv_score,
                    "tenure": assessment.tenure_score,
                    "profitability": assessment.profitability_score,
                    "liquidity": assessment.liquidity_score,
                    "industry": assessment.industry_risk_score
                },
                "automated_decision": assessment.automated_decision,
                "max_loan_amount": float(assessment.max_loan_amount) if assessment.max_loan_amount else None,
                "recommended_terms": assessment.recommended_terms,
                "required_conditions": assessment.required_conditions,
                "risk_factors": assessment.risk_factors,
                "mitigating_factors": assessment.mitigating_factors,
                "assessed_at": assessment.created_at.isoformat()
            }
        }
    
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Risk assessment failed: {str(e)}"
        )


@router.get("/assessment/{loan_id}", status_code=status.HTTP_200_OK)
def get_risk_assessment(
    loan_id: UUID,
    db: Session = Depends(get_db)
):
    """
    Get existing risk assessment for a loan
    
    Returns the most recent risk assessment if it exists.
    """
    from models.loan import LoanApplication
    
    loan = db.query(LoanApplication).filter(LoanApplication.id == loan_id).first()
    
    if not loan:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Loan application not found"
        )
    
    assessment = loan.risk_assessment
    
    if not assessment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No risk assessment found for this loan. Run /assess/{loan_id} first."
        )
    
    return {
        "success": True,
        "assessment": {
            "loan_application_id": str(assessment.loan_application_id),
            "overall_risk_score": assessment.overall_risk_score,
            "risk_rating": assessment.risk_rating,
            "component_scores": {
                "dscr": assessment.dscr_score,
                "credit": assessment.credit_score_component,
                "ltv": assessment.ltv_score,
                "tenure": assessment.tenure_score,
                "profitability": assessment.profitability_score,
                "liquidity": assessment.liquidity_score,
                "industry": assessment.industry_risk_score
            },
            "automated_decision": assessment.automated_decision,
            "max_loan_amount": float(assessment.max_loan_amount) if assessment.max_loan_amount else None,
            "recommended_terms": assessment.recommended_terms,
            "required_conditions": assessment.required_conditions,
            "risk_factors": assessment.risk_factors,
            "mitigating_factors": assessment.mitigating_factors,
            "assessed_at": assessment.created_at.isoformat()
        }
    }


# ========================================================================
# AI Advisor Endpoints
# ========================================================================

@router.post("/ai/ask", status_code=status.HTTP_200_OK)
def ask_ai_advisor(
    request: AIQuestionRequest,
    db: Session = Depends(get_db)
):
    """
    Ask the AI underwriting advisor a question
    
    The AI has specialized knowledge of:
    - Commercial lending best practices
    - Underwriting guidelines
    - Financial ratio interpretation
    - Risk assessment methodologies
    
    Optionally provide loan_application_id for context-specific advice.
    """
    advisor = AIUnderwritingAdvisor()
    
    # Get loan context if provided
    context = None
    if request.loan_application_id:
        from models.loan import LoanApplication
        loan = db.query(LoanApplication).filter(
            LoanApplication.id == request.loan_application_id
        ).first()
        
        if loan:
            context = {
                "loan_type": loan.loan_type.value,
                "loan_amount": float(loan.loan_amount),
                "property_type": loan.property_info.property_type.value if loan.property_info else None
            }
    
    try:
        answer = advisor.ask(request.question, context=context)
        
        return {
            "success": True,
            "question": request.question,
            "answer": answer
        }
    
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"AI advisor error: {str(e)}"
        )


@router.post("/ai/analyze", status_code=status.HTTP_200_OK)
def analyze_loan_with_ai(
    request: AIAnalysisRequest,
    db: Session = Depends(get_db)
):
    """
    Get comprehensive AI analysis of a loan application
    
    The AI will provide:
    - Strengths of the application
    - Weaknesses or concerns
    - Recommended decision
    - Suggested conditions or mitigations
    - Key considerations for underwriter
    """
    from models.loan import LoanApplication
    
    loan = db.query(LoanApplication).filter(
        LoanApplication.id == request.loan_application_id
    ).first()
    
    if not loan:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Loan application not found"
        )
    
    # Gather loan data
    ratios = loan.financial_ratios
    assessment = loan.risk_assessment
    borrower = loan.borrower
    guarantor = loan.guarantors[0] if loan.guarantors else None
    
    loan_data = {
        "loan_type": loan.loan_type.value,
        "loan_amount": float(loan.loan_amount),
        "property_type": loan.property_info.property_type.value if loan.property_info else None,
        "dscr": float(ratios.global_dscr or ratios.property_dscr or ratios.business_dscr) if ratios else None,
        "ltv": float(ratios.ltv) if ratios and ratios.ltv else None,
        "debt_yield": float(ratios.debt_yield) if ratios and ratios.debt_yield else None,
        "current_ratio": float(ratios.current_ratio) if ratios and ratios.current_ratio else None,
        "net_margin": float(ratios.net_margin) if ratios and ratios.net_margin else None,
        "years_in_business": float(borrower.years_in_business) if borrower and borrower.years_in_business else None,
        "industry": borrower.industry if borrower else None,
        "business_credit": borrower.business_credit_score if borrower else None,
        "personal_credit": guarantor.credit_score if guarantor else None,
        "risk_score": assessment.overall_risk_score if assessment else None,
        "risk_rating": assessment.risk_rating if assessment else None
    }
    
    advisor = AIUnderwritingAdvisor()
    
    try:
        analysis = advisor.analyze_loan(loan_data)
        
        return {
            "success": True,
            "loan_application_id": str(request.loan_application_id),
            "analysis": analysis
        }
    
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"AI analysis error: {str(e)}"
        )


@router.post("/ai/explain-ratio", status_code=status.HTTP_200_OK)
def explain_ratio(request: RatioExplanationRequest):
    """
    Get explanation of a financial ratio
    
    Optionally provide the current value for context-specific guidance.
    """
    advisor = AIUnderwritingAdvisor()
    
    try:
        explanation = advisor.explain_ratio(request.ratio_name, request.value)
        
        return {
            "success": True,
            "ratio_name": request.ratio_name,
            "value": request.value,
            "explanation": explanation
        }
    
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Explanation error: {str(e)}"
        )


@router.get("/ai/quick-answers/{question_key}", status_code=status.HTTP_200_OK)
def get_quick_answer(question_key: str):
    """
    Get pre-defined answer for common questions (faster than AI call)
    
    Available keys:
    - what_is_dscr
    - what_is_ltv
    - what_documents_needed
    - how_calculate_noi
    """
    answer = AIUnderwritingAdvisor.get_quick_answer(question_key)
    
    if not answer:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No quick answer found for key: {question_key}"
        )
    
    return {
        "success": True,
        "question_key": question_key,
        "answer": answer
    }


# ========================================================================
# Financial Analysis Endpoints
# ========================================================================

@router.post("/analyze/{loan_id}", status_code=status.HTTP_200_OK)
def analyze_loan_financials(
    loan_id: UUID,
    db: Session = Depends(get_db)
):
    """
    Calculate all financial ratios for a loan application
    
    This endpoint calculates 20+ financial ratios including:
    - DSCR (Global, Business, Property)
    - LTV, LTC, DTI
    - Current, Quick, Cash ratios
    - Profitability margins
    - Investment property ratios (Cap Rate, Debt Yield, etc.)
    
    Returns all calculated ratios.
    """
    try:
        ratios = FinancialAnalysisEngine.analyze_loan_application(db, loan_id)
        
        return {
            "success": True,
            "ratios": {
                "loan_application_id": str(ratios.loan_application_id),
                "calculation_method": ratios.calculation_method,
                "dscr": {
                    "global_dscr": float(ratios.global_dscr) if ratios.global_dscr else None,
                    "business_dscr": float(ratios.business_dscr) if ratios.business_dscr else None,
                    "property_dscr": float(ratios.property_dscr) if ratios.property_dscr else None,
                    "personal_dscr": float(ratios.personal_dscr) if ratios.personal_dscr else None
                },
                "leverage": {
                    "ltv": float(ratios.ltv) if ratios.ltv else None,
                    "ltc": float(ratios.ltc) if ratios.ltc else None,
                    "dti": float(ratios.dti) if ratios.dti else None,
                    "debt_to_ebitda": float(ratios.debt_to_ebitda) if ratios.debt_to_ebitda else None
                },
                "liquidity": {
                    "current_ratio": float(ratios.current_ratio) if ratios.current_ratio else None,
                    "quick_ratio": float(ratios.quick_ratio) if ratios.quick_ratio else None,
                    "cash_ratio": float(ratios.cash_ratio) if ratios.cash_ratio else None
                },
                "profitability": {
                    "gross_margin": float(ratios.gross_margin) if ratios.gross_margin else None,
                    "operating_margin": float(ratios.operating_margin) if ratios.operating_margin else None,
                    "net_margin": float(ratios.net_margin) if ratios.net_margin else None,
                    "ebitda_margin": float(ratios.ebitda_margin) if ratios.ebitda_margin else None,
                    "roa": float(ratios.roa) if ratios.roa else None,
                    "roe": float(ratios.roe) if ratios.roe else None
                },
                "investment_property": {
                    "cap_rate": float(ratios.cap_rate) if ratios.cap_rate else None,
                    "debt_yield": float(ratios.debt_yield) if ratios.debt_yield else None,
                    "cash_on_cash_return": float(ratios.cash_on_cash_return) if ratios.cash_on_cash_return else None,
                    "break_even_occupancy": float(ratios.break_even_occupancy) if ratios.break_even_occupancy else None,
                    "operating_expense_ratio": float(ratios.operating_expense_ratio) if ratios.operating_expense_ratio else None
                },
                "calculated_at": ratios.created_at.isoformat()
            }
        }
    
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Financial analysis failed: {str(e)}"
        )
