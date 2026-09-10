from typing import List, Optional

from pydantic import BaseModel, EmailStr, Field


class RegisterForm(BaseModel):
    name: str
    email: EmailStr
    password: str
    role: str  # "teacher" | "student"


class FaceEnrollRequest(BaseModel):
    descriptor: List[float] = Field(..., min_items=128, max_items=128)


class PollCreateRequest(BaseModel):
    subject: str
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    radius_m: float = 100.0
    anywhere_mode: bool = False
    duration_minutes: int = 15


class MarkAttendanceRequest(BaseModel):
    poll_id: int
    descriptor: List[float] = Field(..., min_items=128, max_items=128)
    latitude: Optional[float] = None
    longitude: Optional[float] = None
