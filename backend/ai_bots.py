"""
AI Bot Framework - Specialized AI assistants for commercial lending
Part of UnderwritePro Enhanced Platform

Implements priority bots:
1. Cassie - Client Onboarding Bot
2. Sage - Document Summarizer Bot
3. Axel - Relationship Manager Bot
4. Remy - Risk Analysis Bot
5. Aurora - Negotiation Coach Bot
6. Titan - Offer Generator Bot
"""

from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
from pydantic import BaseModel
import os
import json

try:
    from openai import OpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False


# Pydantic Models

class ChatMessage(BaseModel):
    role: str  # 'user', 'assistant', 'system'
    content: str


class AIBotRequest(BaseModel):
    bot_type: str
    user_message: str
    context_entity_type: Optional[str] = None
    context_entity_id: Optional[str] = None
    conversation_history: Optional[List[ChatMessage]] = None


class AIRecommendation(BaseModel):
    bot_type: str
    entity_type: str
    entity_id: str
    recommendation_type: str
    recommendation_data: Dict[str, Any]
    confidence_score: float


# AI Bot Base Class

class AIBot:
    """Base class for all AI bots"""
    
    def __init__(self, db, bot_type: str, system_prompt: str):
        self.db = db
        self.bot_type = bot_type
        self.system_prompt = system_prompt
        self.openai_key = os.getenv('OPENAI_API_KEY')
        self.model = os.getenv('OPENAI_MODEL', 'gpt-4')
        
        if OPENAI_AVAILABLE and self.openai_key:
            self.client = OpenAI(api_key=self.openai_key)
        else:
            self.client = None
    
    def chat(self, user_message: str, conversation_history: List[Dict[str, str]] = None, context: Dict[str, Any] = None) -> Dict[str, Any]:
        """Chat with the bot"""
        if not self.client:
            return {
                'success': False,
                'error': 'OpenAI not configured',
                'simulated_response': f"[Simulated {self.bot_type} response to: {user_message}]"
            }
        
        try:
            # Build messages
            messages = [{'role': 'system', 'content': self.system_prompt}]
            
            # Add context if provided
            if context:
                context_str = self._format_context(context)
                messages.append({'role': 'system', 'content': f"Context:\n{context_str}"})
            
            # Add conversation history
            if conversation_history:
                messages.extend(conversation_history)
            
            # Add current user message
            messages.append({'role': 'user', 'content': user_message})
            
            # Call OpenAI
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=0.7,
                max_tokens=1000
            )
            
            assistant_message = response.choices[0].message.content
            
            return {
                'success': True,
                'response': assistant_message,
                'usage': {
                    'prompt_tokens': response.usage.prompt_tokens,
                    'completion_tokens': response.usage.completion_tokens,
                    'total_tokens': response.usage.total_tokens
                }
            }
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }
    
    def _format_context(self, context: Dict[str, Any]) -> str:
        """Format context dictionary into readable string"""
        lines = []
        for key, value in context.items():
            if isinstance(value, dict):
                lines.append(f"{key}:")
                for k, v in value.items():
                    lines.append(f"  {k}: {v}")
            else:
                lines.append(f"{key}: {value}")
        return "\n".join(lines)
    
    def save_conversation(self, user_id: str, conversation_history: List[Dict[str, str]], context_entity_type: str = None, context_entity_id: str = None) -> str:
        """Save conversation to database"""
        query = """
            INSERT INTO ai_conversations (user_id, bot_type, context_entity_type, context_entity_id, conversation_history)
            VALUES (%s, %s, %s, %s, %s)
            RETURNING id
        """
        result = self.db.execute_query(
            query,
            (user_id, self.bot_type, context_entity_type, context_entity_id, json.dumps(conversation_history))
        )
        return result[0]['id'] if result else None
    
    def save_recommendation(self, user_id: str, recommendation: AIRecommendation) -> str:
        """Save recommendation to database"""
        query = """
            INSERT INTO ai_recommendations (user_id, bot_type, entity_type, entity_id, 
                                          recommendation_type, recommendation_data, confidence_score)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            RETURNING id
        """
        result = self.db.execute_query(
            query,
            (user_id, recommendation.bot_type, recommendation.entity_type, recommendation.entity_id,
             recommendation.recommendation_type, json.dumps(recommendation.recommendation_data), recommendation.confidence_score)
        )
        return result[0]['id'] if result else None


