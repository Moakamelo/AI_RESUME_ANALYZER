from sqlalchemy import Column, Integer, String, DateTime, Text, ForeignKey, JSON, Boolean, Float
from sqlalchemy.orm import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime
from app.core.database import Base

class AnalysisResult(Base):
    __tablename__ = "analysis_results"
    
    id = Column(Integer, primary_key=True, index=True)
    job_application_id = Column(Integer, ForeignKey("job_applications.id"), nullable=False)
    
    # Overall scores
    overall_score = Column(Float)
    ats_score = Column(Float) 
    
    # Category scores
    tone_style_score = Column(Float)
    content_score = Column(Float)
    structure_score = Column(Float)
    skills_score = Column(Float)
    
    # Detailed feedback (store as JSON for flexibility)
    tone_style_analysis = Column(JSON)  # {score, feedback, strengths, improvements}
    content_analysis = Column(JSON)     # {score, feedback, strengths, improvements}
    structure_analysis = Column(JSON)   # {score, feedback, strengths, improvements}
    skills_analysis = Column(JSON)      # {score, feedback, strengths, improvements, matching_skills, missing_skills}
    
    # Additional analysis data
    keyword_matches = Column(JSON)      # Matching keywords from job description
    skill_gaps = Column(JSON)           # Missing skills identified
    recommendations = Column(JSON)      # List of improvement recommendations
    summary = Column(Text)              # Overall summary
    
    # Metadata
    analysis_date = Column(DateTime, default=datetime.utcnow)
    ai_model_used = Column(String, default="gpt-4")
    analysis_version = Column(String, default="1.0")
    
    # Relationships
    job_application = relationship("JobApplication", back_populates="analysis_results")
