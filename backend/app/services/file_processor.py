import os
from fastapi import UploadFile, HTTPException
from PyPDF2 import PdfReader
import docx
from pathlib import Path
from datetime import datetime
import tempfile
from app.services.supabase_storage import SupabaseStorageService
import uuid
from app.core.performance import timer, timing_context


class FileProcessor:
    def __init__(self):
        self.storage_service = SupabaseStorageService()

    @timer("file_upload_process")
    async def process_resume(self, file: UploadFile, user_id: int) -> dict:
        """Process uploaded resume file with comprehensive timing"""
        # Validate file type
        allowed_types = ['application/pdf', 
                        'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
                        'application/msword', 'text/plain']
        
        if file.content_type not in allowed_types:
            raise HTTPException(400, "Invalid file type")
        
        # Time file reading
        with timing_context("file_content_read"):
            file_content = await file.read()
            await file.seek(0)  # Reset file pointer
        
        # Time Supabase upload
        with timing_context("supabase_upload"):
            upload_result = await self.upload_file_content(
                file_content=file_content,
                original_filename=file.filename,
                content_type=file.content_type,
                client_file_id=user_id, 
                document_type="resume"
            )
        
        if not upload_result:
            raise HTTPException(500, "Failed to upload file to storage")
        
        # Time text extraction
        with timing_context("text_extraction"):
            extracted_text = await self.extract_text_from_content(
                file_content=file_content,
                filename=file.filename
            )
        
        return {
            "file_path": upload_result["stored_filename"],
            "saved_filename": upload_result["stored_filename"],  
            "original_filename": upload_result["original_filename"],
            "extracted_text": extracted_text,
            "file_type": file.content_type,
            "file_size": upload_result["file_size"]
        }
    
    @timer("supabase_upload_content")
    async def upload_file_content(self, file_content: bytes, original_filename: str, 
                                content_type: str, client_file_id: int, document_type: str) -> dict:
        """Upload file content to Supabase with timing"""
        try:
            if len(file_content) > 2 * 1024 * 1024:  # 2MB
                compressed_content = self.compress_file(file_content)
                file_content = compressed_content
            print(f"📤 Starting file upload: {original_filename}")

            # Generate unique filename
            file_extension = os.path.splitext(original_filename)[1]
            unique_id = str(uuid.uuid4())
            stored_filename = f"client_{client_file_id}/{document_type}_{unique_id}{file_extension}"
            
            print(f"📤 Generated filename: {stored_filename}")
            print(f"📤 Uploading to bucket: {self.storage_service.bucket_name}")
            
            # Upload to Supabase
            upload_response = self.storage_service.supabase.storage.from_(
                self.storage_service.bucket_name
            ).upload(
                path=stored_filename,
                file=file_content,
                file_options={"content-type": content_type}
            )
            
            print(f"📤 Upload response: {upload_response}")
            
            if not upload_response:
                print("❌ Upload response is None")
                return None
            
            # Return file information
            return {
                "original_filename": original_filename,
                "stored_filename": stored_filename,
                "file_path": stored_filename,
                "file_size": len(file_content),
                "mime_type": content_type or "application/octet-stream",
                "bucket_name": self.storage_service.bucket_name
            }
            
        except Exception as e:
            print(f"❌ Upload error: {str(e)}")
            import traceback
            traceback.print_exc()
            return None
    
    @timer("text_extraction_process")
    async def extract_text_from_content(self, file_content: bytes, filename: str) -> str:
        """Extract text from file content with timing"""
        file_ext = Path(filename).suffix.lower()
        
        # Time temporary file creation
        with timing_context("temp_file_creation"):
            with tempfile.NamedTemporaryFile(delete=False, suffix=file_ext) as temp_file:
                temp_file.write(file_content)
                temp_file_path = temp_file.name
        
        try:
            # Time the actual text extraction based on file type
            if file_ext == '.pdf':
                with timing_context("pdf_extraction"):
                    return await self.extract_text_from_pdf(temp_file_path)
            elif file_ext == '.docx':
                with timing_context("docx_extraction"):
                    return await self.extract_text_from_docx(temp_file_path)
            elif file_ext == '.doc':
                with timing_context("doc_extraction"):
                    return await self.extract_text_from_doc(temp_file_path)
            elif file_ext == '.txt':
                with timing_context("txt_extraction"):
                    return await self.extract_text_from_txt(temp_file_path)
            else:
                return ""
        except Exception as e:
            print(f"❌ Text extraction error: {str(e)}")
            return ""
        finally:
            # Time file cleanup
            with timing_context("temp_file_cleanup"):
                try:
                    os.unlink(temp_file_path)
                except:
                    pass
    
    @timer("pdf_extraction_method")
    async def extract_text_from_pdf(self, file_path: str) -> str:
        """Extract text from PDF file with timing"""
        try:
            with open(file_path, 'rb') as f:
                pdf_reader = PdfReader(f)
                text = ""
                for page_num, page in enumerate(pdf_reader.pages):
                    with timing_context(f"pdf_page_{page_num}"):
                        page_text = page.extract_text()
                        if page_text:
                            text += page_text + "\n"
                return text.strip()
        except Exception as e:
            print(f"❌ PDF extraction error: {str(e)}")
            return ""
    
    @timer("docx_extraction_method")
    async def extract_text_from_docx(self, file_path: str) -> str:
        """Extract text from DOCX file with timing"""
        try:
            doc = docx.Document(file_path)
            text = ""
            for paragraph_num, paragraph in enumerate(doc.paragraphs):
                with timing_context(f"docx_paragraph_{paragraph_num}"):
                    if paragraph.text:
                        text += paragraph.text + "\n"
            return text.strip()
        except Exception as e:
            print(f"❌ DOCX extraction error: {str(e)}")
            return ""
    
    @timer("doc_extraction_method")
    async def extract_text_from_doc(self, file_path: str) -> str:
        """Extract text from DOC file with timing"""
        try:
            print("⚠️ .doc file extraction not fully supported. Consider converting to .docx")
            # You might want to use python-docx2txt or other libraries for .doc files
            return ""
        except Exception as e:
            print(f"❌ DOC extraction error: {str(e)}")
            return ""
    
    @timer("txt_extraction_method")
    async def extract_text_from_txt(self, file_path: str) -> str:
        """Extract text from TXT file with timing"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return f.read().strip()
        except Exception as e:
            print(f"❌ TXT extraction error: {str(e)}")
            return ""