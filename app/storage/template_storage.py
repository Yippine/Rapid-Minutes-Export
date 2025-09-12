"""
Template Storage Management System (E2 - Data Storage Layer)
Advanced template file management and version control
Implements SESE principle - Simple, Effective, Systematic, Exhaustive template handling
"""

import logging
import os
import shutil
import json
import hashlib
from typing import Dict, List, Optional, Union, Any
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta
from pathlib import Path
from enum import Enum

from ..config import settings

logger = logging.getLogger(__name__)


class TemplateStatus(Enum):
    """Template status"""
    DRAFT = "draft"
    ACTIVE = "active"
    INACTIVE = "inactive"
    DEPRECATED = "deprecated"
    CORRUPTED = "corrupted"


class TemplateCategory(Enum):
    """Template categories"""
    STANDARD = "standard"
    EXECUTIVE = "executive"
    PROJECT = "project"
    BOARD = "board"
    TEAM = "team"
    CUSTOM = "custom"


@dataclass
class TemplateMetadata:
    """Template metadata"""
    template_id: str
    name: str
    description: str
    category: TemplateCategory
    version: str = "1.0.0"
    language: str = "zh-TW"
    author: str = "System"
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    status: TemplateStatus = TemplateStatus.ACTIVE
    file_path: str = ""
    file_size: int = 0
    file_hash: str = ""
    tags: List[str] = field(default_factory=list)
    field_mappings: Dict[str, str] = field(default_factory=dict)
    usage_count: int = 0
    last_used: Optional[datetime] = None
    compatibility_version: str = "1.0"
    preview_image: Optional[str] = None


@dataclass
class TemplateValidationResult:
    """Template validation result"""
    is_valid: bool
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    field_count: int = 0
    supported_fields: List[str] = field(default_factory=list)
    missing_required_fields: List[str] = field(default_factory=list)


