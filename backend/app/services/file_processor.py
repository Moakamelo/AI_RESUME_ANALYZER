# app/services/file_processor.py
import os
from fastapi import UploadFile, HTTPException
from PyPDF2 import PdfReader
import docx
from pathlib import Path
from datetime import datetime
import tempfile

class FileProcessor:
    @staticmethod
    async def process_resume(file: UploadFile, user_id: int) -> dict:
        # Validate file type
        allowed_types = ['application/pdf', 
                        'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
                        'application/msword', 'text/plain']
        
        if file.content_type not in allowed_types:
            raise HTTPException(400, "Invalid file type")
        
        # Save original file
        file_path = await FileProcessor.save_file(file, user_id)
        
        # Extract text for AI analysis
        extracted_text = await FileProcessor.extract_text(file, file_path)
        
        return {
            "file_path": file_path,
            "extracted_text": extracted_text,
            "file_type": file.content_type,
            "file_size": file.size
        }
    
    @staticmethod
    async def save_file(file: UploadFile, user_id: int) -> str:
        # Create user directory if not exists
        user_dir = Path(f"uploads/resumes/{user_id}")
        user_dir.mkdir(parents=True, exist_ok=True)
        
        # Generate unique filename
        file_ext = Path(file.filename).suffix
        filename = f"{user_id}_{int(datetime.now().timestamp())}{file_ext}"
        file_path = user_dir / filename
        
        # Save file
        content = await file.read()
        with open(file_path, "wb") as f:
            f.write(content)
        
        return str(file_path)
    
    @staticmethod
    async def extract_text(file: UploadFile, file_path: str) -> str:
        file_ext = Path(file_path).suffix.lower()
        
        if file_ext == '.pdf':
            return FileProcessor.extract_text_from_pdf(file_path)
        elif file_ext == '.docx':
            return FileProcessor.extract_text_from_docx(file_path)
        elif file_ext == '.txt':
            with open(file_path, 'r', encoding='utf-8') as f:
                return f.read()
        else:
            return ""
    
    @staticmethod
    def extract_text_from_pdf(file_path: str) -> str:
        with open(file_path, 'rb') as f:
            pdf_reader = PdfReader(f)
            text = ""
            for page in pdf_reader.pages:
                text += page.extract_text() + "\n"
            return text
    
    @staticmethod
    def extract_text_from_docx(file_path: str) -> str:
        doc = docx.Document(file_path)
        text = ""
        for paragraph in doc.paragraphs:
            text += paragraph.text + "\n"
        return text