# Specialized Bots

class CassieOnboardingBot(AIBot):
    """Cassie - Client Onboarding Bot
    Guides borrowers through the application process"""
    
    def __init__(self, db):
        system_prompt = """You are Cassie, an expert commercial loan onboarding specialist. Your role is to guide borrowers through the loan application process with patience and clarity.

Your responsibilities:
- Explain document requirements based on entity type (LLC, Corporation, Partnership, Sole Proprietor)
- Provide step-by-step guidance through the application
- Answer questions about required documents
- Help borrowers understand what information is needed
- Create customized checklists based on loan type

Be friendly, professional, and encouraging. Break down complex requirements into simple steps. Always confirm understanding before moving forward."""
        super().__init__(db, 'cassie_onboarding', system_prompt)
    
    def generate_document_checklist(self, deal_data: Dict[str, Any]) -> Dict[str, Any]:
        """Generate customized document checklist"""
        entity_type = deal_data.get('entity_type', 'LLC')
        deal_type = deal_data.get('deal_type', 'purchase')
        loan_amount = deal_data.get('loan_amount', 0)
        
        prompt = f"""Generate a comprehensive document checklist for a commercial loan application with these details:
- Entity Type: {entity_type}
- Deal Type: {deal_type}
- Loan Amount: ${loan_amount:,.2f}

Provide a categorized checklist with:
1. Personal documents
2. Business documents
3. Property documents
4. Financial documents

For each document, briefly explain why it's needed."""
        
        response = self.chat(prompt, context=deal_data)
        
        if response['success']:
            return {
                'success': True,
                'checklist': response['response'],
                'deal_type': deal_type,
                'entity_type': entity_type
            }
        return response


class SageDocumentSummarizer(AIBot):
    """Sage - Document Summarizer Bot
    Summarizes financial documents and extracts key information"""
    
    def __init__(self, db):
        system_prompt = """You are Sage, an expert financial document analyst specializing in commercial lending. Your role is to quickly summarize complex financial documents and extract key information.

Your responsibilities:
- Summarize financial statements (P&L, Balance Sheet, Cash Flow)
- Extract key metrics (revenue, EBITDA, debt, assets)
- Identify red flags or concerns
- Highlight positive indicators
- Provide executive summaries for loan committees

Be concise, accurate, and focus on information relevant to loan underwriting. Always cite specific numbers and dates."""
        super().__init__(db, 'sage_summarizer', system_prompt)
    
    def summarize_financial_statement(self, document_text: str, document_type: str) -> Dict[str, Any]:
        """Summarize a financial statement"""
        prompt = f"""Analyze this {document_type} and provide:
1. Executive Summary (2-3 sentences)
2. Key Financial Metrics
3. Strengths
4. Concerns/Red Flags
5. Underwriting Recommendation

Document:
{document_text[:4000]}  # Limit to avoid token limits
"""
        
        response = self.chat(prompt)
        
        if response['success']:
            return {
                'success': True,
                'summary': response['response'],
                'document_type': document_type
            }
        return response
    
    def extract_key_metrics(self, financial_data: Dict[str, Any]) -> Dict[str, Any]:
        """Extract and analyze key financial metrics"""
        prompt = f"""Analyze these financial metrics and provide insights:

{json.dumps(financial_data, indent=2)}

Calculate and explain:
1. Debt Service Coverage Ratio (DSCR)
2. Liquidity ratios
3. Profitability trends
4. Leverage ratios
5. Overall financial health score (1-10)

Provide specific recommendations for underwriting."""
        
        response = self.chat(prompt, context=financial_data)
        
        if response['success']:
            return {
                'success': True,
                'analysis': response['response'],
                'metrics': financial_data
            }
        return response


