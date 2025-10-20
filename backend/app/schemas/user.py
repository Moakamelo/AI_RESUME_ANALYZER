from pydantic import BaseModel, EmailStr, validator
from typing import Optional
from datetime import datetime

class UserBase(BaseModel):
    username: str
    email: EmailStr
    name: str
    surname: str

class UserCreate(UserBase):
    sa_id_number: str
    password: str
    consent_popi: bool
    consent_terms: bool


    @validator('consent_popi')
    def validate_popi_consent(cls, v):
        if not v:
            raise ValueError('POPI Act consent is required to use this service')
        return v

    @validator('consent_terms')
    def validate_terms_consent(cls, v):
        if not v:
            raise ValueError('Terms and conditions consent is required')
        return v

    @validator('password')
    def validate_password(cls, v):
        if len(v) < 8:
            raise ValueError('Password must be at least 8 characters long')
        return v

class UserResponse(UserBase):
    id: int
    is_active: bool
    created_at: datetime
    consent_popi: bool
    consent_terms: bool
    consent_given_at: datetime

    class Config:
        from_attributes = True

class UserUpdate(BaseModel):
    email: Optional[EmailStr] = None
    name: Optional[str] = None
    surname: Optional[str] = None