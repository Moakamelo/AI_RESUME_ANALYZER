from typing import Optional, Dict, Any, List
from datetime import datetime
from pydantic import BaseModel, EmailStr, Field, validator
from app.schemas.resume import ResumeResponse
from app.schemas.job_application import JobApplicationResponse


class AnalysisResultBase(BaseModel):
    overall_score: float
    ats_score: Optional[float]
    tone_style_score: float
    content_score: float
    structure_score: float
    skills_score: float

class AnalysisResultResponse(AnalysisResultBase):
    id: int
    job_application_id: int
    tone_style_analysis: Dict[str, Any]
    content_analysis: Dict[str, Any]
    structure_analysis: Dict[str, Any]
    skills_analysis: Dict[str, Any]
    keyword_matches: Optional[Dict[str, Any]] = None
    skill_gaps: Optional[Dict[str, Any]] = None
    recommendations: List[str]
    summary: str
    analysis_date: datetime
    
    class Config:
        from_attributes = True

class CompleteAnalysisResponse(BaseModel):
    job_application: JobApplicationResponse
    resume: ResumeResponse
    analysis_result: AnalysisResultResponse

class AnalysisHistoryItem(BaseModel):
    id: int
    job_title: str
    company_name: Optional[str]
    application_date: datetime
    overall_score: float
    resume_filename: str
    
    class Config:
        from_attributes = True
