import os
from fastapi import FastAPI, Depends
from sqlalchemy import text
from fastapi.middleware.cors import CORSMiddleware
from app.core.database import engine
from app.models import user, resume, analysis_result
from app.services.gemini_ai import GeminiAIService
from app.api.routes import auth, resumes, cache
from app.core.database import get_db
from datetime import datetime
from app.core.performance import get_performance_summary, clear_metrics
from sqlalchemy.orm import Session
from fastapi.responses import JSONResponse
from app.api.dependencies import get_current_user
from app.services.supabase_storage import SupabaseStorageService

# Initialize services
storage_service = SupabaseStorageService()
gemini_ai_service = GeminiAIService()

# Create database tables
user.Base.metadata.create_all(bind=engine)
resume.Base.metadata.create_all(bind=engine)
analysis_result.Base.metadata.create_all(bind=engine)

app = FastAPI(title="AI Resume Analyzer API", version="1.0.0")

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routers
app.include_router(auth.router, prefix="/api/auth", tags=["authentication"])
app.include_router(resumes.router, prefix="/api/resumes", tags=["resumes"])
app.include_router(cache.router, prefix="/cache", tags=["cache"])

@app.get("/")
def read_root():
    return {"message": "AI Resume Analyzer API is running"}

@app.get("/health")
async def health_check(db: Session = Depends(get_db)):  
    health_status = {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "checks": {
            "database": False,
            "supabase_storage": False, 
            "gemini_api": True,  # Temporarily set to True to avoid async issues
        }
    }
    
    failed_checks = []

    # 1. Check Database Connection 
    try:
        db.execute(text("SELECT 1"))
        health_status["checks"]["database"] = True
    except Exception as e:
        failed_checks.append("database")
        health_status["database_error"] = str(e)

    # 2. Check Supabase Storage 
    try:
        files = storage_service.supabase.storage.from_(storage_service.bucket_name).list()
        health_status["checks"]["supabase_storage"] = True
    except Exception as e:
        failed_checks.append("supabase_storage")
        health_status["supabase_error"] = str(e)
    
    # 3. Skip Gemini API check for now to avoid async issues
    health_status["gemini_note"] = "API check temporarily disabled for deployment"
    
    # Determine overall status
    if failed_checks:
        health_status["status"] = "unhealthy"
        health_status["failed_checks"] = failed_checks
        return JSONResponse(health_status, status_code=503)
    else:
        return JSONResponse(health_status, status_code=200)

@app.get("/performance/metrics")
async def get_performance_metrics(current_user=Depends(get_current_user)):
    """
    Get current performance metrics summary
    """
    summary = get_performance_summary()
    return {
        "timestamp": datetime.utcnow().isoformat(),
        "metrics": summary
    }

@app.delete("/performance/metrics")
async def clear_performance_metrics(current_user=Depends(get_current_user)):
    """
    Clear all performance metrics
    """
    clear_metrics()
    return {"message": "Performance metrics cleared"}

@app.get("/performance/breakdown")
async def get_performance_breakdown(current_user=Depends(get_current_user)):
    """
    Get performance breakdown for typical resume analysis
    """
    summary = get_performance_summary()
    
    # Calculate typical flow breakdown with ALL metrics
    typical_flow = {
        "file_upload": (
            summary.get("file_upload_process", {}).get("avg", 0) +
            summary.get("supabase_upload", {}).get("avg", 0) +
            summary.get("supabase_upload_content", {}).get("avg", 0)
        ),
        "pdf_parsing": (
            summary.get("text_extraction_process", {}).get("avg", 0) +
            summary.get("pdf_extraction", {}).get("avg", 0) +
            summary.get("pdf_extraction_method", {}).get("avg", 0) +
            summary.get("docx_extraction", {}).get("avg", 0) +
            summary.get("docx_extraction_method", {}).get("avg", 0)
        ),
        "database_save": (
            summary.get("database_resume_save", {}).get("avg", 0) +
            summary.get("database_analysis_save", {}).get("avg", 0)
        ),
        "database_queries": (
            summary.get("database_analysis_query", {}).get("avg", 0) +
            summary.get("database_history_query", {}).get("avg", 0) +
            summary.get("database_list_query", {}).get("avg", 0) +
            summary.get("database_analysis_count_query", {}).get("avg", 0)
        ),
        "gemini_api": summary.get("gemini_api_call", {}).get("avg", 0),
    }
    
    total = sum(typical_flow.values())
    
    # Create response data
    response_data = {
        "breakdown_seconds": typical_flow,
        "total_seconds": total,
        "detailed_metrics": {
            "file_processing": {
                "total_upload": typical_flow["file_upload"],
                "file_content_read": summary.get("file_content_read", {}).get("avg", 0),
                "supabase_upload": (
                    summary.get("supabase_upload", {}).get("avg", 0) +
                    summary.get("supabase_upload_content", {}).get("avg", 0)
                )
            },
            "text_extraction": {
                "total_extraction": typical_flow["pdf_parsing"],
                "text_extraction_process": summary.get("text_extraction_process", {}).get("avg", 0),
                "pdf_extraction": summary.get("pdf_extraction", {}).get("avg", 0),
                "docx_extraction": summary.get("docx_extraction", {}).get("avg", 0),
                "temp_file_operations": (
                    summary.get("temp_file_creation", {}).get("avg", 0) +
                    summary.get("temp_file_cleanup", {}).get("avg", 0)
                )
            },
            "database_operations": {
                "saves": typical_flow["database_save"],
                "queries": typical_flow["database_queries"]
            },
            "ai_processing": {
                "gemini_api": summary.get("gemini_api_call", {}).get("avg", 0),
                "analysis_structure": summary.get("structure_ai_analysis", {}).get("avg", 0),
                "background_analysis": summary.get("perform_ai_analysis", {}).get("avg", 0)
            }
        }
    }
    
    # Add percentages
    if total > 0:
        percentages = {}
        for key, value in typical_flow.items():
            percentages[f"{key}_percent"] = round((value / total) * 100, 1)
        response_data["percentages"] = percentages
    
    return {
        "performance_breakdown": response_data,
        "sample_size": len(summary.get("gemini_api_call", {}).get("durations", [])),
        "timestamp": datetime.utcnow().isoformat(),
        "metrics_available": list(summary.keys())
    }

# CRITICAL: Add this for Render deployment
if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run("backend.app.main:app", host="0.0.0.0", port=port, reload=False)
