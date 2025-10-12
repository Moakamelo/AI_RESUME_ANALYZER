from typing import Optional, Dict, Any, List
from datetime import datetime
from pydantic import BaseModel, EmailStr, Field, validator


class JobApplicationBase(BaseModel):
    job_title: str
    company_name: Optional[str] = None
    years_experience_required: int
    job_description: str
    job_level: Optional[str] = "mid"

class JobApplicationCreate(JobApplicationBase):
    resume_id: int

class JobApplicationResponse(JobApplicationBase):
    id: int
    user_id: int
    resume_id: int
    application_date: datetime
    status: str
    
    class Config:
        from_attributes = True
