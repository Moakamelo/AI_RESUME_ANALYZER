from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.database import engine
from app.models import user, resume, analysis_result
from app.services.gemini_ai import gemini_ai_service
from app.api.routes import auth, resumes

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

# Include routers
app.include_router(auth.router, prefix="/api/auth", tags=["authentication"])
app.include_router(resumes.router, prefix="/api/resumes", tags=["resumes"])

@app.get("/")
def read_root():
    return {"message": "AI Resume Analyzer API is running"}

@app.get("/health")
def health_check():
    return {"status": "healthy"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)

