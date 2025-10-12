from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.models.user import User
from app.models.resume import Resume
from app.api.dependencies import get_current_user
from app.services.file_processor import FileProcessor
from app.services.preview_generator import PreviewGenerator

router = APIRouter()

@router.post("/upload")
async def upload_resume(
    file: UploadFile,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Upload and process resume"""
    result = await FileProcessor.process_resume(file, current_user.id)
    
    # Save to database
    resume = Resume(
        user_id=current_user.id,
        filename=file.filename,
        file_path=result["file_path"],
        file_type=result["file_type"],
        file_size=result["file_size"],
        extracted_text=result["extracted_text"]
    )
    
    db.add(resume)
    db.commit()
    db.refresh(resume)
    
    return {"message": "Resume uploaded successfully", "resume_id": resume.id}

@router.get("/{resume_id}/preview")
async def get_resume_preview(
    resume_id: int,
    page: int = Query(0, ge=0),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get resume preview as image"""
    resume = db.query(Resume).filter(
        Resume.id == resume_id,
        Resume.user_id == current_user.id
    ).first()
    
    if not resume:
        raise HTTPException(404, "Resume not found")
    
    return await PreviewGenerator.get_preview_endpoint(resume.file_path, page)

@router.get("/{resume_id}/download")
async def download_resume(
    resume_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Download original resume file"""
    resume = db.query(Resume).filter(
        Resume.id == resume_id,
        Resume.user_id == current_user.id
    ).first()
    
    if not resume:
        raise HTTPException(404, "Resume not found")
    
    return FileResponse(
        resume.file_path,
        filename=resume.filename,
        media_type='application/octet-stream'
    )