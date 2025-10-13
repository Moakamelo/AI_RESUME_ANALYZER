from fastapi import HTTPException
from fastapi.responses import FileResponse
import tempfile
from pathlib import Path
import os
from app.services.supabase_storage import SupabaseStorageService

try:
    import fitz 
    PYMUPDF_AVAILABLE = True
except ImportError:
    PYMUPDF_AVAILABLE = False
    print("❌ PyMuPDF not installed. Run: pip install PyMuPDF")

from PIL import Image, ImageDraw, ImageFont

class PreviewGenerator:
    def __init__(self):
        self.storage_service = SupabaseStorageService()

    async def generate_preview(self, supabase_file_path: str, page: int = 0) -> str:
        """Convert document page to image for preview from Supabase storage"""
        try:
            print(f"🎨 Generating preview for: {supabase_file_path}, page: {page}")
            
            # Download file from Supabase first
            file_content = self.storage_service.download_file(supabase_file_path)
            if not file_content:
                raise HTTPException(500, "Failed to download file from storage")
            
            print(f"📥 Downloaded {len(file_content)} bytes from Supabase")
            
            # Get file extension from the path
            file_ext = Path(supabase_file_path).suffix.lower()
            
            # Create temporary file for the downloaded content
            with tempfile.NamedTemporaryFile(delete=False, suffix=file_ext) as temp_file:
                temp_file.write(file_content)
                temp_file_path = temp_file.name
            
            print(f"📁 Created temporary file: {temp_file_path}")
            
            try:
                if file_ext == '.pdf':
                    return await self.pdf_to_image(temp_file_path, page)
                elif file_ext in ['.docx', '.doc']:
                    return await self.docx_to_image(temp_file_path)
                else:
                    return await self.text_to_image(temp_file_path)
            finally:
                # Clean up the temporary downloaded file
                try:
                    os.unlink(temp_file_path)
                    print(f"🧹 Cleaned up temporary file: {temp_file_path}")
                except:
                    pass
                
        except Exception as e:
            print(f"❌ Failed to generate preview: {str(e)}")
            raise HTTPException(500, f"Failed to generate preview: {str(e)}")
    
    async def pdf_to_image(self, local_file_path: str, page: int = 0) -> str:
        """Convert PDF page to JPEG image using PyMuPDF"""
        if not PYMUPDF_AVAILABLE:
            return await self._create_placeholder_image("Please install PyMuPDF: pip install PyMuPDF")
        
        try:
            print(f"📄 Converting PDF to JPEG: {local_file_path}, page: {page}")
            
            # Open the PDF
            doc = fitz.open(local_file_path)
            print(f"📄 PDF opened, total pages: {len(doc)}")
            
            # Check if page exists
            if page >= len(doc):
                doc.close()
                raise HTTPException(404, f"Page {page + 1} not found. PDF has {len(doc)} pages.")
            
            # Get the page
            pdf_page = doc[page]
            print(f"📄 Processing page {page + 1}")
            
            # Convert to image with good resolution
            # Matrix: zoom factor for resolution (2.0 = 2x zoom for better quality)
            mat = fitz.Matrix(2.0, 2.0)
            pix = pdf_page.get_pixmap(matrix=mat)
            print(f"🖼️ Created pixmap: {pix.width}x{pix.height} pixels")
            
            # Save image to temp file
            temp_dir = tempfile.gettempdir()
            image_path = Path(temp_dir) / f"preview_{Path(local_file_path).stem}_{page}.jpg"
            
            # PyMuPDF automatically uses good quality for JPEG
            pix.save(str(image_path))
            
            doc.close()
            
            print(f"✅ PDF to JPEG conversion successful: {image_path}")
            print(f"✅ File size: {os.path.getsize(image_path)} bytes")
            return str(image_path)
            
        except Exception as e:
            print(f"❌ PDF to JPEG conversion failed: {str(e)}")
            raise HTTPException(500, f"PDF conversion failed: {str(e)}")
    
    async def _create_placeholder_image(self, message: str) -> str:
        """Create a placeholder image with error message"""
        try:
            temp_dir = tempfile.gettempdir()
            image_path = Path(temp_dir) / f"preview_placeholder_{os.urandom(4).hex()}.jpg"
            
            # Create image
            img = Image.new('RGB', (600, 400), color=(240, 240, 240))
            d = ImageDraw.Draw(img)
            
            # Add border
            d.rectangle([(10, 10), (590, 390)], outline='gray', width=2)
            
            # Add title
            title_font_size = 20
            try:
                title_font = ImageFont.truetype("arial.ttf", title_font_size)
            except:
                title_font = ImageFont.load_default()
            
            d.text((300, 80), "Preview Not Available", fill='black', font=title_font, anchor="mm")
            
            # Add message
            message_font_size = 14
            try:
                message_font = ImageFont.truetype("arial.ttf", message_font_size)
            except:
                message_font = ImageFont.load_default()
            
            # Wrap text
            words = message.split()
            lines = []
            current_line = ""
            
            for word in words:
                test_line = current_line + word + " "
                if len(test_line) < 50:
                    current_line = test_line
                else:
                    lines.append(current_line)
                    current_line = word + " "
            if current_line:
                lines.append(current_line)
            
            # Draw message lines
            y_position = 150
            for line in lines[:6]:  # Max 6 lines
                d.text((300, y_position), line.strip(), fill='darkred', font=message_font, anchor="mm")
                y_position += 30
            
            img.save(image_path, "JPEG", quality=85)
            print(f"📝 Created placeholder image: {image_path}")
            return str(image_path)
            
        except Exception as e:
            print(f"❌ Failed to create placeholder: {str(e)}")
            try:
                temp_dir = tempfile.gettempdir()
                image_path = Path(temp_dir) / f"preview_error_{os.urandom(4).hex()}.jpg"
                img = Image.new('RGB', (300, 100), color='red')
                img.save(image_path, "JPEG")
                return str(image_path)
            except:
                raise HTTPException(500, "Complete preview failure")
    
    async def docx_to_image(self, local_file_path: str) -> str:
        """Convert DOCX to image placeholder"""
        return await self._create_placeholder_image("Word document preview is not currently supported")
    
    async def text_to_image(self, local_file_path: str) -> str:
        """Convert text file to image preview"""
        try:
            # Read text content
            with open(local_file_path, 'r', encoding='utf-8') as f:
                text_content = f.read()
            
            # Create image with text
            temp_dir = tempfile.gettempdir()
            image_path = Path(temp_dir) / f"preview_{Path(local_file_path).stem}.jpg"
            
            # Create image
            img = Image.new('RGB', (800, 1000), color='white')
            d = ImageDraw.Draw(img)
            
            # Try to use a font
            try:
                font = ImageFont.truetype("arial.ttf", 12)
            except:
                font = ImageFont.load_default()
            
            # Add title
            d.text((50, 30), "Text Document Preview", fill='black', font=font)
            d.line([(50, 55), (750, 55)], fill='gray', width=1)
            
            # Add text lines
            y_position = 80
            line_count = 0
            for line in text_content.split('\n'):
                if line_count >= 40:  # Limit to 40 lines
                    d.text((50, y_position), "... (content truncated)", fill='gray', font=font)
                    break
                    
                if len(line) > 100:  # Limit line length
                    line = line[:97] + "..."
                
                d.text((50, y_position), line, fill='black', font=font)
                y_position += 20
                line_count += 1
                
                if y_position > 950:  # Don't overflow image
                    d.text((50, y_position), "... (content truncated)", fill='gray', font=font)
                    break
            
            img.save(image_path, "JPEG", quality=85)
            print(f"📝 Created text preview: {image_path}")
            return str(image_path)
            
        except Exception as e:
            print(f"❌ Text preview failed: {str(e)}")
            return await self._create_placeholder_image(f"Text preview error: {str(e)}")
    
    async def get_preview_endpoint(self, supabase_file_path: str, page: int = 0):
        """FastAPI endpoint to serve preview images"""
        try:
            print(f"🚀 Starting preview generation for: {supabase_file_path}")
            image_path = await self.generate_preview(supabase_file_path, page)
            print(f"✅ Preview generated successfully: {image_path}")
            return FileResponse(image_path, media_type="image/jpeg")
        except Exception as e:
            print(f"❌ Preview endpoint error: {str(e)}")
            # Return placeholder image on error
            placeholder_path = await self._create_placeholder_image(f"Preview generation failed: {str(e)}")
            return FileResponse(placeholder_path, media_type="image/jpeg")

    # Static method for backward compatibility
    @staticmethod
    async def get_preview_endpoint_static(file_path: str, page: int = 0):
        """Static method for backward compatibility"""
        generator = PreviewGenerator()
        return await generator.get_preview_endpoint(file_path, page)