from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, BackgroundTasks, Form
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.performance import timer, timing_context
from app.models.user import User
from app.models.resume import Resume
from app.models.analysis_result import AnalysisResult
from app.api.dependencies import get_current_user
from app.services.file_processor import FileProcessor
from app.services.gemini_ai import gemini_ai_service
from app.services.preview_generator import PreviewGenerator
from app.services.supabase_storage import SupabaseStorageService
from app.schemas.analysis_result import (
    AnalysisResultResponse, 
    UploadResponse,
    ReanalyzeResponse,
    AnalysisHistoryResponse,
    ResumeListWrapper,
    ResumeListResponse
)
import os
from datetime import datetime
import json
from typing import Optional
import asyncio

router = APIRouter()

@timer("structure_ai_analysis")
def structure_ai_analysis(ai_result: dict) -> dict:
    """Convert the new AI response format to our database schema"""
    try:
        # Handle service errors
        if ai_result.get("analysis_error"):
            error_result = get_error_analysis(ai_result.get("error_message", "AI service error"))
            error_result["raw_analysis"] = ai_result  # Store the error response too
            return error_result

        # Extract tips for each category to use as recommendations
        all_recommendations = []
        
        # Process ATS tips
        ats_tips = ai_result.get("ATS", {}).get("tips", [])
        for tip in ats_tips:
            if tip.get("type") == "improve":
                all_recommendations.append(f"ATS: {tip.get('tip', '')}")
        
        # Process other categories
        categories = ["toneAndStyle", "content", "structure", "skills"]
        for category in categories:
            category_data = ai_result.get(category, {})
            tips = category_data.get("tips", [])
            for tip in tips:
                if tip.get("type") == "improve":
                    all_recommendations.append(f"{category}: {tip.get('tip', '')} - {tip.get('explanation', '')}")
        
        # Extract skills analysis from skills tips
        skills_tips = ai_result.get("skills", {}).get("tips", [])
        highlighted_skills = []
        missing_skills = []
        
        for tip in skills_tips:
            tip_text = tip.get("tip", "")
            if tip.get("type") == "good" and tip_text:
                highlighted_skills.append(tip_text)
            elif tip.get("type") == "improve" and tip_text:
                missing_skills.append(tip_text)
        
        # Create a better summary
        overall_score = ai_result.get("overallScore", 50)
        summary = f"Overall score: {overall_score}/100. "
        if overall_score >= 80:
            summary += "Excellent resume with strong ATS compatibility."
        elif overall_score >= 70:
            summary += "Good resume with some areas for improvement."
        elif overall_score >= 60:
            summary += "Fair resume that needs significant improvements."
        else:
            summary += "Resume requires major revisions for ATS compatibility."
        
        # Map to our database schema
        return {
            "overall_score": overall_score,
            "ats_score": ai_result.get("ATS", {}).get("score", 50),
            "tone_style_score": ai_result.get("toneAndStyle", {}).get("score", 50),
            "content_score": ai_result.get("content", {}).get("score", 50),
            "structure_score": ai_result.get("structure", {}).get("score", 50),
            "skills_score": ai_result.get("skills", {}).get("score", 50),
            "tone_style_analysis": {
                "professionalism": {},
                "clarity": 0,
                "confidence_level": 0,
                "tips": ai_result.get("toneAndStyle", {}).get("tips", [])
            },
            "content_analysis": {
                "completeness": 0,
                "relevance": 0,
                "achievements": [],
                "tips": ai_result.get("content", {}).get("tips", [])
            },
            "structure_analysis": {
                "formatting": 0,
                "organization": 0,
                "readability": 0,
                "tips": ai_result.get("structure", {}).get("tips", [])
            },
            "skills_analysis": {
                "highlighted_skills": highlighted_skills,
                "skill_categories": [],
                "missing_skills": missing_skills,
                "tips": ai_result.get("skills", {}).get("tips", [])
            },
            "keyword_matches": {
                "matching_keywords": [],
                "missing_keywords": []
            },
            "skill_gaps": {},
            "recommendations": all_recommendations[:10],  # Limit to 10 recommendations
            "summary": summary,
            "raw_analysis": ai_result  # Store the complete raw analysis
        }
    except Exception as e:
        print(f"❌ Error structuring AI analysis: {str(e)}")
        error_result = get_error_analysis(f"Structuring error: {str(e)}")
        error_result["raw_analysis"] = {"error": str(e), "original_response": ai_result}
        return error_result

