"""
Practice Mode and Gamification Service
Handles practice scenarios, feedback, points, badges, and leaderboards
"""

import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import psycopg2
import os

def get_db_connection():
    """Get database connection"""
    return psycopg2.connect(
        dbname=os.getenv('DB_NAME', 'underwritepro'),
        user=os.getenv('DB_USER', 'uwpro'),
        password=os.getenv('DB_PASSWORD', 'uwpro_secure_2024'),
        host=os.getenv('DB_HOST', 'localhost'),
        port=os.getenv('DB_PORT', '5432')
    )
import json
import os

class PracticeGamificationService:
    """Service for practice mode and gamification features"""
    
    def __init__(self):
        self.conn = get_db_connection()
        self.openai_api_key = os.getenv('OPENAI_API_KEY')
    
    # ===== PRACTICE SCENARIOS =====
    
    def get_practice_scenarios(self, difficulty: Optional[str] = None) -> List[Dict]:
        """Get all practice scenarios, optionally filtered by difficulty"""
        try:
            cursor = self.conn.cursor()
            
            if difficulty:
                cursor.execute("""
                    SELECT id, name, slug, description, difficulty, scenario_type,
                           learning_objectives, expected_outcome, hints
                    FROM practice_scenarios WHERE difficulty = %s
                    ORDER BY name
                """, (difficulty,))
            else:
                cursor.execute("""
                    SELECT id, name, slug, description, difficulty, scenario_type,
                           learning_objectives, expected_outcome, hints
                    FROM practice_scenarios ORDER BY difficulty, name
                """)
            
            rows = cursor.fetchall()
            cursor.close()
            
            scenarios = []
            for row in rows:
                scenarios.append({
                    "id": row[0],
                    "name": row[1],
                    "slug": row[2],
                    "description": row[3],
                    "difficulty": row[4],
                    "scenario_type": row[5],
                    "learning_objectives": row[6],
                    "expected_outcome": row[7],
                    "hints": row[8]
                })
            
            return scenarios
            
        except Exception as e:
            print(f"Error getting practice scenarios: {e}")
            return []
    
    def get_practice_scenario(self, scenario_id: str) -> Optional[Dict]:
        """Get a specific practice scenario with full data"""
        try:
            cursor = self.conn.cursor()
            
            cursor.execute("""
                SELECT id, name, slug, description, difficulty, scenario_type,
                       learning_objectives, expected_outcome, hints, scenario_data, success_criteria
                FROM practice_scenarios WHERE id = %s
            """, (scenario_id,))
            
            row = cursor.fetchone()
            cursor.close()
            
            if not row:
                return None
            
            return {
                "id": row[0],
                "name": row[1],
                "slug": row[2],
                "description": row[3],
                "difficulty": row[4],
                "scenario_type": row[5],
                "learning_objectives": row[6],
                "expected_outcome": row[7],
                "hints": row[8],
                "scenario_data": row[9],
                "success_criteria": row[10]
            }
            
        except Exception as e:
            print(f"Error getting practice scenario: {e}")
            return None
    
    def create_practice_deal_from_scenario(self, user_id: str, scenario_id: str) -> Dict:
        """Create a practice deal from a scenario"""
        try:
            scenario = self.get_practice_scenario(scenario_id)
            if not scenario:
                return {"success": False, "error": "Scenario not found"}
            
            # Create a practice deal with scenario data
            deal_id = str(uuid.uuid4())
            cursor = self.conn.cursor()
            
            # Get user's organization
            cursor.execute("SELECT organization_id FROM users WHERE id = %s", (user_id,))
            org_row = cursor.fetchone()
            if not org_row:
                return {"success": False, "error": "User not found"}
            
            org_id = org_row[0]
            
            # Create practice deal
            scenario_data = scenario['scenario_data']
            cursor.execute("""
                INSERT INTO deals 
                (id, organization_id, created_by, deal_name, loan_amount, status, 
                 is_practice, practice_scenario_id)
                VALUES (%s, %s, %s, %s, %s, 'active', TRUE, %s)
            """, (
                deal_id,
                org_id,
                user_id,
                f"Practice: {scenario['name']}",
                scenario_data.get('loan_amount', 0),
                scenario_id
            ))
            
            self.conn.commit()
            cursor.close()
            
            return {
                "success": True,
                "deal_id": deal_id,
                "scenario": scenario
            }
            
        except Exception as e:
            self.conn.rollback()
            return {"success": False, "error": str(e)}
    
    def submit_practice_deal(self, user_id: str, deal_id: str, deal_data: Dict) -> Dict:
        """Submit a practice deal for AI feedback"""
        try:
            cursor = self.conn.cursor()
            
            # Get deal and scenario
            cursor.execute("""
                SELECT d.practice_scenario_id, ps.success_criteria, ps.scenario_data, ps.name
                FROM deals d
                JOIN practice_scenarios ps ON d.practice_scenario_id = ps.id
                WHERE d.id = %s AND d.is_practice = TRUE
            """, (deal_id,))
            
            row = cursor.fetchone()
            if not row:
                return {"success": False, "error": "Practice deal not found"}
            
            scenario_id, success_criteria, scenario_data, scenario_name = row
            
            # Generate AI feedback
            feedback = self._generate_practice_feedback(deal_data, scenario_data, success_criteria)
            
            # Save feedback
            feedback_id = str(uuid.uuid4())
            cursor.execute("""
                INSERT INTO practice_feedback 
                (id, user_id, deal_id, scenario_id, ai_feedback, score, 
                 strengths, areas_for_improvement, recommendations)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (
                feedback_id,
                user_id,
                deal_id,
                scenario_id,
                feedback['feedback_text'],
                feedback['score'],
                feedback['strengths'],
                feedback['areas_for_improvement'],
                feedback['recommendations']
            ))
            
            # Update deal
            cursor.execute("""
                UPDATE deals 
                SET practice_completed = TRUE, practice_score = %s
                WHERE id = %s
            """, (feedback['score'], deal_id))
            
            # Award points
            self.award_points(user_id, 'complete_practice', {
                'deal_id': deal_id,
                'score': feedback['score']
            })
            
            # Award badge if high score
            if feedback['score'] >= 90:
                self.award_badge(user_id, 'practice-master', 'Practice Master', 
                                'Scored 90+ on a practice deal', '🎯', 'learning')
            
            self.conn.commit()
            cursor.close()
            
            return {
                "success": True,
                "feedback_id": feedback_id,
                "score": feedback['score'],
                "feedback": feedback
            }
            
        except Exception as e:
            self.conn.rollback()
            return {"success": False, "error": str(e)}
    
    def _generate_practice_feedback(self, deal_data: Dict, scenario_data: Dict, success_criteria: Dict) -> Dict:
        """Generate AI feedback for a practice deal"""
        # In production, this would call OpenAI API
        # For now, generate rule-based feedback
        
        score = 75  # Base score
        strengths = []
        improvements = []
        recommendations = []
        
        # Check DSCR
        if 'dscr' in deal_data:
            dscr = deal_data['dscr']
            min_dscr = success_criteria.get('min_dscr', 1.25)
            if dscr >= min_dscr:
                score += 10
                strengths.append(f"Good DSCR of {dscr:.2f} (above minimum {min_dscr})")
            else:
                score -= 10
                improvements.append(f"DSCR of {dscr:.2f} is below minimum {min_dscr}")
                recommendations.append("Consider reducing loan amount or improving property NOI")
        
        # Check LTV
        if 'ltv' in deal_data:
            ltv = deal_data['ltv']
            max_ltv = success_criteria.get('max_ltv', 0.75)
            if ltv <= max_ltv:
                score += 10
                strengths.append(f"Conservative LTV of {ltv:.1%} (below maximum {max_ltv:.1%})")
            else:
                score -= 10
                improvements.append(f"LTV of {ltv:.1%} exceeds maximum {max_ltv:.1%}")
                recommendations.append("Increase down payment to reduce LTV")
        
        # Check risk assessment
        if 'risk_assessment' in deal_data:
            strengths.append("Completed comprehensive risk assessment")
            score += 5
        else:
            improvements.append("Missing risk assessment")
            recommendations.append("Always conduct thorough risk analysis")
        
        feedback_text = f"""
**Practice Deal Feedback: {deal_data.get('deal_name', 'Unnamed Deal')}**

**Overall Score: {score}/100**

**What You Did Well:**
{chr(10).join('- ' + s for s in strengths) if strengths else '- Basic deal structure completed'}

**Areas for Improvement:**
{chr(10).join('- ' + i for i in improvements) if improvements else '- Continue refining your analysis skills'}

**Recommendations:**
{chr(10).join('- ' + r for r in recommendations) if recommendations else '- Keep practicing with more complex scenarios'}

Great work on completing this practice scenario! Each practice deal helps you build confidence and expertise.
        """.strip()
        
        return {
            "score": max(0, min(100, score)),
            "feedback_text": feedback_text,
            "strengths": strengths,
            "areas_for_improvement": improvements,
            "recommendations": recommendations
        }
    
    # ===== GAMIFICATION: POINTS =====
    
    def initialize_user_points(self, user_id: str) -> Dict:
        """Initialize points for a new user"""
        try:
            cursor = self.conn.cursor()
            
            # Check if already exists
            cursor.execute("SELECT id FROM user_points WHERE user_id = %s", (user_id,))
            if cursor.fetchone():
                cursor.close()
                return {"success": True, "message": "Already initialized"}
            
            points_id = str(uuid.uuid4())
            cursor.execute("""
                INSERT INTO user_points (id, user_id, total_points, level, level_name, points_to_next_level)
                VALUES (%s, %s, 0, 1, 'Beginner', 100)
            """, (points_id, user_id))
            
            self.conn.commit()
            cursor.close()
            
            return {"success": True, "points_id": points_id}
            
        except Exception as e:
            self.conn.rollback()
            return {"success": False, "error": str(e)}
    
    def award_points(self, user_id: str, action: str, metadata: Dict = None) -> Dict:
        """Award points for an action"""
        try:
            cursor = self.conn.cursor()
            
            # Get points for action
            cursor.execute("SELECT points FROM gamification_rules WHERE action = %s", (action,))
            row = cursor.fetchone()
            if not row:
                return {"success": False, "error": "Action not found"}
            
            points = row[0]
            
            # Initialize if needed
            self.initialize_user_points(user_id)
            
            # Add points
            cursor.execute("""
                UPDATE user_points 
                SET total_points = total_points + %s, updated_at = %s
                WHERE user_id = %s
                RETURNING total_points, level, points_to_next_level
            """, (points, datetime.now(), user_id))
            
            row = cursor.fetchone()
            if not row:
                return {"success": False, "error": "User not found"}
            
            total_points, current_level, points_to_next = row
            
            # Check for level up
            level_thresholds = [0, 100, 250, 500, 1000, 2000, 5000, 10000]
            level_names = ['Beginner', 'Novice', 'Intermediate', 'Advanced', 'Expert', 'Master', 'Legend', 'Grandmaster']
            
            new_level = current_level
            for i, threshold in enumerate(level_thresholds):
                if total_points >= threshold:
                    new_level = i + 1
            
            leveled_up = new_level > current_level
            
            if leveled_up:
                next_threshold = level_thresholds[new_level] if new_level < len(level_thresholds) else level_thresholds[-1]
                cursor.execute("""
                    UPDATE user_points 
                    SET level = %s, level_name = %s, points_to_next_level = %s
                    WHERE user_id = %s
                """, (new_level, level_names[new_level-1], next_threshold - total_points, user_id))
                
                # Award level-up badge
                self.award_badge(user_id, f'level-{new_level}', f'Level {new_level}', 
                                f'Reached level {new_level}: {level_names[new_level-1]}', '⭐', 'milestone')
            
            self.conn.commit()
            cursor.close()
            
            return {
                "success": True,
                "points_awarded": points,
                "total_points": total_points,
                "level": new_level,
                "leveled_up": leveled_up
            }
            
        except Exception as e:
            self.conn.rollback()
            return {"success": False, "error": str(e)}
    
    def get_user_points(self, user_id: str) -> Dict:
        """Get user's points and level"""
        try:
            cursor = self.conn.cursor()
            
            cursor.execute("""
                SELECT total_points, level, level_name, points_to_next_level
                FROM user_points WHERE user_id = %s
            """, (user_id,))
            
            row = cursor.fetchone()
            cursor.close()
            
            if not row:
                # Initialize if not exists
                self.initialize_user_points(user_id)
                return {
                    "total_points": 0,
                    "level": 1,
                    "level_name": "Beginner",
                    "points_to_next_level": 100
                }
            
            return {
                "total_points": row[0],
                "level": row[1],
                "level_name": row[2],
                "points_to_next_level": row[3]
            }
            
        except Exception as e:
            print(f"Error getting user points: {e}")
            return {}
    
    # ===== GAMIFICATION: BADGES =====
    
    def award_badge(self, user_id: str, badge_id: str, badge_name: str, 
                   badge_description: str, badge_icon: str, badge_category: str) -> Dict:
        """Award a badge to a user"""
        try:
            cursor = self.conn.cursor()
            
            # Check if already has badge
            cursor.execute("""
                SELECT id FROM user_badges 
                WHERE user_id = %s AND badge_id = %s
            """, (user_id, badge_id))
            
            if cursor.fetchone():
                cursor.close()
                return {"success": True, "message": "Badge already awarded"}
            
            # Award badge
            user_badge_id = str(uuid.uuid4())
            cursor.execute("""
                INSERT INTO user_badges 
                (id, user_id, badge_id, badge_name, badge_description, badge_icon, badge_category)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
            """, (user_badge_id, user_id, badge_id, badge_name, badge_description, badge_icon, badge_category))
            
            self.conn.commit()
            cursor.close()
            
            return {"success": True, "badge_id": user_badge_id}
            
        except Exception as e:
            self.conn.rollback()
            return {"success": False, "error": str(e)}
    
    def get_user_badges(self, user_id: str) -> List[Dict]:
        """Get all badges for a user"""
        try:
            cursor = self.conn.cursor()
            
            cursor.execute("""
                SELECT id, badge_id, badge_name, badge_description, badge_icon, 
                       badge_category, earned_at
                FROM user_badges 
                WHERE user_id = %s 
                ORDER BY earned_at DESC
            """, (user_id,))
            
            rows = cursor.fetchall()
            cursor.close()
            
            badges = []
            for row in rows:
                badges.append({
                    "id": row[0],
                    "badge_id": row[1],
                    "badge_name": row[2],
                    "badge_description": row[3],
                    "badge_icon": row[4],
                    "badge_category": row[5],
                    "earned_at": row[6].isoformat() if row[6] else None
                })
            
            return badges
            
        except Exception as e:
            print(f"Error getting user badges: {e}")
            return []
    
    # ===== GAMIFICATION: LEADERBOARDS =====
    
    def update_leaderboard(self, leaderboard_type: str, period: str) -> Dict:
        """Update leaderboard rankings"""
        try:
            cursor = self.conn.cursor()
            
            # Determine period dates
            now = datetime.now()
            if period == 'weekly':
                period_start = now - timedelta(days=now.weekday())
                period_end = period_start + timedelta(days=6)
            elif period == 'monthly':
                period_start = now.replace(day=1)
                if now.month == 12:
                    period_end = now.replace(year=now.year+1, month=1, day=1) - timedelta(days=1)
                else:
                    period_end = now.replace(month=now.month+1, day=1) - timedelta(days=1)
            else:  # all_time
                period_start = datetime(2020, 1, 1).date()
                period_end = now.date()
            
            # Get scores based on leaderboard type
            if leaderboard_type == 'total_points':
                cursor.execute("""
                    SELECT user_id, total_points as score
                    FROM user_points
                    ORDER BY total_points DESC
                    LIMIT 100
                """)
            elif leaderboard_type == 'learning_progress':
                cursor.execute("""
                    SELECT user_id, COUNT(*) as score
                    FROM user_learning_progress
                    WHERE status = 'completed'
                    GROUP BY user_id
                    ORDER BY score DESC
                    LIMIT 100
                """)
            else:
                return {"success": False, "error": "Unknown leaderboard type"}
            
            rows = cursor.fetchall()
            
            # Clear existing entries for this period
            cursor.execute("""
                DELETE FROM leaderboards 
                WHERE leaderboard_type = %s AND period = %s AND period_start = %s
            """, (leaderboard_type, period, period_start))
            
            # Insert new rankings
            for rank, (user_id, score) in enumerate(rows, 1):
                leaderboard_id = str(uuid.uuid4())
                cursor.execute("""
                    INSERT INTO leaderboards 
                    (id, leaderboard_type, period, user_id, score, rank, period_start, period_end)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                """, (leaderboard_id, leaderboard_type, period, user_id, score, rank, period_start, period_end))
            
            self.conn.commit()
            cursor.close()
            
            return {"success": True, "entries": len(rows)}
            
        except Exception as e:
            self.conn.rollback()
            return {"success": False, "error": str(e)}
    
    def get_leaderboard(self, leaderboard_type: str, period: str, limit: int = 50) -> List[Dict]:
        """Get leaderboard rankings"""
        try:
            cursor = self.conn.cursor()
            
            cursor.execute("""
                SELECT l.rank, l.user_id, u.full_name, l.score
                FROM leaderboards l
                JOIN users u ON l.user_id = u.id
                WHERE l.leaderboard_type = %s AND l.period = %s
                ORDER BY l.rank
                LIMIT %s
            """, (leaderboard_type, period, limit))
            
            rows = cursor.fetchall()
            cursor.close()
            
            leaderboard = []
            for row in rows:
                leaderboard.append({
                    "rank": row[0],
                    "user_id": row[1],
                    "user_name": row[2],
                    "score": row[3]
                })
            
            return leaderboard
            
        except Exception as e:
            print(f"Error getting leaderboard: {e}")
            return []
