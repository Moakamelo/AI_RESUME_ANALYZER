from typing import Optional, Dict, Any, List
from datetime import datetime
from pydantic import BaseModel, EmailStr, Field, validator

class ResumeBase(BaseModel):
    filename: str
    file_type: str

class ResumeCreate(BaseModel):
    original_filename: str

class ResumeResponse(ResumeBase):
    id: int
    user_id: int
    file_size: int
    upload_date: datetime
    is_active: bool
    
    class Config:
        from_attributes = True