@timer("get_error_analysis")
def get_error_analysis(error_message: str) -> dict:
    """Return a standardized error analysis structure"""
    return {
        "overall_score": 50,
        "ats_score": 50,
        "tone_style_score": 50,
        "content_score": 50,
        "structure_score": 50,
        "skills_score": 50,
        "tone_style_analysis": {
            "professionalism": {},
            "clarity": 0,
            "confidence_level": 0,
            "tips": []
        },
        "content_analysis": {
            "completeness": 0,
            "relevance": 0,
            "achievements": [],
            "tips": []
        },
        "structure_analysis": {
            "formatting": 0,
            "organization": 0,
            "readability": 0,
            "tips": []
        },
        "skills_analysis": {
            "highlighted_skills": [],
            "skill_categories": [],
            "missing_skills": [],
            "tips": []
        },
        "keyword_matches": {
            "matching_keywords": [],
            "missing_keywords": []
        },
        "skill_gaps": {},
        "recommendations": ["Please try re-analyzing the resume", "Check AI service configuration"],
        "summary": f"Analysis failed: {error_message}",
        "raw_analysis": None
    }

@router.post("/upload", response_model=UploadResponse)
@timer("upload_and_analyze_resume")
async def upload_and_analyze_resume(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    job_title: Optional[str] = Form(None),
    job_description: Optional[str] = Form(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Upload resume and perform comprehensive AI analysis"""
    
    try:
        # Step 1: Process the uploaded file
        file_processor = FileProcessor()
        processed_file = await file_processor.process_resume(file, current_user.id)
        
        # Debug: Check what fields are returned
        print(f"🔍 File processor returned keys: {list(processed_file.keys())}")
        
        # Ensure saved_filename exists
        if "saved_filename" not in processed_file:
            # Extract filename from file_path as fallback
            file_path = processed_file.get("file_path", "")
            if "/" in file_path:
                processed_file["saved_filename"] = file_path.split("/")[-1]
            else:
                processed_file["saved_filename"] = file_path
            print(f"🔧 Fallback: saved_filename set to: {processed_file['saved_filename']}")
        
        if not processed_file.get("extracted_text"):
            raise HTTPException(status_code=400, detail="Could not extract text from resume")
        
        # Step 2: Save resume to database with timing
        with timing_context("database_resume_save"):
            resume = Resume(
                user_id=current_user.id,
                filename=processed_file["saved_filename"],
                file_path=processed_file["file_path"],
                file_size=processed_file["file_size"],
                file_type=file.content_type,
                original_filename=processed_file["original_filename"],
                upload_date=datetime.utcnow(),
                is_active=True,
                extracted_text=processed_file["extracted_text"]
            )
            
            db.add(resume)
            db.commit()
            db.refresh(resume)
        
        # Step 3: Analyze with AI (in background for better performance)
        background_tasks.add_task(
            perform_ai_analysis,
            resume.id,
            processed_file["extracted_text"],
            job_title,
            job_description,
            db  # Pass db session to background task
        )
        
        # Step 4: Generate preview immediately
        try:
            preview_generator = PreviewGenerator()
            preview_path = await preview_generator.generate_preview(resume.file_path)
            preview_available = True
        except Exception as e:
            print(f"⚠️ Preview generation failed: {str(e)}")
            preview_available = False
        
        # Return response with all required fields
        return {
            "resume": {
                "id": resume.id,
                "filename": resume.filename,
                "original_filename": resume.original_filename,
                "upload_date": resume.upload_date,
                "file_size": resume.file_size,
                "preview_available": preview_available
            },
            "analysis_result": {
                "status": "processing",
                "message": "AI analysis is being processed in the background",
                "job_title": job_title,
                "job_description_provided": bool(job_description)
            }
        }
    
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Upload error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")

# REMOVED DUPLICATE: Only keep one upload-and-analyze endpoint
@router.post("/upload-and-analyze", response_model=UploadResponse)
@timer("upload_and_analyze_resume_legacy")
async def upload_and_analyze_resume_legacy(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    job_title: Optional[str] = Form(None),
    job_description: Optional[str] = Form(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Legacy endpoint - redirects to /upload"""
    # Call the main function directly
    return await upload_and_analyze_resume(
        background_tasks, file, job_title, job_description, current_user, db
    )

@timer("perform_ai_analysis")
async def perform_ai_analysis(
    resume_id: int, 
    resume_text: str, 
    job_title: Optional[str], 
    job_description: Optional[str],
    db: Session  # Receive db session
):
    """Background task to perform AI analysis"""
    try:
        print(f"🤖 Starting AI analysis for resume {resume_id}")
        print(f"📋 Job Title: {job_title}")
        print(f"📄 Job Description Length: {len(job_description) if job_description else 0}")
        
        # Analyze with AI
        analysis_result = await gemini_ai_service.analyze_resume_ats(
            resume_text, 
            job_title,
            job_description
        )
        
        print(f"✅ Raw AI analysis received. Overall score: {analysis_result.get('overall_score', 'N/A')}")
        
        # Convert AI result to match our schema
        structured_analysis = structure_ai_analysis(analysis_result)
        
        print(f"✅ Structured analysis completed. Overall score: {structured_analysis['overall_score']}")
        print(f"✅ Skill gaps type: {type(structured_analysis['skill_gaps'])}")
        
        # Save analysis results with timing
        with timing_context("database_analysis_save"):
            ai_analysis = AnalysisResult(
                resume_id=resume_id,
                overall_score=structured_analysis["overall_score"],
                ats_score=structured_analysis["ats_score"],
                tone_style_score=structured_analysis["tone_style_score"],
                content_score=structured_analysis["content_score"],
                structure_score=structured_analysis["structure_score"],
                skills_score=structured_analysis["skills_score"],
                tone_style_analysis=structured_analysis["tone_style_analysis"],
                content_analysis=structured_analysis["content_analysis"],
                structure_analysis=structured_analysis["structure_analysis"],
                skills_analysis=structured_analysis["skills_analysis"],
                keyword_matches=structured_analysis["keyword_matches"],
                skill_gaps=structured_analysis["skill_gaps"],
                recommendations=structured_analysis["recommendations"],
                summary=structured_analysis["summary"],
                analysis_date=datetime.utcnow(),
                ai_model_used="gemini-2.0-flash-exp",
                analysis_version="1.0"
            )
            
            db.add(ai_analysis)
            db.commit()
        
        print(f"✅ AI analysis saved to database for resume {resume_id}")
        
    except Exception as e:
        print(f"❌ AI analysis failed for resume {resume_id}: {str(e)}")
        
        # Save error analysis with timing
        try:
            with timing_context("database_error_save"):
                error_analysis = AnalysisResult(
                    resume_id=resume_id,
                    overall_score=50,
                    ats_score=50,
                    tone_style_score=50,
                    content_score=50,
                    structure_score=50,
                    skills_score=50,
                    summary=f"Analysis failed: {str(e)}",
                    tone_style_analysis={},
                    content_analysis={},
                    structure_analysis={},
                    skills_analysis={"highlighted_skills": [], "skill_categories": [], "missing_skills": []},
                    keyword_matches={"matching_keywords": [], "missing_keywords": []},
                    skill_gaps={},
                    recommendations=["Please try re-analyzing the resume"],
                    analysis_date=datetime.utcnow(),
                    ai_model_used="gemini-2.0-flash-exp",
                    analysis_version="1.0"
                )
                db.add(error_analysis)
                db.commit()
            print(f"⚠️ Error analysis saved for resume {resume_id}")
        except Exception as save_error:
            print(f"❌ Could not save error analysis: {str(save_error)}")

@router.get("/{resume_id}/analysis", response_model=AnalysisResultResponse)
@timer("get_resume_analysis")
async def get_resume_analysis(
    resume_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get the latest AI analysis for a resume"""
    with timing_context("database_analysis_query"):
        resume = db.query(Resume).filter(
            Resume.id == resume_id,
            Resume.user_id == current_user.id
        ).first()
        
        if not resume:
            raise HTTPException(status_code=404, detail="Resume not found")
        
        analysis = db.query(AnalysisResult).filter(
            AnalysisResult.resume_id == resume_id
        ).order_by(AnalysisResult.analysis_date.desc()).first()
        
        if not analysis:
            raise HTTPException(status_code=404, detail="No analysis found for this resume")
    
    return analysis

@router.get("/{resume_id}/analysis-history", response_model=AnalysisHistoryResponse)
@timer("get_analysis_history")
async def get_analysis_history(
    resume_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get analysis history for a resume"""
    with timing_context("database_history_query"):
        resume = db.query(Resume).filter(
            Resume.id == resume_id,
            Resume.user_id == current_user.id
        ).first()
        
        if not resume:
            raise HTTPException(status_code=404, detail="Resume not found")
        
        analyses = db.query(AnalysisResult).filter(
            AnalysisResult.resume_id == resume_id
        ).order_by(AnalysisResult.analysis_date.desc()).all()
    
    # Fix skill_gaps for each analysis if needed
    fixed_analyses = []
    for analysis in analyses:
        analysis_data = AnalysisResultResponse.from_orm(analysis)
        fixed_analyses.append(analysis_data)
    
    return AnalysisHistoryResponse(
        resume_id=resume.id,
        resume_filename=resume.original_filename,
        total_analyses=len(analyses),
        analyses=fixed_analyses
    )

@router.post("/{resume_id}/reanalyze", response_model=ReanalyzeResponse)
@timer("reanalyze_resume")
async def reanalyze_resume(
    background_tasks: BackgroundTasks,
    resume_id: int,
    job_title: Optional[str] = Form(None),
    job_description: Optional[str] = Form(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Re-analyze an existing resume"""
    with timing_context("database_reanalyze_query"):
        resume = db.query(Resume).filter(
            Resume.id == resume_id,
            Resume.user_id == current_user.id
        ).first()
        
        if not resume:
            raise HTTPException(status_code=404, detail="Resume not found")
        
        if not resume.extracted_text:
            raise HTTPException(status_code=400, detail="No text content available for analysis")
    
    # Trigger background analysis
    background_tasks.add_task(
        perform_ai_analysis,
        resume.id,
        resume.extracted_text,
        job_title,
        job_description,
        db
    )
    
    return ReanalyzeResponse(
        message="Resume re-analysis started in background",
        resume_id=resume_id,
        job_title=job_title,
        job_description_provided=bool(job_description)
    )

@router.get("/list", response_model=ResumeListWrapper)
@timer("list_resumes")
async def list_resumes(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """List all resumes for current user"""
    with timing_context("database_list_query"):
        resumes = db.query(Resume).filter(
            Resume.user_id == current_user.id,
            Resume.is_active == True
        ).order_by(Resume.upload_date.desc()).all()
        
        # Time the analysis count queries too
        resume_responses = []
        for r in resumes:
            with timing_context("database_analysis_count_query"):
                has_analysis = db.query(AnalysisResult).filter(
                    AnalysisResult.resume_id == r.id
                ).count() > 0
            
            resume_responses.append(
                ResumeListResponse(
                    id=r.id,
                    filename=r.filename,
                    original_filename=r.original_filename,
                    upload_date=r.upload_date,
                    file_size=r.file_size,
                    has_analysis=has_analysis
                )
            )
    
    return ResumeListWrapper(
        total=len(resume_responses),
        resumes=resume_responses
    )

@router.get("/{resume_id}/preview")
@timer("get_resume_preview")
async def get_resume_preview(
    resume_id: int,
    page: int = 0,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get preview image for a resume"""
    with timing_context("database_preview_query"):
        resume = db.query(Resume).filter(
            Resume.id == resume_id,
            Resume.user_id == current_user.id
        ).first()
        
        if not resume:
            raise HTTPException(status_code=404, detail="Resume not found")
    
    preview_generator = PreviewGenerator()
    return await preview_generator.get_preview_endpoint(resume.file_path, page)

@router.get("/{resume_id}/download")
@timer("download_resume")
async def download_resume(
    resume_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Download original resume file via signed URL"""
    with timing_context("database_download_query"):
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

@router.delete("/{resume_id}")
@timer("delete_resume")
async def delete_resume(
    resume_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Delete resume from storage and database"""
    with timing_context("database_delete_query"):
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
    
    # Delete from database with timing
    with timing_context("database_delete_operation"):
        db.delete(resume)
        db.commit()
    
    return {"message": "Resume deleted successfully"}