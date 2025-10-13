# app/services/supabase_storage.py
import os
import uuid
from typing import Optional
from fastapi import UploadFile, HTTPException
from supabase import create_client, Client
import traceback

class SupabaseStorageService:
    def __init__(self):
        try:
            supabase_url = os.getenv("SUPABASE_URL")
            supabase_key = os.getenv("SUPABASE_KEY")
            self.bucket_name = os.getenv("SUPABASE_BUCKET", "resume_uploader")
            
            if not supabase_url or not supabase_key:
                raise ValueError("Supabase credentials not found in environment variables")
            
            self.supabase: Client = create_client(supabase_url, supabase_key)
            print(f"✅ Supabase storage service initialized with bucket: {self.bucket_name}")
            
        except Exception as e:
            print(f"❌ Failed to initialize Supabase storage: {e}")
            raise

    async def upload_file(self, file: UploadFile, client_file_id: int, document_type: str) -> dict:
        try:
            print(f"📤 Starting file upload: {file.filename}")
            
            # Read file content
            content = await file.read()
            print(f"📤 Read {len(content)} bytes from file")
            
            # Generate unique filename
            file_extension = os.path.splitext(file.filename)[1]
            unique_id = str(uuid.uuid4())
            stored_filename = f"client_{client_file_id}/{document_type}_{unique_id}{file_extension}"
            
            print(f"📤 Generated filename: {stored_filename}")
            print(f"📤 Uploading to bucket: {self.bucket_name}")
            
            # Upload to Supabase
            upload_response = self.supabase.storage.from_(self.bucket_name).upload(
                path=stored_filename,
                file=content,
                file_options={"content-type": file.content_type}
            )
            
            print(f"📤 Upload response: {upload_response}")
            
            if not upload_response:
                print("❌ Upload response is None")
                return None
            
            # Return file information
            return {
                "original_filename": file.filename,
                "stored_filename": stored_filename,
                "file_path": stored_filename,
                "file_size": len(content),
                "mime_type": file.content_type or "application/octet-stream",
                "bucket_name": self.bucket_name
            }
            
        except Exception as e:
            print(f"❌ Upload error: {str(e)}")
            traceback.print_exc()
            return None

    def verify_file_exists(self, file_path: str) -> bool:
        """Verify that a file exists in storage"""
        try:
            print(f"🔍 Verifying file existence: {file_path}")
            
            # Extract directory and filename
            directory = os.path.dirname(file_path)
            filename = os.path.basename(file_path)
            
            print(f"🔍 Looking for file: '{filename}' in directory: '{directory}'")
            
            # List files in the specific directory
            try:
                if directory:
                    files = self.supabase.storage.from_(self.bucket_name).list(directory)
                else:
                    files = self.supabase.storage.from_(self.bucket_name).list()
            except Exception as list_error:
                print(f"🔍 Error listing directory '{directory}': {list_error}")
                return False
            
            print(f"🔍 Found {len(files)} files in directory")
            
            # Check if our file exists in the list
            file_exists = any(
                file_info.get('name') == filename for file_info in files
            )
            
            print(f"🔍 File exists in storage: {file_exists}")
            return file_exists
        
        except Exception as e:
            print(f"❌ Error verifying file existence: {e}")
            traceback.print_exc()
            return False

    def create_signed_url(self, file_path: str, expires_in: int = 3600) -> Optional[str]:
        """Create a signed URL for file download"""
        try:
            print(f"🔗 Creating signed URL for: {file_path}")
            print(f"🔗 Using bucket: {self.bucket_name}")
            
            # Supabase will handle file existence internally
            response = self.supabase.storage.from_(self.bucket_name).create_signed_url(
                file_path, expires_in
            )
            
            if response and 'signedURL' in response:
                print(f"✅ Signed URL created successfully")
                return response['signedURL']
            else:
                print(f"❌ Signed URL creation failed. Response: {response}")
                # Try verification as fallback
                file_exists = self.verify_file_exists(file_path)
                if file_exists:
                    print(f"✅ File exists but signed URL creation failed")
                else:
                    print(f"❌ File does not exist: {file_path}")
                return None
            
        except Exception as e:
            print(f"❌ Signed URL creation error: {str(e)}")
            traceback.print_exc()
            return None

    def delete_file_sync(self, file_path: str) -> bool:
        """Synchronous version of delete_file"""
        try:
            print(f"🗑️ Deleting file from storage: {file_path}")
            
            # Try to delete directly without verification first
            response = self.supabase.storage.from_(self.bucket_name).remove([file_path])
            print(f"✅ File deletion response: {response}")
            
            # Verify deletion
            still_exists = self.verify_file_exists(file_path)
            if still_exists:
                print(f"❌ File still exists after deletion attempt: {file_path}")
                return False
                
            print(f"✅ File successfully deleted: {file_path}")
            return True
            
        except Exception as e:
            print(f"❌ Error deleting file {file_path}: {str(e)}")
            traceback.print_exc()
            return False

    async def delete_file(self, file_path: str) -> bool:
        """Async wrapper for delete_file"""
        return self.delete_file_sync(file_path)

    def list_bucket_files(self) -> list:
        """List all files in the bucket for debugging"""
        try:
            files = self.supabase.storage.from_(self.bucket_name).list()
            print(f"📁 Found {len(files)} files in bucket:")
            for file_info in files:
                print(f"  - {file_info}")
            return files
        except Exception as e:
            print(f"❌ Error listing bucket files: {e}")
            return []

    def list_directory_files(self, directory: str = "") -> list:
        """List files in a specific directory"""
        try:
            files = self.supabase.storage.from_(self.bucket_name).list(directory)
            print(f"📁 Found {len(files)} files in directory '{directory}':")
            for file_info in files:
                print(f"  - {file_info}")
            return files
        except Exception as e:
            print(f"❌ Error listing directory files: {e}")
            return []

    def get_file_info(self, file_path: str) -> Optional[dict]:
        """Get information about a specific file"""
        try:
            file_exists = self.verify_file_exists(file_path)
            if file_exists:
                return {
                    "path": file_path,
                    "exists": True
                }
            return None
        except Exception as e:
            print(f"❌ Error getting file info: {e}")
            return None

    def download_file(self, file_path: str) -> Optional[bytes]:
        """Download file content from Supabase"""
        try:
            print(f"📥 Downloading file: {file_path}")
            
            response = self.supabase.storage.from_(self.bucket_name).download(file_path)
            
            if response:
                print(f"✅ File downloaded successfully: {len(response)} bytes")
                return response
            else:
                print("❌ Download response is None")
                return None
                
        except Exception as e:
            print(f"❌ Download error: {str(e)}")
            traceback.print_exc()
            return None

    def get_public_url(self, file_path: str) -> Optional[str]:
        """Get public URL for file (if bucket is public)"""
        try:
            response = self.supabase.storage.from_(self.bucket_name).get_public_url(file_path)
            return response
        except Exception as e:
            print(f"❌ Error getting public URL: {e}")
            return None

    # Debug method to check bucket structure
    def debug_bucket_structure(self):
        """Debug method to see the exact structure of files in the bucket"""
        try:
            print(f"🔍 Debugging bucket structure for: {self.bucket_name}")
            
            # List all files recursively
            all_files = self.supabase.storage.from_(self.bucket_name).list()
            
            print(f"📁 Total files in bucket: {len(all_files)}")
            for file_info in all_files:
                print(f"  📄 {file_info}")
                
            return all_files
        except Exception as e:
            print(f"❌ Error debugging bucket structure: {e}")
            return []