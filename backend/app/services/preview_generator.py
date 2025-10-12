# app/services/preview_generator.py
from fastapi import HTTPException
from fastapi.responses import FileResponse
import tempfile
from pathlib import Path
import pdf2image
import os

class PreviewGenerator:
    @staticmethod
    async def generate_preview(file_path: str, page: int = 0) -> str:
        """Convert document page to image for preview"""
        file_ext = Path(file_path).suffix.lower()
        
        if file_ext == '.pdf':
            return await PreviewGenerator.pdf_to_image(file_path, page)
        elif file_ext in ['.docx', '.doc']:
            return await PreviewGenerator.docx_to_image(file_path)
        else:
            return await PreviewGenerator.text_to_image(file_path)
    
    @staticmethod
    async def pdf_to_image(file_path: str, page: int = 0) -> str:
        """Convert PDF page to image"""
        try:
            # Convert PDF to images
            images = pdf2image.convert_from_path(file_path, first_page=page+1, last_page=page+1)
            
            if not images:
                raise HTTPException(404, "Page not found")
            
            # Save image to temp file
            temp_dir = tempfile.gettempdir()
            image_path = Path(temp_dir) / f"preview_{Path(file_path).stem}_{page}.jpg"
            
            images[0].save(image_path, "JPEG", quality=85)
            return str(image_path)
            
        except Exception as e:
            raise HTTPException(500, f"Failed to generate preview: {str(e)}")
    
    @staticmethod
    async def get_preview_endpoint(file_path: str, page: int = 0):
        """FastAPI endpoint to serve preview images"""
        image_path = await PreviewGenerator.generate_preview(file_path, page)
        return FileResponse(image_path, media_type="image/jpeg")