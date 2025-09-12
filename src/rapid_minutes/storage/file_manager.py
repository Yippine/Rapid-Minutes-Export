import os
import uuid
import shutil
import logging
from pathlib import Path
from typing import Optional, Dict, Any
from datetime import datetime, timedelta
import json

from rapid_minutes.config.settings import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class FileManager:
    def __init__(self):
        self.upload_dir = Path(settings.upload_dir)
        self.output_dir = Path(settings.output_dir)
        self.temp_dir = Path(settings.temp_dir)
        self.max_file_size = settings.upload_max_size
        
    def ensure_directories(self):
        """Create necessary directories if they don't exist"""
        try:
            self.upload_dir.mkdir(exist_ok=True)
            self.output_dir.mkdir(exist_ok=True)
            self.temp_dir.mkdir(exist_ok=True)
            logger.info("All directories ensured")
        except Exception as e:
            logger.error(f"Failed to create directories: {e}")
            raise
    
    def save_uploaded_file(self, file_content: bytes, filename: str) -> Dict[str, Any]:
        """Save uploaded file and return file info"""
        try:
            # Generate unique file ID
            file_id = str(uuid.uuid4())
            
            # Validate file size
            if len(file_content) > self.max_file_size:
                raise ValueError(f"File size ({len(file_content)} bytes) exceeds limit ({self.max_file_size} bytes)")
            
            # Determine file extension
            original_name = filename
            file_ext = Path(filename).suffix.lower()
            
            if file_ext not in ['.txt', '.doc', '.docx']:
                logger.warning(f"Unusual file extension: {file_ext}")
            
            # Save file
            safe_filename = f"{file_id}_{original_name}"
            file_path = self.upload_dir / safe_filename
            
            with open(file_path, 'wb') as f:
                f.write(file_content)
            
            # Create metadata
            metadata = {
                "file_id": file_id,
                "original_name": original_name,
                "safe_filename": safe_filename,
                "file_path": str(file_path),
                "file_size": len(file_content),
                "file_ext": file_ext,
                "upload_time": datetime.now().isoformat(),
                "status": "uploaded"
            }
            
            # Save metadata
            self._save_metadata(file_id, metadata)
            
            logger.info(f"File saved: {safe_filename} (ID: {file_id})")
            return metadata
            
        except Exception as e:
            logger.error(f"Failed to save uploaded file: {e}")
            raise
    
    def read_file_content(self, file_id: str) -> str:
        """Read and return text content of uploaded file"""
        try:
            metadata = self._load_metadata(file_id)
            if not metadata:
                raise ValueError(f"File not found: {file_id}")
            
            file_path = Path(metadata["file_path"])
            if not file_path.exists():
                raise FileNotFoundError(f"File does not exist: {file_path}")
            
            # Read file content based on extension
            file_ext = metadata.get("file_ext", "").lower()
            
            if file_ext == '.txt':
                with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
                    content = f.read()
            elif file_ext in ['.doc', '.docx']:
                # For now, treat as text file. In production, use python-docx
                with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
                    content = f.read()
            else:
                # Fallback to text reading
                with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
                    content = f.read()
            
            logger.info(f"File content read: {file_id}")
            return content
            
        except Exception as e:
            logger.error(f"Failed to read file content: {e}")
            raise
    
    def save_output_file(self, file_id: str, content: bytes, file_type: str) -> str:
        """Save generated output file (Word or PDF)"""
        try:
            ext = '.docx' if file_type == 'word' else '.pdf'
            output_filename = f"{file_id}_minutes{ext}"
            output_path = self.output_dir / output_filename
            
            with open(output_path, 'wb') as f:
                f.write(content)
            
            # Update metadata
            metadata = self._load_metadata(file_id) or {}
            metadata[f"{file_type}_output"] = {
                "filename": output_filename,
                "path": str(output_path),
                "created_time": datetime.now().isoformat(),
                "size": len(content)
            }
            self._save_metadata(file_id, metadata)
            
            logger.info(f"Output file saved: {output_filename}")
            return str(output_path)
            
        except Exception as e:
            logger.error(f"Failed to save output file: {e}")
            raise
    
    def get_output_file_path(self, file_id: str, file_type: str) -> Optional[str]:
        """Get path to generated output file"""
        try:
            metadata = self._load_metadata(file_id)
            if not metadata:
                return None
            
            output_info = metadata.get(f"{file_type}_output")
            if not output_info:
                return None
            
            file_path = Path(output_info["path"])
            if file_path.exists():
                return str(file_path)
            
            return None
            
        except Exception as e:
            logger.error(f"Failed to get output file path: {e}")
            return None
    
    def cleanup_old_files(self, hours: int = 24):
        """Remove files older than specified hours"""
        try:
            cutoff_time = datetime.now() - timedelta(hours=hours)
            removed_count = 0
            
            # Clean upload directory
            for file_path in self.upload_dir.glob("*"):
                if file_path.is_file():
                    if datetime.fromtimestamp(file_path.stat().st_mtime) < cutoff_time:
                        file_path.unlink()
                        removed_count += 1
            
            # Clean output directory
            for file_path in self.output_dir.glob("*"):
                if file_path.is_file():
                    if datetime.fromtimestamp(file_path.stat().st_mtime) < cutoff_time:
                        file_path.unlink()
                        removed_count += 1
            
            # Clean temp directory
            for file_path in self.temp_dir.glob("*"):
                if file_path.is_file():
                    if datetime.fromtimestamp(file_path.stat().st_mtime) < cutoff_time:
                        file_path.unlink()
                        removed_count += 1
            
            # Clean metadata files
            metadata_dir = self.temp_dir / "metadata"
            if metadata_dir.exists():
                for metadata_file in metadata_dir.glob("*.json"):
                    if datetime.fromtimestamp(metadata_file.stat().st_mtime) < cutoff_time:
                        metadata_file.unlink()
                        removed_count += 1
            
            logger.info(f"Cleanup completed: removed {removed_count} files")
            return removed_count
            
        except Exception as e:
            logger.error(f"Failed to cleanup files: {e}")
            return 0
    
    def get_file_info(self, file_id: str) -> Optional[Dict[str, Any]]:
        """Get file metadata and status"""
        return self._load_metadata(file_id)
    
    def _save_metadata(self, file_id: str, metadata: Dict[str, Any]):
        """Save file metadata"""
        try:
            metadata_dir = self.temp_dir / "metadata"
            metadata_dir.mkdir(exist_ok=True)
            
            metadata_file = metadata_dir / f"{file_id}.json"
            with open(metadata_file, 'w', encoding='utf-8') as f:
                json.dump(metadata, f, ensure_ascii=False, indent=2)
                
        except Exception as e:
            logger.error(f"Failed to save metadata: {e}")
    
    def _load_metadata(self, file_id: str) -> Optional[Dict[str, Any]]:
        """Load file metadata"""
        try:
            metadata_dir = self.temp_dir / "metadata"
            metadata_file = metadata_dir / f"{file_id}.json"
            
            if not metadata_file.exists():
                return None
            
            with open(metadata_file, 'r', encoding='utf-8') as f:
                return json.load(f)
                
        except Exception as e:
            logger.error(f"Failed to load metadata: {e}")
            return None
    
    def update_processing_status(self, file_id: str, status: str, progress: int = 0, error: str = None):
        """Update file processing status"""
        try:
            metadata = self._load_metadata(file_id) or {}
            metadata.update({
                "status": status,
                "progress": progress,
                "last_updated": datetime.now().isoformat()
            })
            
            if error:
                metadata["error"] = error
            
            self._save_metadata(file_id, metadata)
            logger.info(f"Status updated for {file_id}: {status} ({progress}%)")
            
        except Exception as e:
            logger.error(f"Failed to update status: {e}")