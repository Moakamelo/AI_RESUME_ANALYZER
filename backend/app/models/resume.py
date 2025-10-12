from sqlalchemy import Column, Integer, String, DateTime, Text, ForeignKey, JSON, Boolean, Float
from sqlalchemy.orm import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime
from app.core.database import Base

class Resume(Base):
    __tablename__ = "resumes"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    filename = Column(String, nullable=False)
    file_path = Column(String, nullable=False)  # Path to stored file
    file_size = Column(Integer)  # File size in bytes
    file_type = Column(String)   # pdf, docx, txt
    original_filename = Column(String)
    upload_date = Column(DateTime, default=datetime.utcnow)
    is_active = Column(Boolean, default=True)
    
    # Extracted content (for faster analysis)
    extracted_text = Column(Text)
    
    # Relationships
    user = relationship("User", back_populates="resumes")
    job_applications = relationship("JobApplication", back_populates="resume")