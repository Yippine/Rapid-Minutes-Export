"""
Data Cleanup and Maintenance Manager (E5 - Data Storage Layer)
Automated cleanup and maintenance system for storage optimization
Implements SESE principle - Simple, Effective, Systematic, Exhaustive cleanup
"""

import logging
import os
import shutil
import asyncio
import schedule
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta
from pathlib import Path
from enum import Enum
import json
from concurrent.futures import ThreadPoolExecutor

from ..config import settings

logger = logging.getLogger(__name__)


class CleanupType(Enum):
    """Cleanup operation types"""
    TEMP_FILES = "temp_files"
    OLD_OUTPUTS = "old_outputs"  
    ORPHANED_FILES = "orphaned_files"
    CORRUPTED_FILES = "corrupted_files"
    LARGE_FILES = "large_files"
    LOG_FILES = "log_files"
    CACHE_FILES = "cache_files"


class CleanupStatus(Enum):
    """Cleanup operation status"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class CleanupRule:
    """Cleanup rule definition"""
    rule_id: str
    name: str
    description: str
    cleanup_type: CleanupType
    enabled: bool = True
    schedule_cron: Optional[str] = None  # Cron expression
    max_age_days: Optional[int] = None
    max_size_mb: Optional[int] = None
    file_patterns: List[str] = field(default_factory=list)
    exclude_patterns: List[str] = field(default_factory=list)
    target_directories: List[str] = field(default_factory=list)
    dry_run: bool = False
    created_at: datetime = field(default_factory=datetime.utcnow)
    last_executed: Optional[datetime] = None


@dataclass
class CleanupOperation:
    """Cleanup operation tracking"""
    operation_id: str
    rule_id: str
    status: CleanupStatus
    started_at: datetime
    completed_at: Optional[datetime] = None
    files_scanned: int = 0
    files_deleted: int = 0
    bytes_freed: int = 0
    errors: List[str] = field(default_factory=list)
    dry_run: bool = False


@dataclass
class MaintenanceStats:
    """System maintenance statistics"""
    total_operations: int = 0
    successful_operations: int = 0
    failed_operations: int = 0
    total_files_cleaned: int = 0
    total_bytes_freed: int = 0
    last_cleanup: Optional[datetime] = None
    storage_usage: Dict[str, int] = field(default_factory=dict)


class CleanupManager:
    """
    Data cleanup and maintenance manager
    Handles automated cleanup, storage optimization, and system maintenance
    """
    
    def __init__(self, storage_dirs: Optional[Dict[str, str]] = None):
        """Initialize cleanup manager"""
        self.storage_dirs = storage_dirs or {
            'temp': settings.temp_dir,
            'uploads': settings.upload_dir,
            'outputs': settings.output_dir,
            'templates': settings.templates_dir,
            'logs': getattr(settings, 'log_dir', '/tmp/logs'),
            'cache': getattr(settings, 'cache_dir', '/tmp/cache')
        }
        
        # Ensure directories exist
        for dir_path in self.storage_dirs.values():
            os.makedirs(dir_path, exist_ok=True)
        
        # Cleanup configuration
        self.config_dir = os.path.join(settings.base_dir, '.cleanup')
        self.rules_file = os.path.join(self.config_dir, 'rules.json')
        self.stats_file = os.path.join(self.config_dir, 'stats.json')
        
        os.makedirs(self.config_dir, exist_ok=True)
        
        # Initialize components
        self.cleanup_rules: Dict[str, CleanupRule] = {}
        self.active_operations: Dict[str, CleanupOperation] = {}
        self.maintenance_stats = MaintenanceStats()
        
        # Thread pool for cleanup operations
        self.executor = ThreadPoolExecutor(max_workers=2)
        
        # Load configuration
        self._load_configuration()
        self._create_default_rules()
        
        logger.info(f"🧹 Cleanup Manager initialized - {len(self.cleanup_rules)} rules loaded")
    
    async def add_cleanup_rule(self, rule: CleanupRule) -> bool:
        """
        Add new cleanup rule
        
        Args:
            rule: CleanupRule object
            
        Returns:
            Success status
        """
        try:
            self.cleanup_rules[rule.rule_id] = rule
            await self._save_configuration()
            
            logger.info(f"✅ Cleanup rule added: {rule.rule_id}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to add cleanup rule {rule.rule_id}: {e}")
            return False
    
    async def execute_cleanup_rule(self, rule_id: str, dry_run: bool = False) -> Optional[CleanupOperation]:
        """
        Execute specific cleanup rule
        
        Args:
            rule_id: Rule ID to execute
            dry_run: If True, only simulate cleanup
            
        Returns:
            CleanupOperation if successful
        """
        if rule_id not in self.cleanup_rules:
            logger.error(f"❌ Cleanup rule not found: {rule_id}")
            return None
        
        rule = self.cleanup_rules[rule_id]
        
        if not rule.enabled:
            logger.warning(f"⚠️ Cleanup rule disabled: {rule_id}")
            return None
        
        # Create operation
        operation_id = f"{rule_id}_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"
        operation = CleanupOperation(
            operation_id=operation_id,
            rule_id=rule_id,
            status=CleanupStatus.PENDING,
            started_at=datetime.utcnow(),
            dry_run=dry_run or rule.dry_run
        )
        
        self.active_operations[operation_id] = operation
        
        try:
            logger.info(f"🧹 Starting cleanup operation: {operation_id} (dry_run={operation.dry_run})")
            operation.status = CleanupStatus.RUNNING
            
            # Execute cleanup based on type
            await self._execute_cleanup_by_type(rule, operation)
            
            # Mark as completed
            operation.status = CleanupStatus.COMPLETED
            operation.completed_at = datetime.utcnow()
            
            # Update rule execution time
            rule.last_executed = datetime.utcnow()
            await self._save_configuration()
            
            # Update statistics
            await self._update_maintenance_stats(operation)
            
            logger.info(f"✅ Cleanup completed: {operation_id} - {operation.files_deleted} files, {operation.bytes_freed} bytes freed")
            return operation
            
        except Exception as e:
            operation.status = CleanupStatus.FAILED
            operation.errors.append(str(e))
            operation.completed_at = datetime.utcnow()
            
            logger.error(f"❌ Cleanup failed: {operation_id} - {e}")
            return operation
    
    async def execute_all_cleanup_rules(self, dry_run: bool = False) -> Dict[str, CleanupOperation]:
        """
        Execute all enabled cleanup rules
        
        Args:
            dry_run: If True, only simulate cleanup
            
        Returns:
            Dict of operation results
        """
        results = {}
        
        for rule_id, rule in self.cleanup_rules.items():
            if rule.enabled:
                operation = await self.execute_cleanup_rule(rule_id, dry_run)
                if operation:
                    results[rule_id] = operation
                    
                # Small delay between operations
                await asyncio.sleep(0.1)
        
        return results
    
    async def schedule_automatic_cleanup(self) -> bool:
        """
        Schedule automatic cleanup operations
        
        Returns:
            Success status
        """
        try:
            # Clear existing schedule
            schedule.clear()
            
            # Schedule rules with cron expressions
            for rule in self.cleanup_rules.values():
                if rule.enabled and rule.schedule_cron:
                    try:
                        # Simple cron parsing - extend as needed
                        if rule.schedule_cron == "daily":
                            schedule.every().day.at("02:00").do(
                                lambda r=rule.rule_id: asyncio.create_task(self.execute_cleanup_rule(r))
                            )
                        elif rule.schedule_cron == "weekly":
                            schedule.every().week.do(
                                lambda r=rule.rule_id: asyncio.create_task(self.execute_cleanup_rule(r))
                            )
                        elif rule.schedule_cron.startswith("every_"):
                            # Format: "every_3_hours" or "every_30_minutes"
                            parts = rule.schedule_cron.split('_')
                            if len(parts) >= 3:
                                interval = int(parts[1])
                                unit = parts[2]
                                
                                if unit == "hours":
                                    schedule.every(interval).hours.do(
                                        lambda r=rule.rule_id: asyncio.create_task(self.execute_cleanup_rule(r))
                                    )
                                elif unit == "minutes":
                                    schedule.every(interval).minutes.do(
                                        lambda r=rule.rule_id: asyncio.create_task(self.execute_cleanup_rule(r))
                                    )
                        
                        logger.info(f"📅 Scheduled cleanup rule: {rule.rule_id} - {rule.schedule_cron}")
                        
                    except Exception as e:
                        logger.warning(f"⚠️ Failed to schedule rule {rule.rule_id}: {e}")
            
            logger.info(f"✅ Automatic cleanup scheduling completed - {len(schedule.jobs)} jobs scheduled")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to schedule automatic cleanup: {e}")
            return False
    
    async def get_storage_usage(self) -> Dict[str, Dict[str, Any]]:
        """
        Get current storage usage statistics
        
        Returns:
            Storage usage information
        """
        usage_info = {}
        
        for name, dir_path in self.storage_dirs.items():
            try:
                if os.path.exists(dir_path):
                    total_size = 0
                    file_count = 0
                    
                    for root, dirs, files in os.walk(dir_path):
                        for file in files:
                            file_path = os.path.join(root, file)
                            try:
                                file_size = os.path.getsize(file_path)
                                total_size += file_size
                                file_count += 1
                            except (OSError, IOError):
                                continue
                    
                    usage_info[name] = {
                        'directory': dir_path,
                        'total_size_bytes': total_size,
                        'total_size_mb': round(total_size / (1024 * 1024), 2),
                        'file_count': file_count,
                        'exists': True
                    }
                else:
                    usage_info[name] = {
                        'directory': dir_path,
                        'total_size_bytes': 0,
                        'total_size_mb': 0,
                        'file_count': 0,
                        'exists': False
                    }
                    
            except Exception as e:
                logger.error(f"❌ Failed to get usage for {name}: {e}")
                usage_info[name] = {'error': str(e)}
        
        return usage_info
    
    async def find_cleanup_candidates(self, rule_id: str) -> List[Dict[str, Any]]:
        """
        Find files that would be cleaned by a specific rule
        
        Args:
            rule_id: Cleanup rule ID
            
        Returns:
            List of candidate files
        """
        if rule_id not in self.cleanup_rules:
            return []
        
        rule = self.cleanup_rules[rule_id]
        candidates = []
        
        try:
            target_dirs = rule.target_directories or list(self.storage_dirs.values())
            
            for target_dir in target_dirs:
                if not os.path.exists(target_dir):
                    continue
                
                candidates.extend(await self._scan_directory_for_cleanup(target_dir, rule))
            
            return candidates
            
        except Exception as e:
            logger.error(f"❌ Failed to find cleanup candidates for {rule_id}: {e}")
            return []
    
    def get_cleanup_stats(self) -> Dict[str, Any]:
        """Get cleanup statistics"""
        active_count = sum(1 for op in self.active_operations.values() if op.status == CleanupStatus.RUNNING)
        
        return {
            'total_rules': len(self.cleanup_rules),
            'enabled_rules': sum(1 for rule in self.cleanup_rules.values() if rule.enabled),
            'active_operations': active_count,
            'maintenance_stats': asdict(self.maintenance_stats),
            'storage_directories': list(self.storage_dirs.keys())
        }
    
    # Private methods
    
    async def _execute_cleanup_by_type(self, rule: CleanupRule, operation: CleanupOperation):
        """Execute cleanup based on rule type"""
        target_dirs = rule.target_directories or list(self.storage_dirs.values())
        
        for target_dir in target_dirs:
            if not os.path.exists(target_dir):
                continue
            
            if rule.cleanup_type == CleanupType.TEMP_FILES:
                await self._cleanup_temp_files(target_dir, rule, operation)
            elif rule.cleanup_type == CleanupType.OLD_OUTPUTS:
                await self._cleanup_old_outputs(target_dir, rule, operation)
            elif rule.cleanup_type == CleanupType.ORPHANED_FILES:
                await self._cleanup_orphaned_files(target_dir, rule, operation)
            elif rule.cleanup_type == CleanupType.CORRUPTED_FILES:
                await self._cleanup_corrupted_files(target_dir, rule, operation)
            elif rule.cleanup_type == CleanupType.LARGE_FILES:
                await self._cleanup_large_files(target_dir, rule, operation)
            elif rule.cleanup_type == CleanupType.LOG_FILES:
                await self._cleanup_log_files(target_dir, rule, operation)
            elif rule.cleanup_type == CleanupType.CACHE_FILES:
                await self._cleanup_cache_files(target_dir, rule, operation)
    
    async def _cleanup_temp_files(self, target_dir: str, rule: CleanupRule, operation: CleanupOperation):
        """Cleanup temporary files"""
        cutoff_time = datetime.utcnow() - timedelta(days=rule.max_age_days or 1)
        
        for root, dirs, files in os.walk(target_dir):
            for file in files:
                file_path = os.path.join(root, file)
                operation.files_scanned += 1
                
                try:
                    # Check file age
                    file_mtime = datetime.fromtimestamp(os.path.getmtime(file_path))
                    if file_mtime < cutoff_time:
                        
                        # Check patterns
                        if self._matches_patterns(file, rule.file_patterns) and not self._matches_patterns(file, rule.exclude_patterns):
                            
                            file_size = os.path.getsize(file_path)
                            
                            if not operation.dry_run:
                                os.remove(file_path)
                            
                            operation.files_deleted += 1
                            operation.bytes_freed += file_size
                            
                            logger.debug(f"🗑️ {'[DRY RUN] ' if operation.dry_run else ''}Deleted temp file: {file_path}")
                
                except Exception as e:
                    operation.errors.append(f"Failed to process {file_path}: {str(e)}")
    
    async def _cleanup_old_outputs(self, target_dir: str, rule: CleanupRule, operation: CleanupOperation):
        """Cleanup old output files"""
        cutoff_time = datetime.utcnow() - timedelta(days=rule.max_age_days or 7)
        
        for root, dirs, files in os.walk(target_dir):
            for file in files:
                file_path = os.path.join(root, file)
                operation.files_scanned += 1
                
                try:
                    file_mtime = datetime.fromtimestamp(os.path.getmtime(file_path))
                    if file_mtime < cutoff_time:
                        
                        if self._matches_patterns(file, rule.file_patterns or ['*.docx', '*.pdf', '*.zip']):
                            
                            file_size = os.path.getsize(file_path)
                            
                            if not operation.dry_run:
                                os.remove(file_path)
                            
                            operation.files_deleted += 1
                            operation.bytes_freed += file_size
                            
                            logger.debug(f"🗑️ {'[DRY RUN] ' if operation.dry_run else ''}Deleted old output: {file_path}")
                
                except Exception as e:
                    operation.errors.append(f"Failed to process {file_path}: {str(e)}")
    
    async def _cleanup_large_files(self, target_dir: str, rule: CleanupRule, operation: CleanupOperation):
        """Cleanup large files"""
        max_size_bytes = (rule.max_size_mb or 100) * 1024 * 1024
        
        for root, dirs, files in os.walk(target_dir):
            for file in files:
                file_path = os.path.join(root, file)
                operation.files_scanned += 1
                
                try:
                    file_size = os.path.getsize(file_path)
                    if file_size > max_size_bytes:
                        
                        if not operation.dry_run:
                            os.remove(file_path)
                        
                        operation.files_deleted += 1
                        operation.bytes_freed += file_size
                        
                        logger.debug(f"🗑️ {'[DRY RUN] ' if operation.dry_run else ''}Deleted large file: {file_path} ({file_size} bytes)")
                
                except Exception as e:
                    operation.errors.append(f"Failed to process {file_path}: {str(e)}")
    
    async def _cleanup_orphaned_files(self, target_dir: str, rule: CleanupRule, operation: CleanupOperation):
        """Cleanup orphaned files with no references"""
        # Simple orphaned file detection - files older than specified age with no recent access
        cutoff_time = datetime.utcnow() - timedelta(days=rule.max_age_days or 30)
        
        for root, dirs, files in os.walk(target_dir):
            for file in files:
                file_path = os.path.join(root, file)
                operation.files_scanned += 1
                
                try:
                    file_stats = os.stat(file_path)
                    file_atime = datetime.fromtimestamp(file_stats.st_atime)
                    file_mtime = datetime.fromtimestamp(file_stats.st_mtime)
                    
                    # File is orphaned if both access and modification times are old
                    if file_atime < cutoff_time and file_mtime < cutoff_time:
                        
                        file_size = file_stats.st_size
                        
                        if not operation.dry_run:
                            os.remove(file_path)
                        
                        operation.files_deleted += 1
                        operation.bytes_freed += file_size
                        
                        logger.debug(f"🗑️ {'[DRY RUN] ' if operation.dry_run else ''}Deleted orphaned file: {file_path}")
                
                except Exception as e:
                    operation.errors.append(f"Failed to process {file_path}: {str(e)}")
    
    async def _cleanup_corrupted_files(self, target_dir: str, rule: CleanupRule, operation: CleanupOperation):
        """Cleanup corrupted files"""
        for root, dirs, files in os.walk(target_dir):
            for file in files:
                file_path = os.path.join(root, file)
                operation.files_scanned += 1
                
                try:
                    # Simple corruption detection - zero byte files or files that can't be read
                    file_size = os.path.getsize(file_path)
                    
                    is_corrupted = False
                    
                    if file_size == 0:
                        is_corrupted = True
                    else:
                        # Try to read the file
                        try:
                            with open(file_path, 'rb') as f:
                                f.read(1024)  # Try to read first 1KB
                        except Exception:
                            is_corrupted = True
                    
                    if is_corrupted:
                        if not operation.dry_run:
                            os.remove(file_path)
                        
                        operation.files_deleted += 1
                        operation.bytes_freed += file_size
                        
                        logger.debug(f"🗑️ {'[DRY RUN] ' if operation.dry_run else ''}Deleted corrupted file: {file_path}")
                
                except Exception as e:
                    operation.errors.append(f"Failed to process {file_path}: {str(e)}")
    
    async def _cleanup_log_files(self, target_dir: str, rule: CleanupRule, operation: CleanupOperation):
        """Cleanup old log files"""
        cutoff_time = datetime.utcnow() - timedelta(days=rule.max_age_days or 14)
        log_patterns = rule.file_patterns or ['*.log', '*.log.*', '*.out', '*.err']
        
        for root, dirs, files in os.walk(target_dir):
            for file in files:
                file_path = os.path.join(root, file)
                operation.files_scanned += 1
                
                try:
                    if self._matches_patterns(file, log_patterns):
                        file_mtime = datetime.fromtimestamp(os.path.getmtime(file_path))
                        if file_mtime < cutoff_time:
                            
                            file_size = os.path.getsize(file_path)
                            
                            if not operation.dry_run:
                                os.remove(file_path)
                            
                            operation.files_deleted += 1
                            operation.bytes_freed += file_size
                            
                            logger.debug(f"🗑️ {'[DRY RUN] ' if operation.dry_run else ''}Deleted log file: {file_path}")
                
                except Exception as e:
                    operation.errors.append(f"Failed to process {file_path}: {str(e)}")
    
    async def _cleanup_cache_files(self, target_dir: str, rule: CleanupRule, operation: CleanupOperation):
        """Cleanup cache files"""
        cutoff_time = datetime.utcnow() - timedelta(days=rule.max_age_days or 3)
        cache_patterns = rule.file_patterns or ['*.cache', '*.tmp', '*.temp', '__pycache__/*']
        
        for root, dirs, files in os.walk(target_dir):
            for file in files:
                file_path = os.path.join(root, file)
                operation.files_scanned += 1
                
                try:
                    if self._matches_patterns(file, cache_patterns) or '__pycache__' in root:
                        file_mtime = datetime.fromtimestamp(os.path.getmtime(file_path))
                        if file_mtime < cutoff_time:
                            
                            file_size = os.path.getsize(file_path)
                            
                            if not operation.dry_run:
                                os.remove(file_path)
                            
                            operation.files_deleted += 1
                            operation.bytes_freed += file_size
                            
                            logger.debug(f"🗑️ {'[DRY RUN] ' if operation.dry_run else ''}Deleted cache file: {file_path}")
                
                except Exception as e:
                    operation.errors.append(f"Failed to process {file_path}: {str(e)}")
    
    async def _scan_directory_for_cleanup(self, target_dir: str, rule: CleanupRule) -> List[Dict[str, Any]]:
        """Scan directory for cleanup candidates"""
        candidates = []
        
        for root, dirs, files in os.walk(target_dir):
            for file in files:
                file_path = os.path.join(root, file)
                
                try:
                    file_stats = os.stat(file_path)
                    file_info = {
                        'path': file_path,
                        'name': file,
                        'size': file_stats.st_size,
                        'modified': datetime.fromtimestamp(file_stats.st_mtime),
                        'accessed': datetime.fromtimestamp(file_stats.st_atime)
                    }
                    
                    # Check if file matches cleanup criteria
                    if self._would_cleanup_file(file_path, rule):
                        candidates.append(file_info)
                
                except Exception:
                    continue
        
        return candidates
    
    def _would_cleanup_file(self, file_path: str, rule: CleanupRule) -> bool:
        """Check if file would be cleaned by rule"""
        file_name = os.path.basename(file_path)
        
        try:
            file_stats = os.stat(file_path)
            file_size = file_stats.st_size
            file_mtime = datetime.fromtimestamp(file_stats.st_mtime)
            
            # Check age criteria
            if rule.max_age_days:
                cutoff_time = datetime.utcnow() - timedelta(days=rule.max_age_days)
                if file_mtime >= cutoff_time:
                    return False
            
            # Check size criteria
            if rule.max_size_mb:
                max_size_bytes = rule.max_size_mb * 1024 * 1024
                if file_size <= max_size_bytes:
                    return False
            
            # Check patterns
            if rule.file_patterns and not self._matches_patterns(file_name, rule.file_patterns):
                return False
            
            if rule.exclude_patterns and self._matches_patterns(file_name, rule.exclude_patterns):
                return False
            
            return True
            
        except Exception:
            return False
    
    def _matches_patterns(self, filename: str, patterns: List[str]) -> bool:
        """Check if filename matches any of the patterns"""
        import fnmatch
        
        if not patterns:
            return True
        
        for pattern in patterns:
            if fnmatch.fnmatch(filename.lower(), pattern.lower()):
                return True
        
        return False
    
    async def _update_maintenance_stats(self, operation: CleanupOperation):
        """Update maintenance statistics"""
        self.maintenance_stats.total_operations += 1
        
        if operation.status == CleanupStatus.COMPLETED:
            self.maintenance_stats.successful_operations += 1
        elif operation.status == CleanupStatus.FAILED:
            self.maintenance_stats.failed_operations += 1
        
        self.maintenance_stats.total_files_cleaned += operation.files_deleted
        self.maintenance_stats.total_bytes_freed += operation.bytes_freed
        self.maintenance_stats.last_cleanup = operation.completed_at
        
        # Update storage usage
        self.maintenance_stats.storage_usage = await self.get_storage_usage()
        
        # Save stats
        await self._save_maintenance_stats()
    
    def _create_default_rules(self):
        """Create default cleanup rules"""
        default_rules = [
            CleanupRule(
                rule_id="temp_files_daily",
                name="Daily Temp Files Cleanup",
                description="Clean temporary files older than 1 day",
                cleanup_type=CleanupType.TEMP_FILES,
                schedule_cron="daily",
                max_age_days=1,
                file_patterns=["*.tmp", "*.temp", "temp_*"],
                target_directories=[self.storage_dirs['temp']]
            ),
            CleanupRule(
                rule_id="old_outputs_weekly",
                name="Weekly Old Outputs Cleanup",
                description="Clean output files older than 7 days",
                cleanup_type=CleanupType.OLD_OUTPUTS,
                schedule_cron="weekly",
                max_age_days=7,
                file_patterns=["*.docx", "*.pdf", "*.zip"],
                target_directories=[self.storage_dirs['outputs']]
            ),
            CleanupRule(
                rule_id="large_files_monthly",
                name="Monthly Large Files Cleanup",
                description="Clean files larger than 100MB",
                cleanup_type=CleanupType.LARGE_FILES,
                schedule_cron="every_30_days",
                max_size_mb=100
            ),
            CleanupRule(
                rule_id="cache_files_daily",
                name="Daily Cache Cleanup",
                description="Clean cache files older than 3 days",
                cleanup_type=CleanupType.CACHE_FILES,
                schedule_cron="daily",
                max_age_days=3,
                file_patterns=["*.cache", "__pycache__/*", "*.pyc"]
            )
        ]
        
        for rule in default_rules:
            if rule.rule_id not in self.cleanup_rules:
                self.cleanup_rules[rule.rule_id] = rule
        
        # Save default rules
        asyncio.create_task(self._save_configuration())
    
    async def _save_configuration(self):
        """Save cleanup configuration"""
        try:
            config_data = {
                'rules': {
                    rule_id: asdict(rule) for rule_id, rule in self.cleanup_rules.items()
                }
            }
            
            # Convert enums and datetime objects for JSON serialization
            for rule_data in config_data['rules'].values():
                rule_data['cleanup_type'] = rule_data['cleanup_type'].value if isinstance(rule_data['cleanup_type'], CleanupType) else rule_data['cleanup_type']
                rule_data['created_at'] = rule_data['created_at'].isoformat() if isinstance(rule_data['created_at'], datetime) else rule_data['created_at']
                if rule_data['last_executed']:
                    rule_data['last_executed'] = rule_data['last_executed'].isoformat() if isinstance(rule_data['last_executed'], datetime) else rule_data['last_executed']
            
            with open(self.rules_file, 'w', encoding='utf-8') as f:
                json.dump(config_data, f, ensure_ascii=False, indent=2)
                
        except Exception as e:
            logger.error(f"❌ Failed to save cleanup configuration: {e}")
    
    def _load_configuration(self):
        """Load cleanup configuration"""
        try:
            if os.path.exists(self.rules_file):
                with open(self.rules_file, 'r', encoding='utf-8') as f:
                    config_data = json.load(f)
                
                for rule_id, rule_data in config_data.get('rules', {}).items():
                    # Convert back to proper types
                    rule_data['cleanup_type'] = CleanupType(rule_data['cleanup_type'])
                    rule_data['created_at'] = datetime.fromisoformat(rule_data['created_at'])
                    if rule_data['last_executed']:
                        rule_data['last_executed'] = datetime.fromisoformat(rule_data['last_executed'])
                    
                    self.cleanup_rules[rule_id] = CleanupRule(**rule_data)
                    
        except Exception as e:
            logger.warning(f"⚠️ Failed to load cleanup configuration: {e}")
    
    async def _save_maintenance_stats(self):
        """Save maintenance statistics"""
        try:
            stats_data = asdict(self.maintenance_stats)
            
            # Convert datetime objects
            if stats_data['last_cleanup']:
                stats_data['last_cleanup'] = stats_data['last_cleanup'].isoformat()
            
            with open(self.stats_file, 'w', encoding='utf-8') as f:
                json.dump(stats_data, f, ensure_ascii=False, indent=2)
                
        except Exception as e:
            logger.error(f"❌ Failed to save maintenance stats: {e}")