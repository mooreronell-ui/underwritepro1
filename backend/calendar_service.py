"""
Calendar and Scheduling Service
Manages appointments, availability, and calendar integrations
"""

from datetime import datetime, timedelta
from typing import List, Dict, Optional
import uuid
from database_unified import get_db_connection

class CalendarService:
    """Service for managing calendars and appointments"""
    
    def __init__(self):
        self.conn = get_db_connection()
    
    # Calendar Management
    def create_calendar(self, user_id: str, name: str, timezone: str = "UTC", 
                       settings: Optional[Dict] = None) -> Dict:
        """Create a new calendar"""
        calendar_id = str(uuid.uuid4())
        cursor = self.conn.cursor()
        
        cursor.execute("""
            INSERT INTO calendars (id, user_id, name, timezone, settings, created_at)
            VALUES (%s, %s, %s, %s, %s, %s)
        """, (calendar_id, user_id, name, timezone, str(settings or {}), datetime.utcnow()))
        
        self.conn.commit()
        
        return {
            "id": calendar_id,
            "user_id": user_id,
            "name": name,
            "timezone": timezone,
            "settings": settings or {}
        }
    
    def get_user_calendars(self, user_id: str) -> List[Dict]:
        """Get all calendars for a user"""
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT id, name, timezone, settings, is_default, created_at
            FROM calendars
            WHERE user_id = %s
            ORDER BY is_default DESC, created_at DESC
        """, (user_id,))
        
        calendars = []
        for row in cursor.fetchall():
            calendars.append({
                "id": row[0],
                "name": row[1],
                "timezone": row[2],
                "settings": eval(row[3]) if row[3] else {},
                "is_default": row[4],
                "created_at": row[5].isoformat() if row[5] else None
            })
        
        return calendars
    
    # Appointment Management
    def create_appointment(self, calendar_id: str, title: str, start_time: datetime,
                          end_time: datetime, attendees: List[str] = None,
                          location: Optional[str] = None, description: Optional[str] = None,
                          deal_id: Optional[str] = None, borrower_id: Optional[str] = None) -> Dict:
        """Create a new appointment"""
        appointment_id = str(uuid.uuid4())
        cursor = self.conn.cursor()
        
        cursor.execute("""
            INSERT INTO appointments (id, calendar_id, title, description, start_time, 
                                    end_time, location, attendees, deal_id, borrower_id,
                                    status, created_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """, (appointment_id, calendar_id, title, description, start_time, end_time,
              location, str(attendees or []), deal_id, borrower_id, 'scheduled', datetime.utcnow()))
        
        self.conn.commit()
        
        # Create automatic reminders
        self._create_default_reminders(appointment_id, start_time)
        
        return {
            "id": appointment_id,
            "calendar_id": calendar_id,
            "title": title,
            "description": description,
            "start_time": start_time.isoformat(),
            "end_time": end_time.isoformat(),
            "location": location,
            "attendees": attendees or [],
            "deal_id": deal_id,
            "borrower_id": borrower_id,
            "status": "scheduled"
        }
    
    def get_appointments(self, calendar_id: str, start_date: datetime, 
                        end_date: datetime) -> List[Dict]:
        """Get appointments for a calendar within a date range"""
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT id, title, description, start_time, end_time, location, 
                   attendees, deal_id, borrower_id, status
            FROM appointments
            WHERE calendar_id = %s 
              AND start_time >= %s 
              AND start_time <= %s
            ORDER BY start_time ASC
        """, (calendar_id, start_date, end_date))
        
        appointments = []
        for row in cursor.fetchall():
            appointments.append({
                "id": row[0],
                "title": row[1],
                "description": row[2],
                "start_time": row[3].isoformat() if row[3] else None,
                "end_time": row[4].isoformat() if row[4] else None,
                "location": row[5],
                "attendees": eval(row[6]) if row[6] else [],
                "deal_id": row[7],
                "borrower_id": row[8],
                "status": row[9]
            })
        
        return appointments
    
    def update_appointment(self, appointment_id: str, **kwargs) -> Dict:
        """Update an appointment"""
        cursor = self.conn.cursor()
        
        # Build dynamic update query
        update_fields = []
        values = []
        
        allowed_fields = ['title', 'description', 'start_time', 'end_time', 
                         'location', 'status', 'attendees']
        
        for field in allowed_fields:
            if field in kwargs:
                update_fields.append(f"{field} = %s")
                value = kwargs[field]
                if field == 'attendees':
                    value = str(value)
                values.append(value)
        
        if not update_fields:
            return {"error": "No fields to update"}
        
        values.append(appointment_id)
        query = f"UPDATE appointments SET {', '.join(update_fields)} WHERE id = %s"
        
        cursor.execute(query, values)
        self.conn.commit()
        
        return self.get_appointment(appointment_id)
    
    def get_appointment(self, appointment_id: str) -> Optional[Dict]:
        """Get a specific appointment"""
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT id, calendar_id, title, description, start_time, end_time, 
                   location, attendees, deal_id, borrower_id, status
            FROM appointments
            WHERE id = %s
        """, (appointment_id,))
        
        row = cursor.fetchone()
        if not row:
            return None
        
        return {
            "id": row[0],
            "calendar_id": row[1],
            "title": row[2],
            "description": row[3],
            "start_time": row[4].isoformat() if row[4] else None,
            "end_time": row[5].isoformat() if row[5] else None,
            "location": row[6],
            "attendees": eval(row[7]) if row[7] else [],
            "deal_id": row[8],
            "borrower_id": row[9],
            "status": row[10]
        }
    
    def cancel_appointment(self, appointment_id: str, reason: Optional[str] = None) -> Dict:
        """Cancel an appointment"""
        cursor = self.conn.cursor()
        cursor.execute("""
            UPDATE appointments 
            SET status = 'cancelled', cancellation_reason = %s
            WHERE id = %s
        """, (reason, appointment_id))
        
        self.conn.commit()
        
        return {"success": True, "message": "Appointment cancelled"}
    
    # Reminder Management
    def _create_default_reminders(self, appointment_id: str, start_time: datetime):
        """Create default reminders for an appointment"""
        cursor = self.conn.cursor()
        
        # 24 hours before
        reminder_time_24h = start_time - timedelta(hours=24)
        cursor.execute("""
            INSERT INTO appointment_reminders (id, appointment_id, reminder_time, 
                                              reminder_type, status, created_at)
            VALUES (%s, %s, %s, %s, %s, %s)
        """, (str(uuid.uuid4()), appointment_id, reminder_time_24h, 'email', 
              'pending', datetime.utcnow()))
        
        # 1 hour before
        reminder_time_1h = start_time - timedelta(hours=1)
        cursor.execute("""
            INSERT INTO appointment_reminders (id, appointment_id, reminder_time, 
                                              reminder_type, status, created_at)
            VALUES (%s, %s, %s, %s, %s, %s)
        """, (str(uuid.uuid4()), appointment_id, reminder_time_1h, 'sms', 
              'pending', datetime.utcnow()))
        
        self.conn.commit()
    
    def get_pending_reminders(self) -> List[Dict]:
        """Get all pending reminders that need to be sent"""
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT r.id, r.appointment_id, r.reminder_time, r.reminder_type,
                   a.title, a.start_time, a.attendees
            FROM appointment_reminders r
            JOIN appointments a ON r.appointment_id = a.id
            WHERE r.status = 'pending'
              AND r.reminder_time <= %s
            ORDER BY r.reminder_time ASC
        """, (datetime.utcnow(),))
        
        reminders = []
        for row in cursor.fetchall():
            reminders.append({
                "reminder_id": row[0],
                "appointment_id": row[1],
                "reminder_time": row[2].isoformat() if row[2] else None,
                "reminder_type": row[3],
                "appointment_title": row[4],
                "appointment_start": row[5].isoformat() if row[5] else None,
                "attendees": eval(row[6]) if row[6] else []
            })
        
        return reminders
    
    def mark_reminder_sent(self, reminder_id: str):
        """Mark a reminder as sent"""
        cursor = self.conn.cursor()
        cursor.execute("""
            UPDATE appointment_reminders 
            SET status = 'sent', sent_at = %s
            WHERE id = %s
        """, (datetime.utcnow(), reminder_id))
        
        self.conn.commit()
    
    # Availability Management
    def check_availability(self, calendar_id: str, start_time: datetime, 
                          end_time: datetime) -> bool:
        """Check if a time slot is available"""
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT COUNT(*) FROM appointments
            WHERE calendar_id = %s
              AND status != 'cancelled'
              AND (
                  (start_time <= %s AND end_time > %s) OR
                  (start_time < %s AND end_time >= %s) OR
                  (start_time >= %s AND end_time <= %s)
              )
        """, (calendar_id, start_time, start_time, end_time, end_time, 
              start_time, end_time))
        
        count = cursor.fetchone()[0]
        return count == 0
    
    def get_available_slots(self, calendar_id: str, date: datetime, 
                           duration_minutes: int = 60) -> List[Dict]:
        """Get available time slots for a given date"""
        # Business hours: 9 AM to 5 PM
        start_of_day = date.replace(hour=9, minute=0, second=0, microsecond=0)
        end_of_day = date.replace(hour=17, minute=0, second=0, microsecond=0)
        
        available_slots = []
        current_time = start_of_day
        
        while current_time < end_of_day:
            slot_end = current_time + timedelta(minutes=duration_minutes)
            
            if slot_end <= end_of_day:
                if self.check_availability(calendar_id, current_time, slot_end):
                    available_slots.append({
                        "start_time": current_time.isoformat(),
                        "end_time": slot_end.isoformat(),
                        "duration_minutes": duration_minutes
                    })
            
            current_time += timedelta(minutes=30)  # 30-minute intervals
        
        return available_slots
    
    # Statistics
    def get_calendar_stats(self, calendar_id: str) -> Dict:
        """Get statistics for a calendar"""
        cursor = self.conn.cursor()
        
        # Total appointments
        cursor.execute("""
            SELECT COUNT(*) FROM appointments
            WHERE calendar_id = %s
        """, (calendar_id,))
        total_appointments = cursor.fetchone()[0]
        
        # Upcoming appointments
        cursor.execute("""
            SELECT COUNT(*) FROM appointments
            WHERE calendar_id = %s
              AND start_time > %s
              AND status = 'scheduled'
        """, (calendar_id, datetime.utcnow()))
        upcoming_appointments = cursor.fetchone()[0]
        
        # Completed appointments
        cursor.execute("""
            SELECT COUNT(*) FROM appointments
            WHERE calendar_id = %s
              AND status = 'completed'
        """, (calendar_id,))
        completed_appointments = cursor.fetchone()[0]
        
        # Cancelled appointments
        cursor.execute("""
            SELECT COUNT(*) FROM appointments
            WHERE calendar_id = %s
              AND status = 'cancelled'
        """, (calendar_id,))
        cancelled_appointments = cursor.fetchone()[0]
        
        return {
            "total_appointments": total_appointments,
            "upcoming_appointments": upcoming_appointments,
            "completed_appointments": completed_appointments,
            "cancelled_appointments": cancelled_appointments
        }
