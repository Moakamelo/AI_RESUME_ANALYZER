from sqlalchemy import Column, Integer, String, DateTime, Text, ForeignKey, JSON, Boolean, Float
from sqlalchemy.orm import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime
from app.core.database import Base

class JobApplication(Base):
    __tablename__ = "job_applications"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    resume_id = Column(Integer, ForeignKey("resumes.id"), nullable=False)
    
    # Job information
    job_title = Column(String, nullable=False)
    company_name = Column(String)  # Optional
    years_experience_required = Column(Integer, nullable=False)
    job_description = Column(Text, nullable=False)
    job_level = Column(String)  # entry, mid, senior, executive
    
    # Application metadata
    application_date = Column(DateTime, default=datetime.utcnow)
    status = Column(String, default="analyzed")  # analyzed, submitted, interview, etc.
    
    # Relationships
    user = relationship("User", back_populates="job_applications")
    resume = relationship("Resume", back_populates="job_applications")
    analysis_results = relationship("AnalysisResult", back_populates="job_application")
