"""
API Routes for New Features
Onboarding, LMS, Practice Mode, and Gamification
"""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from auth import get_current_user
from onboarding_service import OnboardingService
from lms_service import LMSService
from practice_gamification_service import PracticeGamificationService

router = APIRouter()

# Initialize services
onboarding_service = OnboardingService()
lms_service = LMSService()
practice_service = PracticeGamificationService()

# ===== PYDANTIC MODELS =====

class UserProfileUpdate(BaseModel):
    user_type: str
    experience_level: Optional[str] = None
    goals: Optional[List[str]] = None
    interests: Optional[List[str]] = None

class OnboardingStepComplete(BaseModel):
    step_name: str
    step_data: Optional[Dict] = None

class LessonProgress(BaseModel):
    time_spent_minutes: Optional[int] = 0

class QuizSubmission(BaseModel):
    answers: Dict[str, Any]

class PracticeDealSubmission(BaseModel):
    deal_data: Dict[str, Any]

# ===== ONBOARDING ROUTES =====

@router.post("/onboarding/profile")
async def update_user_profile(
    profile: UserProfileUpdate,
    current_user: dict = Depends(get_current_user)
):
    """Update user profile with segmentation data"""
    result = onboarding_service.update_user_profile(
        current_user['user_id'],
        profile.dict()
    )
    
    if not result.get('success'):
        raise HTTPException(status_code=400, detail=result.get('error'))
    
    return result

@router.get("/onboarding/flow/{user_type}")
async def get_onboarding_flow(
    user_type: str,
    current_user: dict = Depends(get_current_user)
):
    """Get onboarding flow for user type"""
    flow = onboarding_service.get_onboarding_flow(user_type)
    
    if not flow:
        raise HTTPException(status_code=404, detail="Onboarding flow not found")
    
    return flow

@router.get("/onboarding/progress")
async def get_onboarding_progress(
    current_user: dict = Depends(get_current_user)
):
    """Get user's onboarding progress"""
    progress = onboarding_service.get_user_onboarding_progress(current_user['user_id'])
    return progress

@router.post("/onboarding/step/complete")
async def complete_onboarding_step(
    step: OnboardingStepComplete,
    current_user: dict = Depends(get_current_user)
):
    """Mark an onboarding step as complete"""
    result = onboarding_service.complete_onboarding_step(
        current_user['user_id'],
        step.step_name,
        step.step_data
    )
    
    if not result.get('success'):
        raise HTTPException(status_code=400, detail=result.get('error'))
    
    return result

# ===== LEARNING MANAGEMENT SYSTEM ROUTES =====

@router.get("/learning/paths")
async def get_learning_paths(
    target_audience: Optional[str] = None,
    current_user: dict = Depends(get_current_user)
):
    """Get all learning paths"""
    paths = lms_service.get_learning_paths(target_audience)
    return {"paths": paths}

