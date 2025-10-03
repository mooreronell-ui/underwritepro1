"""
Learning Management System (LMS) Service
Handles learning paths, modules, lessons, progress tracking, quizzes, and achievements
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

class LMSService:
    """Service for managing the Learning Management System"""
    
    def __init__(self):
        self.conn = get_db_connection()
    
    # ===== LEARNING PATHS =====
    
    def create_learning_path(self, path_data: Dict) -> Dict:
        """Create a new learning path"""
        try:
            path_id = str(uuid.uuid4())
            cursor = self.conn.cursor()
            
            cursor.execute("""
                INSERT INTO learning_paths 
                (id, name, slug, description, target_audience, duration_weeks, 
                 difficulty, prerequisites, learning_objectives)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (
                path_id,
                path_data['name'],
                path_data['slug'],
                path_data.get('description'),
                path_data['target_audience'],
                path_data.get('duration_weeks'),
                path_data.get('difficulty'),
                path_data.get('prerequisites', []),
                path_data.get('learning_objectives', [])
            ))
            
            self.conn.commit()
            cursor.close()
            
            return {"success": True, "path_id": path_id}
            
        except Exception as e:
            self.conn.rollback()
            return {"success": False, "error": str(e)}
    
    def get_learning_paths(self, target_audience: Optional[str] = None) -> List[Dict]:
        """Get all learning paths, optionally filtered by audience"""
        try:
            cursor = self.conn.cursor()
            
            if target_audience:
                cursor.execute("""
                    SELECT id, name, slug, description, target_audience, duration_weeks,
                           difficulty, prerequisites, learning_objectives, created_at
                    FROM learning_paths WHERE target_audience = %s
                    ORDER BY name
                """, (target_audience,))
            else:
                cursor.execute("""
                    SELECT id, name, slug, description, target_audience, duration_weeks,
                           difficulty, prerequisites, learning_objectives, created_at
                    FROM learning_paths ORDER BY name
                """)
            
            rows = cursor.fetchall()
            cursor.close()
            
            paths = []
            for row in rows:
                paths.append({
                    "id": row[0],
                    "name": row[1],
                    "slug": row[2],
                    "description": row[3],
                    "target_audience": row[4],
                    "duration_weeks": row[5],
                    "difficulty": row[6],
                    "prerequisites": row[7],
                    "learning_objectives": row[8],
                    "created_at": row[9].isoformat() if row[9] else None
                })
            
            return paths
            
        except Exception as e:
            print(f"Error getting learning paths: {e}")
            return []
    
    def get_learning_path(self, path_id: str) -> Optional[Dict]:
        """Get a specific learning path with modules"""
        try:
            cursor = self.conn.cursor()
            
            # Get path
            cursor.execute("""
                SELECT id, name, slug, description, target_audience, duration_weeks,
                       difficulty, prerequisites, learning_objectives
                FROM learning_paths WHERE id = %s
            """, (path_id,))
            
            row = cursor.fetchone()
            if not row:
                return None
            
            path = {
                "id": row[0],
                "name": row[1],
                "slug": row[2],
                "description": row[3],
                "target_audience": row[4],
                "duration_weeks": row[5],
                "difficulty": row[6],
                "prerequisites": row[7],
                "learning_objectives": row[8]
            }
            
            # Get modules
            cursor.execute("""
                SELECT id, module_number, title, slug, description, 
                       learning_objectives, estimated_minutes, is_required
                FROM learning_modules WHERE path_id = %s ORDER BY module_number
            """, (path_id,))
            
            modules = []
            for mod_row in cursor.fetchall():
                modules.append({
                    "id": mod_row[0],
                    "module_number": mod_row[1],
                    "title": mod_row[2],
                    "slug": mod_row[3],
                    "description": mod_row[4],
                    "learning_objectives": mod_row[5],
                    "estimated_minutes": mod_row[6],
                    "is_required": mod_row[7]
                })
            
            path['modules'] = modules
            cursor.close()
            
            return path
            
        except Exception as e:
            print(f"Error getting learning path: {e}")
            return None
    
    # ===== MODULES =====
    
    def create_module(self, module_data: Dict) -> Dict:
        """Create a new module"""
        try:
            module_id = str(uuid.uuid4())
            cursor = self.conn.cursor()
            
            cursor.execute("""
                INSERT INTO learning_modules 
                (id, path_id, module_number, title, slug, description, 
                 learning_objectives, estimated_minutes, is_required)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (
                module_id,
                module_data['path_id'],
                module_data['module_number'],
                module_data['title'],
                module_data['slug'],
                module_data.get('description'),
                module_data.get('learning_objectives', []),
                module_data.get('estimated_minutes'),
                module_data.get('is_required', True)
            ))
            
            self.conn.commit()
            cursor.close()
            
            return {"success": True, "module_id": module_id}
            
        except Exception as e:
            self.conn.rollback()
            return {"success": False, "error": str(e)}
    
    def get_module_with_lessons(self, module_id: str) -> Optional[Dict]:
        """Get a module with all its lessons"""
        try:
            cursor = self.conn.cursor()
            
            # Get module
            cursor.execute("""
                SELECT id, path_id, module_number, title, slug, description,
                       learning_objectives, estimated_minutes, is_required
                FROM learning_modules WHERE id = %s
            """, (module_id,))
            
            row = cursor.fetchone()
            if not row:
                return None
            
            module = {
                "id": row[0],
                "path_id": row[1],
                "module_number": row[2],
                "title": row[3],
                "slug": row[4],
                "description": row[5],
                "learning_objectives": row[6],
                "estimated_minutes": row[7],
                "is_required": row[8]
            }
            
            # Get lessons
            cursor.execute("""
                SELECT id, lesson_number, title, slug, lesson_type, content,
                       video_url, video_duration_seconds, resources, estimated_minutes, is_required
                FROM learning_lessons WHERE module_id = %s ORDER BY lesson_number
            """, (module_id,))
            
            lessons = []
            for les_row in cursor.fetchall():
                lessons.append({
                    "id": les_row[0],
                    "lesson_number": les_row[1],
                    "title": les_row[2],
                    "slug": les_row[3],
                    "lesson_type": les_row[4],
                    "content": les_row[5],
                    "video_url": les_row[6],
                    "video_duration_seconds": les_row[7],
                    "resources": les_row[8],
                    "estimated_minutes": les_row[9],
                    "is_required": les_row[10]
                })
            
            module['lessons'] = lessons
            cursor.close()
            
            return module
            
        except Exception as e:
            print(f"Error getting module: {e}")
            return None
    
    # ===== LESSONS =====
    
    def create_lesson(self, lesson_data: Dict) -> Dict:
        """Create a new lesson"""
        try:
            lesson_id = str(uuid.uuid4())
            cursor = self.conn.cursor()
            
            cursor.execute("""
                INSERT INTO learning_lessons 
                (id, module_id, lesson_number, title, slug, lesson_type, content,
                 video_url, video_duration_seconds, resources, estimated_minutes, is_required)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (
                lesson_id,
                lesson_data['module_id'],
                lesson_data['lesson_number'],
                lesson_data['title'],
                lesson_data['slug'],
                lesson_data['lesson_type'],
                lesson_data.get('content'),
                lesson_data.get('video_url'),
                lesson_data.get('video_duration_seconds'),
                json.dumps(lesson_data.get('resources', {})),
                lesson_data.get('estimated_minutes'),
                lesson_data.get('is_required', True)
            ))
            
            self.conn.commit()
            cursor.close()
            
            return {"success": True, "lesson_id": lesson_id}
            
        except Exception as e:
            self.conn.rollback()
            return {"success": False, "error": str(e)}
    
    def get_lesson(self, lesson_id: str) -> Optional[Dict]:
        """Get a specific lesson with quiz questions"""
        try:
            cursor = self.conn.cursor()
            
            # Get lesson
            cursor.execute("""
                SELECT id, module_id, lesson_number, title, slug, lesson_type, content,
                       video_url, video_duration_seconds, resources, estimated_minutes, is_required
                FROM learning_lessons WHERE id = %s
            """, (lesson_id,))
            
            row = cursor.fetchone()
            if not row:
                return None
            
            lesson = {
                "id": row[0],
                "module_id": row[1],
                "lesson_number": row[2],
                "title": row[3],
                "slug": row[4],
                "lesson_type": row[5],
                "content": row[6],
                "video_url": row[7],
                "video_duration_seconds": row[8],
                "resources": row[9],
                "estimated_minutes": row[10],
                "is_required": row[11]
            }
            
            # Get quiz questions if it's a quiz lesson
            if lesson['lesson_type'] == 'quiz':
                cursor.execute("""
                    SELECT id, question_number, question_text, question_type, options,
                           correct_answer, explanation, points
                    FROM quiz_questions WHERE lesson_id = %s ORDER BY question_number
                """, (lesson_id,))
                
                questions = []
                for q_row in cursor.fetchall():
                    questions.append({
                        "id": q_row[0],
                        "question_number": q_row[1],
                        "question_text": q_row[2],
                        "question_type": q_row[3],
                        "options": q_row[4],
                        "correct_answer": q_row[5],  # Only include for grading
                        "explanation": q_row[6],
                        "points": q_row[7]
                    })
                
                lesson['quiz_questions'] = questions
            
            cursor.close()
            return lesson
            
        except Exception as e:
            print(f"Error getting lesson: {e}")
            return None
    
    # ===== PROGRESS TRACKING =====
    
    def start_lesson(self, user_id: str, lesson_id: str) -> Dict:
        """Mark a lesson as started"""
        try:
            cursor = self.conn.cursor()
            
            # Get module and path info
            cursor.execute("""
                SELECT m.path_id, m.id
                FROM learning_lessons l
                JOIN learning_modules m ON l.module_id = m.id
                WHERE l.id = %s
            """, (lesson_id,))
            
            row = cursor.fetchone()
            if not row:
                return {"success": False, "error": "Lesson not found"}
            
            path_id, module_id = row
            
            # Check if progress already exists
            cursor.execute("""
                SELECT id, status FROM user_learning_progress 
                WHERE user_id = %s AND lesson_id = %s
            """, (user_id, lesson_id))
            
            existing = cursor.fetchone()
            
            if existing:
                # Update to in_progress if not already completed
                if existing[1] != 'completed':
                    cursor.execute("""
                        UPDATE user_learning_progress 
                        SET status = 'in_progress', last_accessed_at = %s, updated_at = %s
                        WHERE id = %s
                    """, (datetime.now(), datetime.now(), existing[0]))
            else:
                # Create new progress record
                progress_id = str(uuid.uuid4())
                cursor.execute("""
                    INSERT INTO user_learning_progress 
                    (id, user_id, path_id, module_id, lesson_id, status, started_at, last_accessed_at)
                    VALUES (%s, %s, %s, %s, %s, 'in_progress', %s, %s)
                """, (progress_id, user_id, path_id, module_id, lesson_id, datetime.now(), datetime.now()))
            
            self.conn.commit()
            cursor.close()
            
            return {"success": True}
            
        except Exception as e:
            self.conn.rollback()
            return {"success": False, "error": str(e)}
    
    def complete_lesson(self, user_id: str, lesson_id: str, time_spent_minutes: int = 0) -> Dict:
        """Mark a lesson as completed"""
        try:
            cursor = self.conn.cursor()
            
            # Update progress
            cursor.execute("""
                UPDATE user_learning_progress 
                SET status = 'completed', progress_percent = 100, 
                    completed_at = %s, time_spent_minutes = %s, updated_at = %s
                WHERE user_id = %s AND lesson_id = %s
            """, (datetime.now(), time_spent_minutes, datetime.now(), user_id, lesson_id))
            
            # Award achievement
            self.award_achievement(user_id, 'lesson_completed', f'Completed lesson', {
                'lesson_id': lesson_id
            })
            
            # Check if module is complete
            cursor.execute("""
                SELECT m.id, m.title,
                       COUNT(l.id) as total_lessons,
                       COUNT(CASE WHEN ulp.status = 'completed' THEN 1 END) as completed_lessons
                FROM learning_lessons l
                JOIN learning_modules m ON l.module_id = m.id
                LEFT JOIN user_learning_progress ulp ON l.id = ulp.lesson_id AND ulp.user_id = %s
                WHERE l.id = %s
                GROUP BY m.id, m.title
            """, (user_id, lesson_id))
            
            row = cursor.fetchone()
            if row and row[2] == row[3]:  # All lessons complete
                self.award_achievement(user_id, 'module_completed', f'Completed module: {row[1]}', {
                    'module_id': row[0]
                })
            
            self.conn.commit()
            cursor.close()
            
            return {"success": True}
            
        except Exception as e:
            self.conn.rollback()
            return {"success": False, "error": str(e)}
    
    def get_user_progress(self, user_id: str, path_id: Optional[str] = None) -> Dict:
        """Get user's learning progress"""
        try:
            cursor = self.conn.cursor()
            
            if path_id:
                cursor.execute("""
                    SELECT 
                        COUNT(DISTINCT l.id) as total_lessons,
                        COUNT(DISTINCT CASE WHEN ulp.status = 'completed' THEN l.id END) as completed_lessons,
                        COUNT(DISTINCT CASE WHEN ulp.status = 'in_progress' THEN l.id END) as in_progress_lessons,
                        SUM(COALESCE(ulp.time_spent_minutes, 0)) as total_time_minutes
                    FROM learning_lessons l
                    JOIN learning_modules m ON l.module_id = m.id
                    LEFT JOIN user_learning_progress ulp ON l.id = ulp.lesson_id AND ulp.user_id = %s
                    WHERE m.path_id = %s
                """, (user_id, path_id))
            else:
                cursor.execute("""
                    SELECT 
                        COUNT(DISTINCT l.id) as total_lessons,
                        COUNT(DISTINCT CASE WHEN ulp.status = 'completed' THEN l.id END) as completed_lessons,
                        COUNT(DISTINCT CASE WHEN ulp.status = 'in_progress' THEN l.id END) as in_progress_lessons,
                        SUM(COALESCE(ulp.time_spent_minutes, 0)) as total_time_minutes
                    FROM learning_lessons l
                    LEFT JOIN user_learning_progress ulp ON l.id = ulp.lesson_id AND ulp.user_id = %s
                """, (user_id,))
            
            row = cursor.fetchone()
            cursor.close()
            
            total = row[0] or 0
            completed = row[1] or 0
            in_progress = row[2] or 0
            time_spent = row[3] or 0
            
            progress_percent = int((completed / total * 100)) if total > 0 else 0
            
            return {
                "total_lessons": total,
                "completed_lessons": completed,
                "in_progress_lessons": in_progress,
                "not_started_lessons": total - completed - in_progress,
                "progress_percent": progress_percent,
                "total_time_minutes": int(time_spent)
            }
            
        except Exception as e:
            print(f"Error getting user progress: {e}")
            return {}
    
    # ===== QUIZZES =====
    
    def submit_quiz(self, user_id: str, lesson_id: str, answers: Dict) -> Dict:
        """Submit quiz answers and calculate score"""
        try:
            cursor = self.conn.cursor()
            
            # Get quiz questions
            cursor.execute("""
                SELECT id, question_number, correct_answer, points
                FROM quiz_questions WHERE lesson_id = %s
            """, (lesson_id,))
            
            questions = cursor.fetchall()
            if not questions:
                return {"success": False, "error": "No quiz questions found"}
            
            # Calculate score
            score = 0
            max_score = 0
            results = []
            
            for q in questions:
                q_id, q_num, correct, points = q
                max_score += points
                user_answer = answers.get(str(q_num))
                is_correct = str(user_answer).strip().lower() == str(correct).strip().lower()
                
                if is_correct:
                    score += points
                
                results.append({
                    "question_number": q_num,
                    "correct": is_correct,
                    "user_answer": user_answer,
                    "correct_answer": correct
                })
            
            # Determine if passed (70% threshold)
            passed = (score / max_score) >= 0.7 if max_score > 0 else False
            
            # Get attempt number
            cursor.execute("""
                SELECT COALESCE(MAX(attempt_number), 0) + 1
                FROM quiz_attempts WHERE user_id = %s AND lesson_id = %s
            """, (user_id, lesson_id))
            
            attempt_number = cursor.fetchone()[0]
            
            # Save attempt
            attempt_id = str(uuid.uuid4())
            cursor.execute("""
                INSERT INTO quiz_attempts 
                (id, user_id, lesson_id, attempt_number, score, max_score, passed, answers)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """, (attempt_id, user_id, lesson_id, attempt_number, score, max_score, passed, json.dumps(results)))
            
            # If passed, mark lesson as complete
            if passed:
                self.complete_lesson(user_id, lesson_id)
                self.award_achievement(user_id, 'quiz_passed', f'Passed quiz', {
                    'lesson_id': lesson_id,
                    'score': score,
                    'max_score': max_score
                })
            
            self.conn.commit()
            cursor.close()
            
            return {
                "success": True,
                "score": score,
                "max_score": max_score,
                "percentage": int((score / max_score * 100)) if max_score > 0 else 0,
                "passed": passed,
                "attempt_number": attempt_number,
                "results": results
            }
            
        except Exception as e:
            self.conn.rollback()
            return {"success": False, "error": str(e)}
    
    # ===== ACHIEVEMENTS =====
    
    def award_achievement(self, user_id: str, achievement_type: str, achievement_name: str, metadata: Dict = None) -> Dict:
        """Award an achievement to a user"""
        try:
            achievement_id = str(uuid.uuid4())
            cursor = self.conn.cursor()
            
            # Map achievement types to icons
            icon_map = {
                'lesson_completed': '✅',
                'module_completed': '🎓',
                'path_completed': '🏆',
                'quiz_passed': '💯',
                'streak': '🔥',
                'first_deal': '🎉'
            }
            
            cursor.execute("""
                INSERT INTO user_achievements 
                (id, user_id, achievement_type, achievement_name, badge_icon, metadata)
                VALUES (%s, %s, %s, %s, %s, %s)
            """, (
                achievement_id,
                user_id,
                achievement_type,
                achievement_name,
                icon_map.get(achievement_type, '⭐'),
                json.dumps(metadata) if metadata else None
            ))
            
            self.conn.commit()
            cursor.close()
            
            return {"success": True, "achievement_id": achievement_id}
            
        except Exception as e:
            self.conn.rollback()
            return {"success": False, "error": str(e)}
    
    def get_user_achievements(self, user_id: str) -> List[Dict]:
        """Get all achievements for a user"""
        try:
            cursor = self.conn.cursor()
            
            cursor.execute("""
                SELECT id, achievement_type, achievement_name, achievement_description,
                       badge_icon, metadata, earned_at
                FROM user_achievements 
                WHERE user_id = %s 
                ORDER BY earned_at DESC
            """, (user_id,))
            
            rows = cursor.fetchall()
            cursor.close()
            
            achievements = []
            for row in rows:
                achievements.append({
                    "id": row[0],
                    "achievement_type": row[1],
                    "achievement_name": row[2],
                    "achievement_description": row[3],
                    "badge_icon": row[4],
                    "metadata": row[5],
                    "earned_at": row[6].isoformat() if row[6] else None
                })
            
            return achievements
            
        except Exception as e:
            print(f"Error getting achievements: {e}")
            return []
    
    # ===== CERTIFICATES =====
    
    def issue_certificate(self, user_id: str, path_id: str) -> Dict:
        """Issue a certificate for completing a learning path"""
        try:
            # Check if path is complete
            progress = self.get_user_progress(user_id, path_id)
            if progress.get('progress_percent', 0) < 100:
                return {"success": False, "error": "Path not completed"}
            
            certificate_id = str(uuid.uuid4())
            certificate_number = f"UWP-{datetime.now().year}-{certificate_id[:8].upper()}"
            
            cursor = self.conn.cursor()
            
            cursor.execute("""
                INSERT INTO user_certificates 
                (id, user_id, path_id, certificate_number)
                VALUES (%s, %s, %s, %s)
            """, (certificate_id, user_id, path_id, certificate_number))
            
            # Award achievement
            self.award_achievement(user_id, 'path_completed', 'Completed learning path', {
                'path_id': path_id,
                'certificate_number': certificate_number
            })
            
            self.conn.commit()
            cursor.close()
            
            return {
                "success": True,
                "certificate_id": certificate_id,
                "certificate_number": certificate_number
            }
            
        except Exception as e:
            self.conn.rollback()
            return {"success": False, "error": str(e)}