class TemplateStorage:
    """
    Template storage management system
    Handles template files, metadata, versions, and validation
    """
    
    def __init__(self, templates_dir: Optional[str] = None):
        """Initialize template storage"""
        self.templates_dir = templates_dir or settings.templates_dir
        self.metadata_dir = os.path.join(self.templates_dir, '.metadata')
        self.versions_dir = os.path.join(self.templates_dir, '.versions')
        self.previews_dir = os.path.join(self.templates_dir, '.previews')
        
        # Ensure directories exist
        for directory in [self.templates_dir, self.metadata_dir, self.versions_dir, self.previews_dir]:
            os.makedirs(directory, exist_ok=True)
        
        # Template registry
        self._templates: Dict[str, TemplateMetadata] = {}
        
        # Required template fields
        self._required_fields = [
            'MEETING_TITLE', 'MEETING_DATE', 'ATTENDEES_LIST'
        ]
        
        # Supported file extensions
        self._supported_extensions = ['.docx', '.doc', '.odt', '.rtf']
        
        # Load existing templates
        self._load_templates()
        
        logger.info(f"📚 Template Storage initialized - {len(self._templates)} templates loaded")
    
    async def add_template(
        self,
        file_path: str,
        name: str,
        description: str,
        category: TemplateCategory,
        metadata: Optional[Dict] = None
    ) -> Optional[TemplateMetadata]:
        """
        Add new template to storage
        
        Args:
            file_path: Path to template file
            name: Template name
            description: Template description
            category: Template category
            metadata: Additional metadata
            
        Returns:
            TemplateMetadata if successful
        """
        if not os.path.exists(file_path):
            logger.error(f"❌ Template file not found: {file_path}")
            return None
        
        # Validate file extension
        file_ext = Path(file_path).suffix.lower()
        if file_ext not in self._supported_extensions:
            logger.error(f"❌ Unsupported file type: {file_ext}")
            return None
        
        try:
            # Generate template ID
            template_id = self._generate_template_id(name, category)
            
            # Create template storage path
            template_filename = f"{template_id}{file_ext}"
            storage_path = os.path.join(self.templates_dir, template_filename)
            
            # Copy template file
            shutil.copy2(file_path, storage_path)
            
            # Calculate file hash
            file_hash = await self._calculate_file_hash(storage_path)
            file_size = os.path.getsize(storage_path)
            
            # Create metadata
            template_metadata = TemplateMetadata(
                template_id=template_id,
                name=name,
                description=description,
                category=category,
                file_path=storage_path,
                file_size=file_size,
                file_hash=file_hash,
                **(metadata or {})
            )
            
            # Validate template
            validation_result = await self.validate_template(template_id)
            if not validation_result.is_valid:
                logger.warning(f"⚠️ Template validation issues: {validation_result.errors}")
                # Don't fail on validation issues, but log them
            
            # Save metadata
            await self._save_template_metadata(template_metadata)
            
            # Add to registry
            self._templates[template_id] = template_metadata
            
            logger.info(f"✅ Template added: {template_id}")
            return template_metadata
            
        except Exception as e:
            logger.error(f"❌ Failed to add template: {e}")
            return None
    
    async def get_template(self, template_id: str) -> Optional[TemplateMetadata]:
        """Get template metadata"""
        return self._templates.get(template_id)
    
    async def update_template(
        self,
        template_id: str,
        file_path: Optional[str] = None,
        metadata_updates: Optional[Dict] = None
    ) -> bool:
        """
        Update existing template
        
        Args:
            template_id: Template ID
            file_path: New template file path (optional)
            metadata_updates: Metadata updates
            
        Returns:
            Success status
        """
        if template_id not in self._templates:
            logger.error(f"❌ Template not found: {template_id}")
            return False
        
        try:
            template_metadata = self._templates[template_id]
            
            # Update file if provided
            if file_path and os.path.exists(file_path):
                # Create version backup
                await self._create_version_backup(template_id)
                
                # Update file
                shutil.copy2(file_path, template_metadata.file_path)
                
                # Update file metadata
                template_metadata.file_size = os.path.getsize(template_metadata.file_path)
                template_metadata.file_hash = await self._calculate_file_hash(template_metadata.file_path)
                template_metadata.updated_at = datetime.utcnow()
                
                # Increment version
                template_metadata.version = self._increment_version(template_metadata.version)
            
            # Update metadata
            if metadata_updates:
                for key, value in metadata_updates.items():
                    if hasattr(template_metadata, key):
                        setattr(template_metadata, key, value)
                template_metadata.updated_at = datetime.utcnow()
            
            # Save updated metadata
            await self._save_template_metadata(template_metadata)
            
            logger.info(f"✅ Template updated: {template_id}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to update template {template_id}: {e}")
            return False
    
    async def delete_template(self, template_id: str, permanent: bool = False) -> bool:
        """
        Delete template
        
        Args:
            template_id: Template ID
            permanent: If True, permanently delete; otherwise mark as deprecated
            
        Returns:
            Success status
        """
        if template_id not in self._templates:
            logger.error(f"❌ Template not found: {template_id}")
            return False
        
        try:
            template_metadata = self._templates[template_id]
            
            if permanent:
                # Remove file
                if os.path.exists(template_metadata.file_path):
                    os.remove(template_metadata.file_path)
                
                # Remove metadata
                metadata_file = os.path.join(self.metadata_dir, f"{template_id}.json")
                if os.path.exists(metadata_file):
                    os.remove(metadata_file)
                
                # Remove from registry
                del self._templates[template_id]
                
                logger.info(f"🗑️ Template permanently deleted: {template_id}")
            else:
                # Mark as deprecated
                template_metadata.status = TemplateStatus.DEPRECATED
                template_metadata.updated_at = datetime.utcnow()
                await self._save_template_metadata(template_metadata)
                
                logger.info(f"📦 Template marked as deprecated: {template_id}")
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to delete template {template_id}: {e}")
            return False
    
    async def list_templates(
        self,
        category: Optional[TemplateCategory] = None,
        status: Optional[TemplateStatus] = None,
        search_query: Optional[str] = None
    ) -> List[TemplateMetadata]:
        """
        List templates with optional filtering
        
        Args:
            category: Filter by category
            status: Filter by status
            search_query: Search in name/description
            
        Returns:
            List of template metadata
        """
        templates = list(self._templates.values())
        
        # Apply filters
        if category:
            templates = [t for t in templates if t.category == category]
        
        if status:
            templates = [t for t in templates if t.status == status]
        
        if search_query:
            query = search_query.lower()
            templates = [
                t for t in templates
                if query in t.name.lower() or query in t.description.lower() or query in ' '.join(t.tags).lower()
            ]
        
        # Sort by usage and update time
        templates.sort(key=lambda t: (t.usage_count, t.updated_at), reverse=True)
        
        return templates
    
    async def validate_template(self, template_id: str) -> TemplateValidationResult:
        """
        Validate template file and content
        
        Args:
            template_id: Template ID
            
        Returns:
            TemplateValidationResult
        """
        if template_id not in self._templates:
            return TemplateValidationResult(
                is_valid=False,
                errors=["Template not found"]
            )
        
        template_metadata = self._templates[template_id]
        
        try:
            # Check file exists
            if not os.path.exists(template_metadata.file_path):
                return TemplateValidationResult(
                    is_valid=False,
                    errors=["Template file not found"]
                )
            
            # Check file integrity
            current_hash = await self._calculate_file_hash(template_metadata.file_path)
            if current_hash != template_metadata.file_hash:
                return TemplateValidationResult(
                    is_valid=False,
                    errors=["Template file corrupted - hash mismatch"]
                )
            
            # Validate template content
            validation_result = await self._validate_template_content(template_metadata.file_path)
            
            return validation_result
            
        except Exception as e:
            return TemplateValidationResult(
                is_valid=False,
                errors=[f"Validation error: {str(e)}"]
            )
    
    async def get_template_usage_stats(self, template_id: str) -> Dict[str, Any]:
        """Get template usage statistics"""
        if template_id not in self._templates:
            return {}
        
        template_metadata = self._templates[template_id]
        
        return {
            'template_id': template_id,
            'usage_count': template_metadata.usage_count,
            'last_used': template_metadata.last_used.isoformat() if template_metadata.last_used else None,
            'created_at': template_metadata.created_at.isoformat(),
            'updated_at': template_metadata.updated_at.isoformat(),
            'version': template_metadata.version,
            'status': template_metadata.status.value
        }
    
    async def increment_usage_count(self, template_id: str) -> bool:
        """Increment template usage count"""
        if template_id not in self._templates:
            return False
        
        try:
            template_metadata = self._templates[template_id]
            template_metadata.usage_count += 1
            template_metadata.last_used = datetime.utcnow()
            
            await self._save_template_metadata(template_metadata)
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to increment usage count for {template_id}: {e}")
            return False
    
    async def create_template_backup(self, template_id: str) -> Optional[str]:
        """Create template backup"""
        if template_id not in self._templates:
            return None
        
        try:
            return await self._create_version_backup(template_id)
        except Exception as e:
            logger.error(f"❌ Failed to create backup for {template_id}: {e}")
            return None
    
    def get_storage_stats(self) -> Dict[str, Any]:
        """Get storage statistics"""
        total_templates = len(self._templates)
        
        # Status distribution
        status_counts = {}
        for status in TemplateStatus:
            status_counts[status.value] = sum(
                1 for t in self._templates.values() if t.status == status
            )
        
        # Category distribution
        category_counts = {}
        for category in TemplateCategory:
            category_counts[category.value] = sum(
                1 for t in self._templates.values() if t.category == category
            )
        
        # Storage usage
        total_size = sum(t.file_size for t in self._templates.values())
        
        return {
            'total_templates': total_templates,
            'status_distribution': status_counts,
            'category_distribution': category_counts,
            'total_storage_bytes': total_size,
            'average_file_size': total_size / total_templates if total_templates > 0 else 0
        }
    
    # Private methods
    
    def _generate_template_id(self, name: str, category: TemplateCategory) -> str:
        """Generate unique template ID"""
        # Clean name for ID
        clean_name = "".join(c for c in name if c.isalnum() or c in (' ', '_', '-')).strip()
        clean_name = clean_name.replace(' ', '_').lower()[:20]
        
        # Add timestamp for uniqueness
        timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
        
        return f"{category.value}_{clean_name}_{timestamp}"
    
    async def _calculate_file_hash(self, file_path: str) -> str:
        """Calculate file SHA256 hash"""
        hash_sha256 = hashlib.sha256()
        try:
            with open(file_path, 'rb') as f:
                for chunk in iter(lambda: f.read(4096), b""):
                    hash_sha256.update(chunk)
            return hash_sha256.hexdigest()
        except Exception as e:
            logger.error(f"❌ Failed to calculate hash for {file_path}: {e}")
            return ""
    
    async def _save_template_metadata(self, template_metadata: TemplateMetadata):
        """Save template metadata to JSON file"""
        metadata_file = os.path.join(self.metadata_dir, f"{template_metadata.template_id}.json")
        
        try:
            # Convert dataclass to dict for JSON serialization
            metadata_dict = asdict(template_metadata)
            
            # Convert datetime objects to ISO strings
            for key, value in metadata_dict.items():
                if isinstance(value, datetime):
                    metadata_dict[key] = value.isoformat()
            
            # Convert enums to strings
            metadata_dict['category'] = template_metadata.category.value
            metadata_dict['status'] = template_metadata.status.value
            
            with open(metadata_file, 'w', encoding='utf-8') as f:
                json.dump(metadata_dict, f, ensure_ascii=False, indent=2)
                
        except Exception as e:
            logger.error(f"❌ Failed to save metadata for {template_metadata.template_id}: {e}")
    
    def _load_templates(self):
        """Load existing templates from metadata files"""
        if not os.path.exists(self.metadata_dir):
            return
        
        for metadata_file in os.listdir(self.metadata_dir):
            if metadata_file.endswith('.json'):
                try:
                    file_path = os.path.join(self.metadata_dir, metadata_file)
                    with open(file_path, 'r', encoding='utf-8') as f:
                        metadata_dict = json.load(f)
                    
                    # Convert back to proper types
                    if 'created_at' in metadata_dict:
                        metadata_dict['created_at'] = datetime.fromisoformat(metadata_dict['created_at'])
                    if 'updated_at' in metadata_dict:
                        metadata_dict['updated_at'] = datetime.fromisoformat(metadata_dict['updated_at'])
                    if 'last_used' in metadata_dict and metadata_dict['last_used']:
                        metadata_dict['last_used'] = datetime.fromisoformat(metadata_dict['last_used'])
                    
                    # Convert enum strings back to enums
                    metadata_dict['category'] = TemplateCategory(metadata_dict['category'])
                    metadata_dict['status'] = TemplateStatus(metadata_dict['status'])
                    
                    # Create metadata object
                    template_metadata = TemplateMetadata(**metadata_dict)
                    
                    # Add to registry
                    self._templates[template_metadata.template_id] = template_metadata
                    
                except Exception as e:
                    logger.warning(f"⚠️ Failed to load template metadata {metadata_file}: {e}")
    
    async def _create_version_backup(self, template_id: str) -> str:
        """Create version backup of template"""
        template_metadata = self._templates[template_id]
        
        # Create version filename
        timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
        file_ext = Path(template_metadata.file_path).suffix
        version_filename = f"{template_id}_v{template_metadata.version}_{timestamp}{file_ext}"
        version_path = os.path.join(self.versions_dir, version_filename)
        
        # Copy file to versions directory
        shutil.copy2(template_metadata.file_path, version_path)
        
        logger.info(f"📦 Version backup created: {version_filename}")
        return version_path
    
    def _increment_version(self, version: str) -> str:
        """Increment version number"""
        try:
            parts = version.split('.')
            if len(parts) >= 3:
                # Increment patch version
                parts[2] = str(int(parts[2]) + 1)
                return '.'.join(parts)
            else:
                # Fallback: append .1
                return f"{version}.1"
        except:
            # Fallback: use timestamp
            return datetime.utcnow().strftime('%Y.%m.%d')
    
    async def _validate_template_content(self, file_path: str) -> TemplateValidationResult:
        """Validate template file content"""
        errors = []
        warnings = []
        supported_fields = []
        
        try:
            # Basic file validation
            if not os.path.exists(file_path):
                errors.append("Template file does not exist")
                return TemplateValidationResult(is_valid=False, errors=errors)
            
            # File size validation
            file_size = os.path.getsize(file_path)
            if file_size == 0:
                errors.append("Template file is empty")
            elif file_size > 50 * 1024 * 1024:  # 50MB limit
                warnings.append("Template file is very large (>50MB)")
            
            # Try to read file content for field validation
            try:
                if file_path.endswith('.docx'):
                    # For DOCX files, we would need python-docx to read content
                    # For now, just validate the file extension and size
                    supported_fields = ['MEETING_TITLE', 'MEETING_DATE', 'ATTENDEES_LIST']
                else:
                    # For other file types, try to read as text
                    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                        content = f.read()
                        # Look for template placeholders
                        import re
                        placeholders = re.findall(r'\{\{([^}]+)\}\}', content)
                        supported_fields = list(set(placeholders))
            
            except Exception as e:
                warnings.append(f"Could not analyze template content: {str(e)}")
            
            # Check for required fields
            missing_required = [
                field for field in self._required_fields
                if field not in supported_fields
            ]
            
            if missing_required:
                warnings.append(f"Missing recommended fields: {', '.join(missing_required)}")
            
            is_valid = len(errors) == 0
            
            return TemplateValidationResult(
                is_valid=is_valid,
                errors=errors,
                warnings=warnings,
                field_count=len(supported_fields),
                supported_fields=supported_fields,
                missing_required_fields=missing_required
            )
            
        except Exception as e:
            return TemplateValidationResult(
                is_valid=False,
                errors=[f"Validation failed: {str(e)}"]
            )