@router.get("/learning/paths/{path_id}")
async def get_learning_path(
    path_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Get a specific learning path with modules"""
    path = lms_service.get_learning_path(path_id)
    
    if not path:
        raise HTTPException(status_code=404, detail="Learning path not found")
    
    # Add user progress
    progress = lms_service.get_user_progress(current_user['user_id'], path_id)
    path['user_progress'] = progress
    
    return path

@router.get("/learning/modules/{module_id}")
async def get_module(
    module_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Get a module with lessons"""
    module = lms_service.get_module_with_lessons(module_id)
    
    if not module:
        raise HTTPException(status_code=404, detail="Module not found")
    
    return module

@router.get("/learning/lessons/{lesson_id}")
async def get_lesson(
    lesson_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Get a specific lesson"""
    lesson = lms_service.get_lesson(lesson_id)
    
    if not lesson:
        raise HTTPException(status_code=404, detail="Lesson not found")
    
    return lesson

@router.post("/learning/lessons/{lesson_id}/start")
async def start_lesson(
    lesson_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Mark a lesson as started"""
    result = lms_service.start_lesson(current_user['user_id'], lesson_id)
    
    if not result.get('success'):
        raise HTTPException(status_code=400, detail=result.get('error'))
    
    return result

@router.post("/learning/lessons/{lesson_id}/complete")
async def complete_lesson(
    lesson_id: str,
    progress: LessonProgress,
    current_user: dict = Depends(get_current_user)
):
    """Mark a lesson as completed"""
    result = lms_service.complete_lesson(
        current_user['user_id'],
        lesson_id,
        progress.time_spent_minutes
    )
    
    if not result.get('success'):
        raise HTTPException(status_code=400, detail=result.get('error'))
    
    return result

@router.post("/learning/lessons/{lesson_id}/quiz")
async def submit_quiz(
    lesson_id: str,
    submission: QuizSubmission,
    current_user: dict = Depends(get_current_user)
):
    """Submit quiz answers"""
    result = lms_service.submit_quiz(
        current_user['user_id'],
        lesson_id,
        submission.answers
    )
    
    if not result.get('success'):
        raise HTTPException(status_code=400, detail=result.get('error'))
    
    return result

@router.get("/learning/progress")
async def get_learning_progress(
    path_id: Optional[str] = None,
    current_user: dict = Depends(get_current_user)
):
    """Get user's learning progress"""
    progress = lms_service.get_user_progress(current_user['user_id'], path_id)
    return progress

@router.get("/learning/achievements")
async def get_achievements(
    current_user: dict = Depends(get_current_user)
):
    """Get user's achievements"""
    achievements = lms_service.get_user_achievements(current_user['user_id'])
    return {"achievements": achievements}

@router.post("/learning/certificates/{path_id}")
async def request_certificate(
    path_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Request a certificate for completing a path"""
    result = lms_service.issue_certificate(current_user['user_id'], path_id)
    
    if not result.get('success'):
        raise HTTPException(status_code=400, detail=result.get('error'))
    
    return result

# ===== PRACTICE MODE ROUTES =====

@router.get("/practice/scenarios")
async def get_practice_scenarios(
    difficulty: Optional[str] = None,
    current_user: dict = Depends(get_current_user)
):
    """Get all practice scenarios"""
    scenarios = practice_service.get_practice_scenarios(difficulty)
    return {"scenarios": scenarios}

@router.get("/practice/scenarios/{scenario_id}")
async def get_practice_scenario(
    scenario_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Get a specific practice scenario"""
    scenario = practice_service.get_practice_scenario(scenario_id)
    
    if not scenario:
        raise HTTPException(status_code=404, detail="Scenario not found")
    
    return scenario

@router.post("/practice/scenarios/{scenario_id}/start")
async def start_practice_scenario(
    scenario_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Start a practice deal from a scenario"""
    result = practice_service.create_practice_deal_from_scenario(
        current_user['user_id'],
        scenario_id
    )
    
    if not result.get('success'):
        raise HTTPException(status_code=400, detail=result.get('error'))
    
    return result

@router.post("/practice/deals/{deal_id}/submit")
async def submit_practice_deal(
    deal_id: str,
    submission: PracticeDealSubmission,
    current_user: dict = Depends(get_current_user)
):
    """Submit a practice deal for feedback"""
    result = practice_service.submit_practice_deal(
        current_user['user_id'],
        deal_id,
        submission.deal_data
    )
    
    if not result.get('success'):
        raise HTTPException(status_code=400, detail=result.get('error'))
    
    return result

# ===== GAMIFICATION ROUTES =====

@router.get("/gamification/points")
async def get_user_points(
    current_user: dict = Depends(get_current_user)
):
    """Get user's points and level"""
    points = practice_service.get_user_points(current_user['user_id'])
    return points

@router.get("/gamification/badges")
async def get_user_badges(
    current_user: dict = Depends(get_current_user)
):
    """Get user's badges"""
    badges = practice_service.get_user_badges(current_user['user_id'])
    return {"badges": badges}

@router.get("/gamification/leaderboard/{leaderboard_type}/{period}")
async def get_leaderboard(
    leaderboard_type: str,
    period: str,
    limit: int = 50,
    current_user: dict = Depends(get_current_user)
):
    """Get leaderboard rankings"""
    leaderboard = practice_service.get_leaderboard(leaderboard_type, period, limit)
    return {"leaderboard": leaderboard}

@router.post("/gamification/leaderboard/{leaderboard_type}/{period}/update")
async def update_leaderboard(
    leaderboard_type: str,
    period: str,
    current_user: dict = Depends(get_current_user)
):
    """Update leaderboard rankings (admin only)"""
    # In production, add admin check here
    result = practice_service.update_leaderboard(leaderboard_type, period)
    
    if not result.get('success'):
        raise HTTPException(status_code=400, detail=result.get('error'))
    
    return result