class AxelRelationshipManager(AIBot):
    """Axel - Relationship Manager Bot
    Tracks and optimizes borrower relationships"""
    
    def __init__(self, db):
        system_prompt = """You are Axel, an expert relationship manager for commercial lending. Your role is to maintain and strengthen borrower relationships to maximize lifetime value.

Your responsibilities:
- Analyze relationship health based on interaction patterns
- Recommend optimal touchpoint timing
- Identify cross-sell opportunities
- Suggest personalized engagement strategies
- Predict churn risk

Be proactive, data-driven, and focused on long-term relationship building."""
        super().__init__(db, 'axel_relationship', system_prompt)
    
    def calculate_relationship_score(self, borrower_id: str) -> Dict[str, Any]:
        """Calculate comprehensive relationship score"""
        # Get borrower data
        borrower_query = """
            SELECT b.*, 
                   COUNT(DISTINCT d.id) as total_deals,
                   SUM(d.loan_amount) as total_loan_volume,
                   MAX(d.created_at) as last_deal_date
            FROM borrowers b
            LEFT JOIN deals d ON b.id = d.borrower_id
            WHERE b.id = %s
            GROUP BY b.id
        """
        borrower_data = self.db.execute_query(borrower_query, (borrower_id,))
        
        if not borrower_data:
            return {'success': False, 'error': 'Borrower not found'}
        
        borrower = borrower_data[0]
        
        # Get touchpoints
        touchpoints_query = """
            SELECT COUNT(*) as touchpoint_count,
                   MAX(occurred_at) as last_contact,
                   MIN(occurred_at) as first_contact
            FROM contact_touchpoints
            WHERE borrower_id = %s
        """
        touchpoints = self.db.execute_query(touchpoints_query, (borrower_id,))
        
        context = {
            'borrower_name': borrower.get('name'),
            'total_deals': borrower.get('total_deals', 0),
            'total_volume': borrower.get('total_loan_volume', 0),
            'last_deal_date': str(borrower.get('last_deal_date', '')),
            'touchpoint_count': touchpoints[0].get('touchpoint_count', 0) if touchpoints else 0,
            'last_contact': str(touchpoints[0].get('last_contact', '')) if touchpoints else 'Never'
        }
        
        prompt = f"""Analyze this borrower relationship and provide:
1. Relationship Health Score (0-100)
2. Engagement Level (Low/Medium/High)
3. Churn Risk (Low/Medium/High)
4. Recommended Next Actions
5. Cross-sell Opportunities

Explain your reasoning for each assessment."""
        
        response = self.chat(prompt, context=context)
        
        if response['success']:
            # Save relationship score
            score_query = """
                INSERT INTO relationship_scores (borrower_id, engagement_score, last_contact_date, score_factors, updated_at)
                VALUES (%s, %s, %s, %s, %s)
                ON CONFLICT (borrower_id) DO UPDATE
                SET engagement_score = EXCLUDED.engagement_score,
                    last_contact_date = EXCLUDED.last_contact_date,
                    score_factors = EXCLUDED.score_factors,
                    updated_at = EXCLUDED.updated_at
            """
            self.db.execute_query(
                score_query,
                (borrower_id, 75, datetime.now(), json.dumps(context), datetime.now())  # Default score, will be updated
            )
            
            return {
                'success': True,
                'analysis': response['response'],
                'context': context
            }
        return response


