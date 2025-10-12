# app/api/routes/resumes.py
from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.models.user import User
from app.models.resume import Resume
from app.api.dependencies import get_current_user
from app.services.file_processor import FileProcessor
from app.services.supabase_storage import SupabaseStorageService
from app.services.preview_generator import PreviewGenerator
import tempfile
import os
from pathlib import Path

router = APIRouter()

@router.post("/upload")
async def upload_resume(
    file: UploadFile,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Upload and process resume"""
    file_processor = FileProcessor()
    result = await file_processor.process_resume(file, current_user.id)
    
    # Save to database with Supabase file path
    resume = Resume(
        user_id=current_user.id,
        filename=result["original_filename"],  # Use the original filename
        file_path=result["file_path"],  # This should be the Supabase path like "client_1/resume_07d69fbd-ed54-4729-827a-1b8809ffeccd.pdf"
        file_type=result["file_type"],
        file_size=result["file_size"],
        extracted_text=result["extracted_text"]
    )
    
    db.add(resume)
    db.commit()
    db.refresh(resume)
    
    return {"message": "Resume uploaded successfully", "resume_id": resume.id}

@router.get("/{resume_id}/download")
async def download_resume(
    resume_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Download original resume file via signed URL"""
    resume = db.query(Resume).filter(
        Resume.id == resume_id,
        Resume.user_id == current_user.id
    ).first()
    
    if not resume:
        raise HTTPException(404, "Resume not found")
    
    storage_service = SupabaseStorageService()
    
    print(f"🔗 Creating download URL for: {resume.file_path}")
    
    # Create signed URL
    signed_url = storage_service.create_signed_url(resume.file_path)
    
    if not signed_url:
        raise HTTPException(500, f"Failed to generate download URL")
    
    return RedirectResponse(signed_url)


@router.get("/{resume_id}/preview")
async def get_resume_preview(
    resume_id: int,
    page: int = Query(1, ge=1),  # Pages start at 1 for users
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get resume preview as JPEG image"""
    resume = db.query(Resume).filter(
        Resume.id == resume_id,
        Resume.user_id == current_user.id
    ).first()
    
    if not resume:
        raise HTTPException(404, "Resume not found")
    
    print(f"🎨 Generating preview for resume {resume_id}, file: {resume.file_path}, page: {page}")
    
    # Convert to 0-based index for the generator
    page_index = page - 1
    
    preview_generator = PreviewGenerator()
    return await preview_generator.get_preview_endpoint(resume.file_path, page_index)

@router.delete("/{resume_id}")
async def delete_resume(
    resume_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Delete resume from storage and database"""
    resume = db.query(Resume).filter(
        Resume.id == resume_id,
        Resume.user_id == current_user.id
    ).first()
    
    if not resume:
        raise HTTPException(404, "Resume not found")
    
    storage_service = SupabaseStorageService()
    
    # Delete from Supabase storage using the correct file path
    delete_success = await storage_service.delete_file(resume.file_path)
    
    if not delete_success:
        raise HTTPException(500, "Failed to delete file from storage")
    
    # Delete from database
    db.delete(resume)
    db.commit()
    
    return {"message": "Resume deleted successfully"}