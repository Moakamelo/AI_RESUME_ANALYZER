# app/schemas/analysis_result.py
from typing import Optional, Dict, Any, List, Union
from datetime import datetime
from pydantic import BaseModel, ConfigDict, field_validator

class ToneStyleAnalysis(BaseModel):
    tips: Optional[List[Dict[str, Any]]] = None

class ContentAnalysis(BaseModel):
    tips: Optional[List[Dict[str, Any]]] = None

class StructureAnalysis(BaseModel):
    tips: Optional[List[Dict[str, Any]]] = None

class SkillsAnalysis(BaseModel):
    highlighted_skills: Optional[List[str]] = []
    missing_skills: Optional[List[str]] = []
    tips: Optional[List[Dict[str, Any]]] = None

class KeywordMatches(BaseModel):
    matching_keywords: Optional[List[str]] = []
    missing_keywords: Optional[List[str]] = []

class AnalysisResultBase(BaseModel):
    overall_score: Optional[float] = None
    ats_score: Optional[float] = None
    tone_style_score: Optional[float] = None
    content_score: Optional[float] = None
    structure_score: Optional[float] = None
    skills_score: Optional[float] = None
    tone_style_analysis: Optional[ToneStyleAnalysis] = None
    content_analysis: Optional[ContentAnalysis] = None
    structure_analysis: Optional[StructureAnalysis] = None
    skills_analysis: Optional[SkillsAnalysis] = None
    keyword_matches: Optional[KeywordMatches] = None
    skill_gaps: Optional[Dict[str, Any]] = None
    recommendations: Optional[List[str]] = None
    summary: Optional[str] = None
    raw_analysis: Optional[Dict[str, Any]] = None


    @field_validator('skill_gaps', mode='before')
    @classmethod
    def validate_skill_gaps(cls, v):
        """Convert empty lists to empty dicts for skill_gaps"""
        if v == [] or v is None:
            return {}
        return v

class AnalysisResultCreate(AnalysisResultBase):
    resume_id: int

class AnalysisResultResponse(AnalysisResultBase):
    id: int
    resume_id: int
    analysis_date: datetime
    ai_model_used: str
    analysis_version: str
    
    model_config = ConfigDict(from_attributes=True)


class AnalysisStatusResponse(BaseModel):
    status: str
    message: str
    job_title: Optional[str] = None
    job_description_provided: bool

class ResumeUploadResponse(BaseModel):
    id: int
    filename: str
    original_filename: str
    upload_date: datetime
    file_size: int
    preview_available: bool

class UploadResponse(BaseModel):
    resume: ResumeUploadResponse
    analysis_result: AnalysisStatusResponse

class ReanalyzeResponse(BaseModel):
    message: str
    resume_id: int
    job_title: Optional[str] = None
    job_description_provided: bool

class AnalysisHistoryResponse(BaseModel):
    resume_id: int
    resume_filename: str
    total_analyses: int
    analyses: List[AnalysisResultResponse]

class ResumeListResponse(BaseModel):
    id: int
    filename: str
    original_filename: str
    upload_date: datetime
    file_size: int
    has_analysis: bool

class ResumeListWrapper(BaseModel):
    total: int
    resumes: List[ResumeListResponse]

class CompleteAnalysisResponse(BaseModel):
    resume: ResumeUploadResponse
    analysis_result: AnalysisResultResponse