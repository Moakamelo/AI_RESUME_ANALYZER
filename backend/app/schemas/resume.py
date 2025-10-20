from typing import Optional, Dict, Any, List
from datetime import datetime
from pydantic import BaseModel, ConfigDict
from app.schemas.analysis_result import AnalysisResultResponse


class ResumeBase(BaseModel):
    filename: str
    original_filename: str
    file_type: str
    extracted_text: Optional[str] = None

class ResumeCreate(BaseModel):
    original_filename: str
    file_type: str
    file_size: int
    file_path: str
    extracted_text: Optional[str] = None

class ResumeUpdate(BaseModel):
    is_active: Optional[bool] = None
    extracted_text: Optional[str] = None

class ResumeResponse(ResumeBase):
    id: int
    user_id: int
    file_path: str
    file_size: int
    upload_date: datetime
    is_active: bool
    
    model_config = ConfigDict(from_attributes=True)

class ResumeWithAnalysisResponse(ResumeResponse):
    latest_analysis: Optional[AnalysisResultResponse] = None
    analysis_history: Optional[List[AnalysisResultResponse]] = None