class RemyRiskAnalyzer(AIBot):
    """Remy - Risk Analysis Bot
    Enhanced risk assessment beyond standard underwriting"""
    
    def __init__(self, db):
        system_prompt = """You are Remy, an expert risk analyst specializing in commercial real estate lending. Your role is to identify and assess risks that standard underwriting might miss.

Your responsibilities:
- Analyze deal structure and identify hidden risks
- Evaluate market conditions and property-specific risks
- Assess borrower capacity beyond financial ratios
- Recommend risk mitigation strategies
- Provide scenario analysis for different economic conditions

Be thorough, conservative, and always explain your risk assessments with specific reasoning."""
        super().__init__(db, 'remy_risk', system_prompt)
    
    def analyze_deal_risk(self, deal_id: str) -> Dict[str, Any]:
        """Comprehensive risk analysis of a deal"""
        # Get deal data
        deal_query = """
            SELECT d.*, b.name as borrower_name, b.entity_type, b.years_in_business,
                   f.revenue, f.net_income, f.total_debt, f.total_assets
            FROM deals d
            LEFT JOIN borrowers b ON d.borrower_id = b.id
            LEFT JOIN financial_data f ON d.id = f.deal_id
            WHERE d.id = %s
        """
        deal_data = self.db.execute_query(deal_query, (deal_id,))
        
        if not deal_data:
            return {'success': False, 'error': 'Deal not found'}
        
        deal = deal_data[0]
        
        # Calculate key ratios
        ltv = (deal.get('loan_amount', 0) / deal.get('appraised_value', 1)) * 100 if deal.get('appraised_value') else 0
        dscr = (deal.get('net_income', 0) * 12) / (deal.get('loan_amount', 0) * (deal.get('interest_rate', 0) / 100) / 12) if deal.get('loan_amount') else 0
        
        context = {
            'deal_type': deal.get('deal_type'),
            'loan_amount': deal.get('loan_amount'),
            'appraised_value': deal.get('appraised_value'),
            'ltv': round(ltv, 2),
            'interest_rate': deal.get('interest_rate'),
            'dscr': round(dscr, 2),
            'borrower_entity': deal.get('entity_type'),
            'years_in_business': deal.get('years_in_business'),
            'revenue': deal.get('revenue'),
            'net_income': deal.get('net_income'),
            'total_debt': deal.get('total_debt')
        }
        
        prompt = f"""Perform a comprehensive risk analysis on this commercial loan:

Provide:
1. Overall Risk Rating (Low/Medium/High/Very High)
2. Key Risk Factors (list top 5)
3. Hidden Risks (non-obvious concerns)
4. Risk Mitigation Recommendations
5. Scenario Analysis:
   - Best case
   - Base case
   - Stress case (recession)
6. Approval Recommendation (Approve/Approve with Conditions/Decline)

Be specific and cite numbers in your analysis."""
        
        response = self.chat(prompt, context=context)
        
        if response['success']:
            # Save recommendation
            recommendation = AIRecommendation(
                bot_type='remy_risk',
                entity_type='deal',
                entity_id=deal_id,
                recommendation_type='risk_analysis',
                recommendation_data=context,
                confidence_score=0.85
            )
            self.save_recommendation(deal.get('created_by'), recommendation)
            
            return {
                'success': True,
                'analysis': response['response'],
                'metrics': context
            }
        return response


class AuroraNegotiationCoach(AIBot):
    """Aurora - Negotiation Coach Bot
    Real-time negotiation guidance"""
    
    def __init__(self, db):
        system_prompt = """You are Aurora, an expert negotiation coach for commercial lending. Your role is to help loan officers navigate negotiations and close deals profitably.

Your responsibilities:
- Suggest optimal pricing and terms
- Provide objection handling strategies
- Recommend concessions and trade-offs
- Identify win-win solutions
- Coach on negotiation tactics

Be strategic, empathetic to both parties, and focused on profitable deal closure."""
        super().__init__(db, 'aurora_negotiation', system_prompt)
    
    def suggest_negotiation_strategy(self, deal_data: Dict[str, Any], borrower_request: str) -> Dict[str, Any]:
        """Suggest negotiation strategy for borrower request"""
        prompt = f"""The borrower has requested: "{borrower_request}"

Deal context:
- Loan Amount: ${deal_data.get('loan_amount', 0):,.2f}
- Current Rate: {deal_data.get('interest_rate', 0)}%
- LTV: {deal_data.get('ltv', 0)}%
- Deal Type: {deal_data.get('deal_type')}

Provide:
1. Assessment of the request (reasonable/aggressive/unreasonable)
2. Recommended response strategy
3. Possible concessions (if any)
4. Trade-offs to propose
5. Talking points and scripts
6. Walk-away threshold

Be specific and provide exact wording for the loan officer to use."""
        
        response = self.chat(prompt, context=deal_data)
        
        if response['success']:
            return {
                'success': True,
                'strategy': response['response'],
                'borrower_request': borrower_request
            }
        return response


