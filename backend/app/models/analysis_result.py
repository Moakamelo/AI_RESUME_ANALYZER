# app/models/analysis_result.py
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, JSON, Float
from sqlalchemy.orm import relationship
from app.core.database import Base
from datetime import datetime

class AnalysisResult(Base):
    __tablename__ = "analysis_results"
    
    id = Column(Integer, primary_key=True, index=True)
    resume_id = Column(Integer, ForeignKey("resumes.id"), nullable=False)
    overall_score = Column(Float)
    ats_score = Column(Float)
    tone_style_score = Column(Float)
    content_score = Column(Float)
    structure_score = Column(Float)
    skills_score = Column(Float)
    tone_style_analysis = Column(JSON)
    content_analysis = Column(JSON)
    structure_analysis = Column(JSON)
    skills_analysis = Column(JSON)
    keyword_matches = Column(JSON)
    skill_gaps = Column(JSON)
    recommendations = Column(JSON)  
    summary = Column(Text)
    raw_analysis = Column(JSON, nullable=True)
    analysis_date = Column(DateTime, default=datetime.utcnow)
    ai_model_used = Column(String, default="gemini-pro")
    analysis_version = Column(String, default="1.0")
    
    # Relationships
    resume = relationship("Resume", back_populates="analysis_results")