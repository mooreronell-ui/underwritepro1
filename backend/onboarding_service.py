"""
Onboarding Service
Handles user segmentation, onboarding flows, and progress tracking
"""

import uuid
from datetime import datetime
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

class OnboardingService:
    """Service for managing user onboarding and segmentation"""
    
    def __init__(self):
        self.conn = get_db_connection()
    
    def update_user_type(self, user_id: str, user_data: Dict) -> Dict:
        """Update user type and segmentation data"""
        try:
            cursor = self.conn.cursor()
            
            update_fields = []
            params = []
            
            if 'user_type' in user_data:
                update_fields.append("user_type = %s")
                params.append(user_data['user_type'])
            
            if 'user_subtype' in user_data:
                update_fields.append("user_subtype = %s")
                params.append(user_data['user_subtype'])
            
            if 'learning_path' in user_data:
                update_fields.append("learning_path = %s")
                params.append(user_data['learning_path'])
            
            if 'experience_level' in user_data:
                update_fields.append("experience_level = %s")
                params.append(user_data['experience_level'])
            
            if 'goals' in user_data:
                update_fields.append("goals = %s")
                params.append(user_data['goals'])
            
            if 'years_of_experience' in user_data:
                update_fields.append("years_of_experience = %s")
                params.append(user_data['years_of_experience'])
            
            if 'current_volume_annual' in user_data:
                update_fields.append("current_volume_annual = %s")
                params.append(user_data['current_volume_annual'])
            
            if 'target_income_annual' in user_data:
                update_fields.append("target_income_annual = %s")
                params.append(user_data['target_income_annual'])
            
            if not update_fields:
                return {"success": False, "error": "No fields to update"}
            
            params.append(user_id)
            query = f"UPDATE users SET {', '.join(update_fields)} WHERE id = %s"
            
            cursor.execute(query, params)
            self.conn.commit()
            cursor.close()
            
            return {"success": True, "user_id": user_id}
            
        except Exception as e:
            self.conn.rollback()
            return {"success": False, "error": str(e)}
    
    def get_user_profile(self, user_id: str) -> Optional[Dict]:
        """Get user profile with segmentation data"""
        try:
            cursor = self.conn.cursor()
            cursor.execute("""
                SELECT id, email, full_name, organization_id, 
                       user_type, user_subtype, learning_path, experience_level,
                       goals, years_of_experience, current_volume_annual, target_income_annual,
                       onboarding_completed, created_at
                FROM users WHERE id = %s
            """, (user_id,))
            
            row = cursor.fetchone()
            cursor.close()
            
            if not row:
                return None
            
            return {
                "id": row[0],
                "email": row[1],
                "full_name": row[2],
                "organization_id": row[3],
                "user_type": row[4],
                "user_subtype": row[5],
                "learning_path": row[6],
                "experience_level": row[7],
                "goals": row[8],
                "years_of_experience": row[9],
                "current_volume_annual": float(row[10]) if row[10] else None,
                "target_income_annual": float(row[11]) if row[11] else None,
                "onboarding_completed": row[12],
                "created_at": row[13].isoformat() if row[13] else None
            }
            
        except Exception as e:
            print(f"Error getting user profile: {e}")
            return None
    
    def get_onboarding_template(self, user_type: str) -> Optional[Dict]:
        """Get onboarding template for user type"""
        try:
            cursor = self.conn.cursor()
            cursor.execute("""
                SELECT id, template_name, user_type, steps
                FROM onboarding_templates WHERE user_type = %s
            """, (user_type,))
            
            row = cursor.fetchone()
            cursor.close()
            
            if not row:
                return None
            
            return {
                "id": row[0],
                "template_name": row[1],
                "user_type": row[2],
                "steps": row[3]
            }
            
        except Exception as e:
            print(f"Error getting onboarding template: {e}")
            return None
    
    def initialize_onboarding(self, user_id: str, user_type: str) -> Dict:
        """Initialize onboarding progress for a user"""
        try:
            # Get template
            template = self.get_onboarding_template(user_type)
            if not template:
                return {"success": False, "error": "Template not found"}
            
            cursor = self.conn.cursor()
            
            # Create progress records for each step
            steps = template['steps']
            for step in steps:
                progress_id = str(uuid.uuid4())
                cursor.execute("""
                    INSERT INTO onboarding_progress 
                    (id, user_id, step_number, step_name, step_data, completed)
                    VALUES (%s, %s, %s, %s, %s, %s)
                """, (progress_id, user_id, step['step'], step['name'], 
                      json.dumps(step), False))
            
            self.conn.commit()
            cursor.close()
            
            return {"success": True, "steps_created": len(steps)}
            
        except Exception as e:
            self.conn.rollback()
            return {"success": False, "error": str(e)}
    
    def get_onboarding_progress(self, user_id: str) -> List[Dict]:
        """Get user's onboarding progress"""
        try:
            cursor = self.conn.cursor()
            cursor.execute("""
                SELECT id, step_number, step_name, step_data, completed, completed_at
                FROM onboarding_progress 
                WHERE user_id = %s 
                ORDER BY step_number
            """, (user_id,))
            
            rows = cursor.fetchall()
            cursor.close()
            
            progress = []
            for row in rows:
                progress.append({
                    "id": row[0],
                    "step_number": row[1],
                    "step_name": row[2],
                    "step_data": row[3],
                    "completed": row[4],
                    "completed_at": row[5].isoformat() if row[5] else None
                })
            
            return progress
            
        except Exception as e:
            print(f"Error getting onboarding progress: {e}")
            return []
    
    def complete_onboarding_step(self, user_id: str, step_number: int, step_data: Optional[Dict] = None) -> Dict:
        """Mark an onboarding step as complete"""
        try:
            cursor = self.conn.cursor()
            
            # Update step
            if step_data:
                cursor.execute("""
                    UPDATE onboarding_progress 
                    SET completed = TRUE, completed_at = %s, step_data = %s, updated_at = %s
                    WHERE user_id = %s AND step_number = %s
                """, (datetime.now(), json.dumps(step_data), datetime.now(), user_id, step_number))
            else:
                cursor.execute("""
                    UPDATE onboarding_progress 
                    SET completed = TRUE, completed_at = %s, updated_at = %s
                    WHERE user_id = %s AND step_number = %s
                """, (datetime.now(), datetime.now(), user_id, step_number))
            
            # Check if all steps are complete
            cursor.execute("""
                SELECT COUNT(*) as total, 
                       SUM(CASE WHEN completed THEN 1 ELSE 0 END) as completed
                FROM onboarding_progress WHERE user_id = %s
            """, (user_id,))
            
            row = cursor.fetchone()
            total = row[0]
            completed = row[1]
            
            # If all steps complete, mark user onboarding as complete
            if total == completed:
                cursor.execute("""
                    UPDATE users SET onboarding_completed = TRUE WHERE id = %s
                """, (user_id,))
            
            self.conn.commit()
            cursor.close()
            
            return {
                "success": True,
                "step_completed": step_number,
                "all_complete": total == completed,
                "progress": f"{completed}/{total}"
            }
            
        except Exception as e:
            self.conn.rollback()
            return {"success": False, "error": str(e)}
    
    def get_personalized_dashboard_data(self, user_id: str) -> Dict:
        """Get personalized dashboard data based on user type"""
        try:
            user = self.get_user_profile(user_id)
            if not user:
                return {}
            
            user_type = user.get('user_type', 'commercial_lender')
            
            # Customize based on user type
            if user_type == 'commercial_lender':
                return {
                    "welcome_message": f"Welcome back, {user['full_name']}!",
                    "quick_actions": [
                        {"label": "Create New Deal", "action": "create_deal"},
                        {"label": "Review Pipeline", "action": "view_pipeline"},
                        {"label": "Chat with AI Assistant", "action": "open_ai_chat"}
                    ],
                    "focus_areas": ["Deal Management", "AI Assistants", "Workflows"],
                    "recommended_features": ["Workflow Automation", "Lender Network", "Advanced Analytics"]
                }
            
            elif user_type in ['residential_lo_active', 'residential_lo_former']:
                return {
                    "welcome_message": f"Welcome to commercial lending, {user['full_name']}!",
                    "quick_actions": [
                        {"label": "Continue Learning", "action": "continue_learning"},
                        {"label": "Practice Deal", "action": "create_practice_deal"},
                        {"label": "Income Calculator", "action": "income_calculator"}
                    ],
                    "focus_areas": ["Learning Path", "Practice Deals", "AI Coaches"],
                    "recommended_features": ["Commercial Lending 101", "Practice Mode", "AI Coaching"]
                }
            
            elif user_type == 'career_changer':
                return {
                    "welcome_message": f"Welcome to your new career, {user['full_name']}!",
                    "quick_actions": [
                        {"label": "Start First Lesson", "action": "start_lesson"},
                        {"label": "Join Community", "action": "join_community"},
                        {"label": "Meet Your AI Coach", "action": "meet_coach"}
                    ],
                    "focus_areas": ["Fundamentals", "Community", "Practice"],
                    "recommended_features": ["Beginner Course", "Community Forums", "Practice Scenarios"]
                }
            
            return {}
            
        except Exception as e:
            print(f"Error getting personalized dashboard: {e}")
            return {}
    
    def get_recommended_learning_path(self, user_id: str) -> str:
        """Recommend learning path based on user profile"""
        try:
            user = self.get_user_profile(user_id)
            if not user:
                return 'beginner'
            
            user_type = user.get('user_type')
            experience_level = user.get('experience_level')
            years_exp = user.get('years_of_experience', 0)
            
            # Commercial lenders
            if user_type == 'commercial_lender':
                if years_exp >= 5 or experience_level == 'expert':
                    return 'advanced'
                elif years_exp >= 2 or experience_level == 'intermediate':
                    return 'advanced'  # Still advanced, just need platform training
                else:
                    return 'transition'
            
            # Residential LOs
            elif user_type in ['residential_lo_active', 'residential_lo_former']:
                return 'transition'  # Always transition path for LOs
            
            # Career changers
            elif user_type == 'career_changer':
                if years_exp >= 3 and user.get('user_subtype') in ['financial_advisor', 'realtor']:
                    return 'transition'  # Some relevant experience
                else:
                    return 'beginner'  # Start from scratch
            
            return 'beginner'
            
        except Exception as e:
            print(f"Error recommending learning path: {e}")
            return 'beginner'