class TitanOfferGenerator(AIBot):
    """Titan - Offer Generator Bot
    Creates compelling loan proposals"""
    
    def __init__(self, db):
        system_prompt = """You are Titan, an expert at crafting compelling commercial loan proposals. Your role is to create professional, persuasive offers that win deals.

Your responsibilities:
- Generate complete term sheets
- Highlight competitive advantages
- Address borrower needs and concerns
- Structure deals for mutual benefit
- Create compelling value propositions

Be professional, clear, and persuasive. Focus on benefits, not just features."""
        super().__init__(db, 'titan_offer', system_prompt)
    
    def generate_term_sheet(self, deal_data: Dict[str, Any]) -> Dict[str, Any]:
        """Generate professional term sheet"""
        prompt = f"""Create a professional commercial loan term sheet for:

Deal Details:
- Loan Amount: ${deal_data.get('loan_amount', 0):,.2f}
- Property Value: ${deal_data.get('appraised_value', 0):,.2f}
- Interest Rate: {deal_data.get('interest_rate', 0)}%
- Amortization: {deal_data.get('amortization_months', 0)} months
- Deal Type: {deal_data.get('deal_type')}
- Borrower: {deal_data.get('borrower_name')}

Generate a complete term sheet including:
1. Loan Summary
2. Key Terms (rate, amount, term, amortization)
3. Fees and Costs
4. Conditions Precedent
5. Covenants
6. Competitive Advantages (why this is a great deal)
7. Next Steps

Make it professional, clear, and compelling."""
        
        response = self.chat(prompt, context=deal_data)
        
        if response['success']:
            return {
                'success': True,
                'term_sheet': response['response'],
                'deal_data': deal_data
            }
        return response


# AI Bot Service

class AIBotService:
    """Service to manage all AI bots"""
    
    def __init__(self, db):
        self.db = db
        self.bots = {
            'cassie_onboarding': CassieOnboardingBot(db),
            'sage_summarizer': SageDocumentSummarizer(db),
            'axel_relationship': AxelRelationshipManager(db),
            'remy_risk': RemyRiskAnalyzer(db),
            'aurora_negotiation': AuroraNegotiationCoach(db),
            'titan_offer': TitanOfferGenerator(db)
        }
    
    def get_bot(self, bot_type: str) -> Optional[AIBot]:
        """Get bot by type"""
        return self.bots.get(bot_type)
    
    def chat_with_bot(self, request: AIBotRequest, user_id: str) -> Dict[str, Any]:
        """Chat with specified bot"""
        bot = self.get_bot(request.bot_type)
        if not bot:
            return {'success': False, 'error': f'Bot type {request.bot_type} not found'}
        
        # Get context if entity provided
        context = None
        if request.context_entity_type and request.context_entity_id:
            context = self._get_entity_context(request.context_entity_type, request.context_entity_id)
        
        # Convert conversation history
        history = [{'role': msg.role, 'content': msg.content} for msg in request.conversation_history] if request.conversation_history else []
        
        # Chat
        response = bot.chat(request.user_message, history, context)
        
        # Save conversation
        if response.get('success'):
            history.append({'role': 'user', 'content': request.user_message})
            history.append({'role': 'assistant', 'content': response['response']})
            bot.save_conversation(user_id, history, request.context_entity_type, request.context_entity_id)
        
        return response
    
    def _get_entity_context(self, entity_type: str, entity_id: str) -> Dict[str, Any]:
        """Get context data for entity"""
        if entity_type == 'deal':
            query = """
                SELECT d.*, b.name as borrower_name, b.entity_type
                FROM deals d
                LEFT JOIN borrowers b ON d.borrower_id = b.id
                WHERE d.id = %s
            """
            result = self.db.execute_query(query, (entity_id,))
            return result[0] if result else {}
        elif entity_type == 'borrower':
            query = "SELECT * FROM borrowers WHERE id = %s"
            result = self.db.execute_query(query, (entity_id,))
            return result[0] if result else {}
        return {}
    
    def get_recommendations(self, user_id: str, entity_type: str = None, entity_id: str = None, status: str = 'pending') -> List[Dict[str, Any]]:
        """Get AI recommendations for user"""
        where_clauses = ["user_id = %s", "status = %s"]
        params = [user_id, status]
        
        if entity_type:
            where_clauses.append("entity_type = %s")
            params.append(entity_type)
        if entity_id:
            where_clauses.append("entity_id = %s")
            params.append(entity_id)
        
        where_sql = " AND ".join(where_clauses)
        
        query = f"""
            SELECT * FROM ai_recommendations
            WHERE {where_sql}
            ORDER BY created_at DESC
            LIMIT 50
        """
        
        return self.db.execute_query(query, tuple(params))


# Helper function

def get_ai_bot_service(db):
    """Factory function to create AI bot service"""
    return AIBotService(db)
