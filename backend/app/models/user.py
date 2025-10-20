from sqlalchemy import Column, Integer, String, Boolean, DateTime
from sqlalchemy.orm import relationship
from app.core.database import Base
from datetime import datetime

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True, nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)
    name = Column(String, nullable=False)
    surname = Column(String, nullable=False)
    
    # Hashed South African ID number (never store plain text)
    hashed_sa_id = Column(String, unique=True, index=True, nullable=False)
    
    # Password (hashed)
    hashed_password = Column(String, nullable=False)
    
    # Consent management
    consent_popi = Column(Boolean, default=False, nullable=False)
    consent_terms = Column(Boolean, default=False, nullable=False)
    consent_given_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # Account status
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    resumes = relationship("Resume", back_populates="user")