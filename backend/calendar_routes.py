"""
Calendar API Routes
RESTful endpoints for calendar and scheduling management
"""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime
from auth import get_current_user
from calendar_service import CalendarService

router = APIRouter(prefix="/api/calendar", tags=["Calendar"])

# Request Models
class CreateCalendarRequest(BaseModel):
    name: str
    timezone: str = "UTC"
    settings: Optional[dict] = None

class CreateAppointmentRequest(BaseModel):
    calendar_id: str
    title: str
    start_time: datetime
    end_time: datetime
    attendees: Optional[List[str]] = None
    location: Optional[str] = None
    description: Optional[str] = None
    deal_id: Optional[str] = None
    borrower_id: Optional[str] = None

class UpdateAppointmentRequest(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    location: Optional[str] = None
    status: Optional[str] = None
    attendees: Optional[List[str]] = None

class CheckAvailabilityRequest(BaseModel):
    calendar_id: str
    start_time: datetime
    end_time: datetime

# Calendar Endpoints
@router.post("/calendars")
async def create_calendar(
    request: CreateCalendarRequest,
    current_user: dict = Depends(get_current_user)
):
    """Create a new calendar"""
    service = CalendarService()
    calendar = service.create_calendar(
        user_id=current_user["id"],
        name=request.name,
        timezone=request.timezone,
        settings=request.settings
    )
    return calendar

@router.get("/calendars")
async def get_calendars(current_user: dict = Depends(get_current_user)):
    """Get all calendars for the current user"""
    service = CalendarService()
    calendars = service.get_user_calendars(current_user["id"])
    return {"calendars": calendars}

@router.get("/calendars/{calendar_id}/stats")
async def get_calendar_stats(
    calendar_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Get statistics for a calendar"""
    service = CalendarService()
    stats = service.get_calendar_stats(calendar_id)
    return stats

# Appointment Endpoints
@router.post("/appointments")
async def create_appointment(
    request: CreateAppointmentRequest,
    current_user: dict = Depends(get_current_user)
):
    """Create a new appointment"""
    service = CalendarService()
    
    # Check availability
    is_available = service.check_availability(
        request.calendar_id,
        request.start_time,
        request.end_time
    )
    
    if not is_available:
        raise HTTPException(status_code=409, detail="Time slot not available")
    
    appointment = service.create_appointment(
        calendar_id=request.calendar_id,
        title=request.title,
        start_time=request.start_time,
        end_time=request.end_time,
        attendees=request.attendees,
        location=request.location,
        description=request.description,
        deal_id=request.deal_id,
        borrower_id=request.borrower_id
    )
    return appointment

@router.get("/appointments")
async def get_appointments(
    calendar_id: str,
    start_date: datetime,
    end_date: datetime,
    current_user: dict = Depends(get_current_user)
):
    """Get appointments for a calendar within a date range"""
    service = CalendarService()
    appointments = service.get_appointments(calendar_id, start_date, end_date)
    return {"appointments": appointments}

@router.get("/appointments/{appointment_id}")
async def get_appointment(
    appointment_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Get a specific appointment"""
    service = CalendarService()
    appointment = service.get_appointment(appointment_id)
    
    if not appointment:
        raise HTTPException(status_code=404, detail="Appointment not found")
    
    return appointment

@router.put("/appointments/{appointment_id}")
async def update_appointment(
    appointment_id: str,
    request: UpdateAppointmentRequest,
    current_user: dict = Depends(get_current_user)
):
    """Update an appointment"""
    service = CalendarService()
    
    # Build update dict
    update_data = {}
    if request.title is not None:
        update_data['title'] = request.title
    if request.description is not None:
        update_data['description'] = request.description
    if request.start_time is not None:
        update_data['start_time'] = request.start_time
    if request.end_time is not None:
        update_data['end_time'] = request.end_time
    if request.location is not None:
        update_data['location'] = request.location
    if request.status is not None:
        update_data['status'] = request.status
    if request.attendees is not None:
        update_data['attendees'] = request.attendees
    
    appointment = service.update_appointment(appointment_id, **update_data)
    return appointment

@router.delete("/appointments/{appointment_id}")
async def cancel_appointment(
    appointment_id: str,
    reason: Optional[str] = None,
    current_user: dict = Depends(get_current_user)
):
    """Cancel an appointment"""
    service = CalendarService()
    result = service.cancel_appointment(appointment_id, reason)
    return result

# Availability Endpoints
@router.post("/availability/check")
async def check_availability(
    request: CheckAvailabilityRequest,
    current_user: dict = Depends(get_current_user)
):
    """Check if a time slot is available"""
    service = CalendarService()
    is_available = service.check_availability(
        request.calendar_id,
        request.start_time,
        request.end_time
    )
    return {"available": is_available}

@router.get("/availability/slots")
async def get_available_slots(
    calendar_id: str,
    date: datetime,
    duration_minutes: int = 60,
    current_user: dict = Depends(get_current_user)
):
    """Get available time slots for a given date"""
    service = CalendarService()
    slots = service.get_available_slots(calendar_id, date, duration_minutes)
    return {"slots": slots}

# Reminder Endpoints
@router.get("/reminders/pending")
async def get_pending_reminders(current_user: dict = Depends(get_current_user)):
    """Get all pending reminders (admin only)"""
    service = CalendarService()
    reminders = service.get_pending_reminders()
    return {"reminders": reminders}
