"""
AI Result Optimizer and Post-Processor (A5 - AI Processing Layer)
Advanced optimization and post-processing system for AI extraction results
Implements SESE principle - Simple, Effective, Systematic, Exhaustive optimization
"""

import logging
import re
import json
from typing import Dict, List, Optional, Any, Tuple, Union, Set
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta
from enum import Enum
import asyncio
from collections import defaultdict, Counter
import difflib

logger = logging.getLogger(__name__)


class OptimizationType(Enum):
    """Types of optimization operations"""
    CONTENT_ENHANCEMENT = "content_enhancement"
    STRUCTURE_NORMALIZATION = "structure_normalization"
    DATA_DEDUPLICATION = "data_deduplication"
    FORMAT_STANDARDIZATION = "format_standardization"
    QUALITY_IMPROVEMENT = "quality_improvement"
    COMPLETENESS_FILLING = "completeness_filling"


class OptimizationLevel(Enum):
    """Optimization intensity levels"""
    MINIMAL = "minimal"
    STANDARD = "standard"
    AGGRESSIVE = "aggressive"
    COMPREHENSIVE = "comprehensive"


@dataclass
class OptimizationRule:
    """Individual optimization rule"""
    rule_id: str
    name: str
    description: str
    optimization_type: OptimizationType
    enabled: bool = True
    priority: int = 1  # 1-5, where 5 is highest priority
    target_fields: List[str] = field(default_factory=list)
    conditions: Dict[str, Any] = field(default_factory=dict)
    parameters: Dict[str, Any] = field(default_factory=dict)


@dataclass
class OptimizationResult:
    """Result of a single optimization operation"""
    rule_id: str
    field_name: str
    original_value: Any
    optimized_value: Any
    improvement_score: float
    changes_made: List[str] = field(default_factory=list)
    confidence: float = 1.0
    processing_time_ms: float = 0.0


@dataclass
class OptimizationReport:
    """Complete optimization report"""
    process_id: str
    optimization_timestamp: datetime
    optimization_level: OptimizationLevel
    total_optimizations: int = 0
    successful_optimizations: int = 0
    failed_optimizations: int = 0
    overall_improvement_score: float = 0.0
    field_improvements: Dict[str, float] = field(default_factory=dict)
    optimization_results: List[OptimizationResult] = field(default_factory=list)
    before_stats: Dict[str, Any] = field(default_factory=dict)
    after_stats: Dict[str, Any] = field(default_factory=dict)
    processing_time_ms: float = 0.0
    warnings: List[str] = field(default_factory=list)


class ResultOptimizer:
    """
    AI Result Optimizer and Post-Processor
    Advanced system for optimizing and enhancing AI extraction results
    """
    
    def __init__(self, optimization_level: OptimizationLevel = OptimizationLevel.STANDARD):
        """Initialize result optimizer"""
        self.optimization_level = optimization_level
        self.optimization_rules: Dict[str, OptimizationRule] = {}
        
        # Optimization parameters based on level
        self.optimization_params = {
            OptimizationLevel.MINIMAL: {
                'max_rules': 3,
                'quality_threshold': 0.6,
                'enhancement_strength': 0.3
            },
            OptimizationLevel.STANDARD: {
                'max_rules': 6,
                'quality_threshold': 0.75,
                'enhancement_strength': 0.6
            },
            OptimizationLevel.AGGRESSIVE: {
                'max_rules': 10,
                'quality_threshold': 0.85,
                'enhancement_strength': 0.9
            },
            OptimizationLevel.COMPREHENSIVE: {
                'max_rules': 15,
                'quality_threshold': 0.9,
                'enhancement_strength': 1.0
            }
        }
        
        # Common patterns for text enhancement
        self.text_patterns = {
            # Fix common spacing issues
            'double_spaces': (r'\s{2,}', ' '),
            'space_punctuation': (r'\s+([,.!?;:])', r'\1'),
            'punctuation_space': (r'([,.!?;:])([^\s])', r'\1 \2'),
            
            # Fix common formatting issues
            'bullet_points': (r'^[\s]*[-•·]\s*', '• '),
            'number_list': (r'^[\s]*(\d+)[\.\)]\s*', r'\1. '),
            
            # Chinese punctuation fixes
            'chinese_punctuation': (r'([。，！？；：])', r'\1 '),
            'english_in_chinese': (r'([a-zA-Z])([。，！？；：])', r'\1 \2')
        }
        
        # Initialize optimization rules
        self._initialize_optimization_rules()
        
        logger.info(f"🔧 Result Optimizer initialized - Level: {optimization_level.value}")
    
    async def optimize_extraction_results(
        self,
        process_id: str,
        extracted_data: Dict[str, Any],
        original_text: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> Tuple[Dict[str, Any], OptimizationReport]:
        """
        Optimize AI extraction results
        
        Args:
            process_id: Processing operation ID
            extracted_data: Original extracted data
            original_text: Original input text for context
            context: Additional optimization context
            
        Returns:
            Tuple of (optimized_data, optimization_report)
        """
        start_time = datetime.utcnow()
        
        try:
            # Create optimization report
            report = OptimizationReport(
                process_id=process_id,
                optimization_timestamp=start_time,
                optimization_level=self.optimization_level
            )
            
            # Analyze input data
            report.before_stats = await self._analyze_data_stats(extracted_data)
            
            # Create a working copy
            optimized_data = await self._deep_copy_data(extracted_data)
            
            # Get applicable optimization rules
            applicable_rules = await self._get_applicable_rules(optimized_data, context)
            
            # Apply optimizations
            for rule in applicable_rules:
                if rule.enabled:
                    try:
                        optimization_result = await self._apply_optimization_rule(
                            rule, optimized_data, original_text, context
                        )
                        
                        if optimization_result:
                            report.optimization_results.append(optimization_result)
                            report.successful_optimizations += 1
                            
                            # Update field improvements
                            field_name = optimization_result.field_name
                            if field_name not in report.field_improvements:
                                report.field_improvements[field_name] = 0.0
                            report.field_improvements[field_name] += optimization_result.improvement_score
                        
                    except Exception as e:
                        report.failed_optimizations += 1
                        report.warnings.append(f"Failed to apply rule {rule.rule_id}: {str(e)}")
                        logger.warning(f"⚠️ Optimization rule failed {rule.rule_id}: {e}")
            
            # Post-processing cleanup
            optimized_data = await self._post_process_cleanup(optimized_data)
            
            # Calculate final statistics
            report.after_stats = await self._analyze_data_stats(optimized_data)
            report.total_optimizations = len(report.optimization_results)
            
            # Calculate overall improvement
            if report.optimization_results:
                improvement_scores = [result.improvement_score for result in report.optimization_results]
                report.overall_improvement_score = sum(improvement_scores) / len(improvement_scores)
            
            # Calculate processing time
            end_time = datetime.utcnow()
            report.processing_time_ms = (end_time - start_time).total_seconds() * 1000
            
            logger.info(f"✅ Result optimization completed: {process_id} - {report.successful_optimizations} improvements")
            return optimized_data, report
            
        except Exception as e:
            logger.error(f"❌ Result optimization failed for {process_id}: {e}")
            
            # Return original data with error report
            error_report = OptimizationReport(
                process_id=process_id,
                optimization_timestamp=start_time,
                optimization_level=self.optimization_level,
                warnings=[f"Optimization failed: {str(e)}"]
            )
            
            return extracted_data, error_report
    
    async def enhance_text_content(
        self,
        text: str,
        enhancement_type: str = "general",
        context: Optional[Dict[str, Any]] = None
    ) -> Tuple[str, List[str]]:
        """
        Enhance text content quality
        
        Args:
            text: Original text
            enhancement_type: Type of enhancement (general, meeting, action_item, etc.)
            context: Enhancement context
            
        Returns:
            Tuple of (enhanced_text, applied_changes)
        """
        if not text or not text.strip():
            return text, []
        
        enhanced_text = text
        applied_changes = []
        
        try:
            # Apply text pattern fixes
            for pattern_name, (pattern, replacement) in self.text_patterns.items():
                if re.search(pattern, enhanced_text):
                    enhanced_text = re.sub(pattern, replacement, enhanced_text)
                    applied_changes.append(f"Applied {pattern_name} fix")
            
            # Enhancement based on type
            if enhancement_type == "meeting":
                enhanced_text, meeting_changes = await self._enhance_meeting_text(enhanced_text, context)
                applied_changes.extend(meeting_changes)
            
            elif enhancement_type == "action_item":
                enhanced_text, action_changes = await self._enhance_action_item_text(enhanced_text, context)
                applied_changes.extend(action_changes)
            
            elif enhancement_type == "decision":
                enhanced_text, decision_changes = await self._enhance_decision_text(enhanced_text, context)
                applied_changes.extend(decision_changes)
            
            # General text quality improvements
            enhanced_text, quality_changes = await self._improve_text_quality(enhanced_text)
            applied_changes.extend(quality_changes)
            
            return enhanced_text.strip(), applied_changes
            
        except Exception as e:
            logger.error(f"❌ Text enhancement failed: {e}")
            return text, [f"Enhancement failed: {str(e)}"]
    
    async def normalize_data_structure(
        self,
        data: Dict[str, Any],
        target_schema: Optional[Dict[str, Any]] = None
    ) -> Tuple[Dict[str, Any], List[str]]:
        """
        Normalize data structure according to schema
        
        Args:
            data: Original data
            target_schema: Target schema definition
            
        Returns:
            Tuple of (normalized_data, applied_changes)
        """
        normalized_data = await self._deep_copy_data(data)
        applied_changes = []
        
        try:
            # Use default schema if not provided
            if not target_schema:
                target_schema = self._get_default_meeting_schema()
            
            # Ensure all required fields exist
            for field_name, field_config in target_schema.items():
                if field_name not in normalized_data:
                    default_value = field_config.get('default', '' if field_config.get('type') == 'string' else [])
                    normalized_data[field_name] = default_value
                    applied_changes.append(f"Added missing field: {field_name}")
                
                # Type conversion
                expected_type = field_config.get('type')
                current_value = normalized_data[field_name]
                
                if expected_type == 'list' and not isinstance(current_value, list):
                    if isinstance(current_value, str) and current_value.strip():
                        # Convert string to list
                        normalized_data[field_name] = [item.strip() for item in current_value.split('\n') if item.strip()]
                        applied_changes.append(f"Converted {field_name} from string to list")
                    else:
                        normalized_data[field_name] = []
                        applied_changes.append(f"Initialized empty list for {field_name}")
                
                elif expected_type == 'string' and not isinstance(current_value, str):
                    if isinstance(current_value, list):
                        normalized_data[field_name] = '\n'.join(str(item) for item in current_value if item)
                        applied_changes.append(f"Converted {field_name} from list to string")
                    else:
                        normalized_data[field_name] = str(current_value) if current_value else ''
                        applied_changes.append(f"Converted {field_name} to string")
            
            return normalized_data, applied_changes
            
        except Exception as e:
            logger.error(f"❌ Data normalization failed: {e}")
            return data, [f"Normalization failed: {str(e)}"]
    
    async def deduplicate_content(
        self,
        data: Dict[str, Any],
        similarity_threshold: float = 0.8
    ) -> Tuple[Dict[str, Any], List[str]]:
        """
        Remove duplicate content from data
        
        Args:
            data: Data to deduplicate
            similarity_threshold: Similarity threshold for deduplication
            
        Returns:
            Tuple of (deduplicated_data, applied_changes)
        """
        deduplicated_data = await self._deep_copy_data(data)
        applied_changes = []
        
        try:
            # Deduplicate list fields
            list_fields = ['ATTENDEES_LIST', 'AGENDA_ITEMS', 'ACTION_ITEMS', 'KEY_DECISIONS']
            
            for field_name in list_fields:
                if field_name in deduplicated_data and isinstance(deduplicated_data[field_name], list):
                    original_list = deduplicated_data[field_name]
                    deduplicated_list = await self._deduplicate_list(original_list, similarity_threshold)
                    
                    if len(deduplicated_list) < len(original_list):
                        deduplicated_data[field_name] = deduplicated_list
                        removed_count = len(original_list) - len(deduplicated_list)
                        applied_changes.append(f"Removed {removed_count} duplicate items from {field_name}")
            
            return deduplicated_data, applied_changes
            
        except Exception as e:
            logger.error(f"❌ Content deduplication failed: {e}")
            return data, [f"Deduplication failed: {str(e)}"]
    
    async def fill_missing_content(
        self,
        data: Dict[str, Any],
        original_text: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> Tuple[Dict[str, Any], List[str]]:
        """
        Fill missing content using intelligent analysis
        
        Args:
            data: Data with potentially missing content
            original_text: Original text for content extraction
            context: Additional context
            
        Returns:
            Tuple of (filled_data, applied_changes)
        """
        filled_data = await self._deep_copy_data(data)
        applied_changes = []
        
        try:
            # Fill missing required fields
            required_fields = ['MEETING_TITLE', 'MEETING_DATE', 'ATTENDEES_LIST']
            
            for field_name in required_fields:
                current_value = filled_data.get(field_name)
                
                if not current_value or (isinstance(current_value, str) and not current_value.strip()):
                    filled_value = await self._extract_missing_field(field_name, original_text, filled_data, context)
                    
                    if filled_value:
                        filled_data[field_name] = filled_value
                        applied_changes.append(f"Filled missing content for {field_name}")
            
            # Enhance existing content
            for field_name, field_value in filled_data.items():
                if isinstance(field_value, str) and field_value.strip() and len(field_value.strip()) < 10:
                    # Try to expand short content
                    expanded_content = await self._expand_short_content(field_name, field_value, original_text)
                    
                    if expanded_content and len(expanded_content) > len(field_value):
                        filled_data[field_name] = expanded_content
                        applied_changes.append(f"Expanded short content for {field_name}")
            
            return filled_data, applied_changes
            
        except Exception as e:
            logger.error(f"❌ Content filling failed: {e}")
            return data, [f"Content filling failed: {str(e)}"]
    
    def get_optimization_summary(self, report: OptimizationReport) -> Dict[str, Any]:
        """Get optimization summary"""
        return {
            'process_id': report.process_id,
            'optimization_level': report.optimization_level.value,
            'total_optimizations': report.total_optimizations,
            'successful_optimizations': report.successful_optimizations,
            'failed_optimizations': report.failed_optimizations,
            'overall_improvement_score': round(report.overall_improvement_score, 3),
            'field_improvements': {
                field: round(score, 3)
                for field, score in report.field_improvements.items()
            },
            'processing_time_ms': round(report.processing_time_ms, 2),
            'warnings_count': len(report.warnings),
            'before_stats': report.before_stats,
            'after_stats': report.after_stats
        }
    
    # Private methods
    
    def _initialize_optimization_rules(self):
        """Initialize default optimization rules"""
        rules = [
            OptimizationRule(
                rule_id="content_enhancement",
                name="Content Enhancement",
                description="Enhance text content quality and readability",
                optimization_type=OptimizationType.CONTENT_ENHANCEMENT,
                priority=5,
                target_fields=['MEETING_TITLE', 'MEETING_SUMMARY', 'KEY_DECISIONS', 'ACTION_ITEMS']
            ),
            OptimizationRule(
                rule_id="structure_normalization",
                name="Structure Normalization",
                description="Normalize data structure to standard format",
                optimization_type=OptimizationType.STRUCTURE_NORMALIZATION,
                priority=4,
                target_fields=['ATTENDEES_LIST', 'AGENDA_ITEMS', 'ACTION_ITEMS']
            ),
            OptimizationRule(
                rule_id="data_deduplication",
                name="Data Deduplication",
                description="Remove duplicate content and entries",
                optimization_type=OptimizationType.DATA_DEDUPLICATION,
                priority=3,
                target_fields=['ATTENDEES_LIST', 'AGENDA_ITEMS', 'ACTION_ITEMS', 'KEY_DECISIONS']
            ),
            OptimizationRule(
                rule_id="format_standardization",
                name="Format Standardization",
                description="Standardize date, name, and other format conventions",
                optimization_type=OptimizationType.FORMAT_STANDARDIZATION,
                priority=2,
                target_fields=['MEETING_DATE', 'ATTENDEES_LIST']
            ),
            OptimizationRule(
                rule_id="completeness_filling",
                name="Completeness Filling",
                description="Fill missing content using intelligent analysis",
                optimization_type=OptimizationType.COMPLETENESS_FILLING,
                priority=1,
                target_fields=['MEETING_TITLE', 'MEETING_DATE', 'ATTENDEES_LIST']
            )
        ]
        
        for rule in rules:
            self.optimization_rules[rule.rule_id] = rule
    
    async def _get_applicable_rules(
        self,
        data: Dict[str, Any],
        context: Optional[Dict[str, Any]]
    ) -> List[OptimizationRule]:
        """Get applicable optimization rules"""
        applicable_rules = []
        max_rules = self.optimization_params[self.optimization_level]['max_rules']
        
        # Sort rules by priority (descending)
        sorted_rules = sorted(
            self.optimization_rules.values(),
            key=lambda r: r.priority,
            reverse=True
        )
        
        for rule in sorted_rules[:max_rules]:
            if rule.enabled:
                # Check if rule is applicable to current data
                if await self._is_rule_applicable(rule, data, context):
                    applicable_rules.append(rule)
        
        return applicable_rules
    
    async def _is_rule_applicable(
        self,
        rule: OptimizationRule,
        data: Dict[str, Any],
        context: Optional[Dict[str, Any]]
    ) -> bool:
        """Check if optimization rule is applicable"""
        # Check if target fields exist in data
        if rule.target_fields:
            has_target_fields = any(field in data for field in rule.target_fields)
            if not has_target_fields:
                return False
        
        # Check conditions
        if rule.conditions:
            for condition_key, condition_value in rule.conditions.items():
                if condition_key == 'min_quality_score':
                    # Check if data quality is below threshold
                    data_quality = await self._calculate_data_quality(data)
                    if data_quality >= condition_value:
                        return False
        
        return True
    
    async def _apply_optimization_rule(
        self,
        rule: OptimizationRule,
        data: Dict[str, Any],
        original_text: Optional[str],
        context: Optional[Dict[str, Any]]
    ) -> Optional[OptimizationResult]:
        """Apply single optimization rule"""
        start_time = datetime.utcnow()
        
        try:
            if rule.optimization_type == OptimizationType.CONTENT_ENHANCEMENT:
                return await self._apply_content_enhancement(rule, data, original_text, context)
            
            elif rule.optimization_type == OptimizationType.STRUCTURE_NORMALIZATION:
                return await self._apply_structure_normalization(rule, data, context)
            
            elif rule.optimization_type == OptimizationType.DATA_DEDUPLICATION:
                return await self._apply_data_deduplication(rule, data, context)
            
            elif rule.optimization_type == OptimizationType.FORMAT_STANDARDIZATION:
                return await self._apply_format_standardization(rule, data, context)
            
            elif rule.optimization_type == OptimizationType.COMPLETENESS_FILLING:
                return await self._apply_completeness_filling(rule, data, original_text, context)
            
            else:
                logger.warning(f"⚠️ Unknown optimization type: {rule.optimization_type}")
                return None
                
        except Exception as e:
            logger.error(f"❌ Failed to apply optimization rule {rule.rule_id}: {e}")
            return None
    
    async def _apply_content_enhancement(
        self,
        rule: OptimizationRule,
        data: Dict[str, Any],
        original_text: Optional[str],
        context: Optional[Dict[str, Any]]
    ) -> Optional[OptimizationResult]:
        """Apply content enhancement optimization"""
        for field_name in rule.target_fields:
            if field_name in data:
                original_value = data[field_name]
                
                if isinstance(original_value, str) and original_value.strip():
                    enhanced_text, changes = await self.enhance_text_content(
                        original_value,
                        enhancement_type=self._get_enhancement_type(field_name),
                        context=context
                    )
                    
                    if enhanced_text != original_value:
                        data[field_name] = enhanced_text
                        
                        # Calculate improvement score
                        improvement_score = await self._calculate_text_improvement(original_value, enhanced_text)
                        
                        return OptimizationResult(
                            rule_id=rule.rule_id,
                            field_name=field_name,
                            original_value=original_value,
                            optimized_value=enhanced_text,
                            improvement_score=improvement_score,
                            changes_made=changes,
                            confidence=0.8
                        )
        
        return None
    
    async def _apply_structure_normalization(
        self,
        rule: OptimizationRule,
        data: Dict[str, Any],
        context: Optional[Dict[str, Any]]
    ) -> Optional[OptimizationResult]:
        """Apply structure normalization optimization"""
        normalized_data, changes = await self.normalize_data_structure(data)
        
        if changes:
            # Update data with normalized values
            for field_name in rule.target_fields:
                if field_name in normalized_data and field_name in data:
                    data[field_name] = normalized_data[field_name]
            
            return OptimizationResult(
                rule_id=rule.rule_id,
                field_name="structure",
                original_value=data,
                optimized_value=normalized_data,
                improvement_score=0.7,
                changes_made=changes,
                confidence=0.9
            )
        
        return None
    
    async def _apply_data_deduplication(
        self,
        rule: OptimizationRule,
        data: Dict[str, Any],
        context: Optional[Dict[str, Any]]
    ) -> Optional[OptimizationResult]:
        """Apply data deduplication optimization"""
        deduplicated_data, changes = await self.deduplicate_content(data)
        
        if changes:
            # Update data with deduplicated values
            for field_name in rule.target_fields:
                if field_name in deduplicated_data:
                    data[field_name] = deduplicated_data[field_name]
            
            return OptimizationResult(
                rule_id=rule.rule_id,
                field_name="deduplication",
                original_value=data,
                optimized_value=deduplicated_data,
                improvement_score=0.6,
                changes_made=changes,
                confidence=0.95
            )
        
        return None
    
    async def _apply_format_standardization(
        self,
        rule: OptimizationRule,
        data: Dict[str, Any],
        context: Optional[Dict[str, Any]]
    ) -> Optional[OptimizationResult]:
        """Apply format standardization optimization"""
        changes_made = []
        
        # Date format standardization
        if 'MEETING_DATE' in data and 'MEETING_DATE' in rule.target_fields:
            original_date = data['MEETING_DATE']
            if isinstance(original_date, str) and original_date.strip():
                standardized_date = await self._standardize_date_format(original_date)
                if standardized_date != original_date:
                    data['MEETING_DATE'] = standardized_date
                    changes_made.append(f"Standardized date format: {original_date} -> {standardized_date}")
        
        # Name format standardization
        if 'ATTENDEES_LIST' in data and 'ATTENDEES_LIST' in rule.target_fields:
            original_attendees = data['ATTENDEES_LIST']
            if isinstance(original_attendees, list):
                standardized_attendees = [await self._standardize_name_format(name) for name in original_attendees if name]
                if standardized_attendees != original_attendees:
                    data['ATTENDEES_LIST'] = standardized_attendees
                    changes_made.append("Standardized attendee name formats")
        
        if changes_made:
            return OptimizationResult(
                rule_id=rule.rule_id,
                field_name="format",
                original_value="various",
                optimized_value="standardized",
                improvement_score=0.5,
                changes_made=changes_made,
                confidence=0.85
            )
        
        return None
    
    async def _apply_completeness_filling(
        self,
        rule: OptimizationRule,
        data: Dict[str, Any],
        original_text: Optional[str],
        context: Optional[Dict[str, Any]]
    ) -> Optional[OptimizationResult]:
        """Apply completeness filling optimization"""
        filled_data, changes = await self.fill_missing_content(data, original_text, context)
        
        if changes:
            # Update data with filled values
            for field_name in rule.target_fields:
                if field_name in filled_data:
                    data[field_name] = filled_data[field_name]
            
            return OptimizationResult(
                rule_id=rule.rule_id,
                field_name="completeness",
                original_value=data,
                optimized_value=filled_data,
                improvement_score=0.8,
                changes_made=changes,
                confidence=0.7
            )
        
        return None
    
    async def _enhance_meeting_text(self, text: str, context: Optional[Dict[str, Any]]) -> Tuple[str, List[str]]:
        """Enhance meeting-specific text"""
        enhanced_text = text
        changes = []
        
        # Add meeting context if available
        if context and 'meeting_type' in context:
            meeting_type = context['meeting_type']
            if meeting_type and meeting_type.lower() not in enhanced_text.lower():
                enhanced_text = f"{meeting_type} - {enhanced_text}"
                changes.append("Added meeting type context")
        
        return enhanced_text, changes
    
    async def _enhance_action_item_text(self, text: str, context: Optional[Dict[str, Any]]) -> Tuple[str, List[str]]:
        """Enhance action item text"""
        enhanced_text = text
        changes = []
        
        # Ensure action items start with action verbs
        action_verbs = ['完成', '執行', '準備', '檢查', '確認', '聯絡', '更新', '提供', '安排', '討論']
        
        if not any(enhanced_text.strip().startswith(verb) for verb in action_verbs):
            enhanced_text = f"需要 {enhanced_text}"
            changes.append("Added action verb prefix")
        
        return enhanced_text, changes
    
    async def _enhance_decision_text(self, text: str, context: Optional[Dict[str, Any]]) -> Tuple[str, List[str]]:
        """Enhance decision text"""
        enhanced_text = text
        changes = []
        
        # Ensure decisions are clearly stated
        decision_indicators = ['決定', '同意', '通過', '批准', '確認', '拒絕']
        
        if not any(indicator in enhanced_text for indicator in decision_indicators):
            enhanced_text = f"會議決定：{enhanced_text}"
            changes.append("Added decision indicator")
        
        return enhanced_text, changes
    
    async def _improve_text_quality(self, text: str) -> Tuple[str, List[str]]:
        """General text quality improvements"""
        improved_text = text
        changes = []
        
        # Remove excessive whitespace
        if re.search(r'\s{3,}', improved_text):
            improved_text = re.sub(r'\s{3,}', ' ', improved_text)
            changes.append("Removed excessive whitespace")
        
        # Ensure proper sentence ending
        if improved_text and not improved_text.rstrip().endswith(('.', '!', '?', '。', '！', '？')):
            improved_text = improved_text.rstrip() + '。'
            changes.append("Added sentence ending punctuation")
        
        # Capitalize first letter (for mixed language content)
        if improved_text and improved_text[0].islower():
            improved_text = improved_text[0].upper() + improved_text[1:]
            changes.append("Capitalized first letter")
        
        return improved_text, changes
    
    async def _deduplicate_list(self, items: List[str], similarity_threshold: float) -> List[str]:
        """Deduplicate list items based on similarity"""
        if not items:
            return items
        
        unique_items = []
        
        for item in items:
            if not item or not item.strip():
                continue
            
            item_clean = item.strip()
            is_duplicate = False
            
            for existing_item in unique_items:
                similarity = difflib.SequenceMatcher(None, item_clean.lower(), existing_item.lower()).ratio()
                if similarity >= similarity_threshold:
                    is_duplicate = True
                    break
            
            if not is_duplicate:
                unique_items.append(item_clean)
        
        return unique_items
    
    async def _extract_missing_field(
        self,
        field_name: str,
        original_text: Optional[str],
        existing_data: Dict[str, Any],
        context: Optional[Dict[str, Any]]
    ) -> Optional[str]:
        """Extract missing field from original text"""
        if not original_text:
            return None
        
        # Simple extraction patterns
        if field_name == 'MEETING_TITLE':
            # Look for meeting title patterns
            title_patterns = [
                r'會議主題[：:]\s*([^\n]+)',
                r'主題[：:]\s*([^\n]+)',
                r'會議[：:]\s*([^\n]+)',
                r'^([^\n]{10,50}會議)'
            ]
            
            for pattern in title_patterns:
                match = re.search(pattern, original_text)
                if match:
                    return match.group(1).strip()
        
        elif field_name == 'MEETING_DATE':
            # Look for date patterns
            date_patterns = [
                r'(\d{4}[-/年]\d{1,2}[-/月]\d{1,2}日?)',
                r'(\d{1,2}[-/月]\d{1,2}[-/日])',
                r'日期[：:]\s*([^\n]+)'
            ]
            
            for pattern in date_patterns:
                match = re.search(pattern, original_text)
                if match:
                    return match.group(1).strip()
        
        elif field_name == 'ATTENDEES_LIST':
            # Look for attendee patterns
            attendee_patterns = [
                r'出席[者人員][：:]\s*([^\n]+)',
                r'與會人員[：:]\s*([^\n]+)',
                r'參與者[：:]\s*([^\n]+)'
            ]
            
            for pattern in attendee_patterns:
                match = re.search(pattern, original_text)
                if match:
                    attendee_text = match.group(1).strip()
                    # Split by common separators
                    attendees = [name.strip() for name in re.split(r'[、，,；;]', attendee_text) if name.strip()]
                    return attendees if len(attendees) > 1 else attendee_text
        
        return None
    
    async def _expand_short_content(
        self,
        field_name: str,
        short_content: str,
        original_text: Optional[str]
    ) -> Optional[str]:
        """Expand short content using context from original text"""
        if not original_text or len(short_content.strip()) > 20:
            return None
        
        # Look for expanded context around the short content
        content_lower = short_content.lower()
        original_lower = original_text.lower()
        
        # Find the position of short content in original text
        pos = original_lower.find(content_lower)
        if pos >= 0:
            # Extract surrounding context
            start = max(0, pos - 50)
            end = min(len(original_text), pos + len(short_content) + 50)
            context = original_text[start:end].strip()
            
            # If context is significantly longer, use it
            if len(context) > len(short_content) * 2:
                return context
        
        return None
    
    async def _standardize_date_format(self, date_str: str) -> str:
        """Standardize date format"""
        # Simple date standardization
        date_patterns = [
            (r'(\d{4})[年/-](\d{1,2})[月/-](\d{1,2})日?', r'\1-\2-\3'),
            (r'(\d{1,2})[月/](\d{1,2})[日/]', r'2024-\1-\2'),  # Assume current year
        ]
        
        standardized = date_str
        for pattern, replacement in date_patterns:
            standardized = re.sub(pattern, replacement, standardized)
        
        return standardized
    
    async def _standardize_name_format(self, name: str) -> str:
        """Standardize name format"""
        if not name or not name.strip():
            return name
        
        # Remove titles and clean up
        name = name.strip()
        titles_to_remove = ['先生', '女士', '小姐', '經理', '主任', '總監', '董事']
        
        for title in titles_to_remove:
            name = name.replace(title, '').strip()
        
        return name
    
    async def _calculate_data_quality(self, data: Dict[str, Any]) -> float:
        """Calculate overall data quality score"""
        quality_factors = []
        
        # Field completeness
        total_fields = len(self._get_default_meeting_schema())
        present_fields = sum(1 for field in self._get_default_meeting_schema().keys() if data.get(field))
        completeness = present_fields / total_fields
        quality_factors.append(completeness)
        
        # Content quality for text fields
        text_scores = []
        for field_name, field_value in data.items():
            if isinstance(field_value, str) and field_value.strip():
                # Simple quality score based on length and structure
                length_score = min(1.0, len(field_value.strip()) / 50)  # Optimal around 50 chars
                text_scores.append(length_score)
        
        if text_scores:
            avg_text_quality = sum(text_scores) / len(text_scores)
            quality_factors.append(avg_text_quality)
        
        return sum(quality_factors) / len(quality_factors) if quality_factors else 0.0
    
    async def _calculate_text_improvement(self, original: str, enhanced: str) -> float:
        """Calculate text improvement score"""
        if original == enhanced:
            return 0.0
        
        # Simple improvement metrics
        length_improvement = (len(enhanced) - len(original)) / max(len(original), 1)
        length_improvement = max(0, min(length_improvement, 0.5))  # Cap at 0.5
        
        # Structure improvement (basic checks)
        structure_improvement = 0.0
        if enhanced.endswith(('.', '。', '!', '！', '?', '？')) and not original.endswith(('.', '。', '!', '！', '?', '？')):
            structure_improvement += 0.2
        
        if enhanced[0].isupper() and not original[0].isupper():
            structure_improvement += 0.1
        
        return length_improvement + structure_improvement
    
    def _get_enhancement_type(self, field_name: str) -> str:
        """Get enhancement type for field"""
        if 'ACTION' in field_name.upper():
            return 'action_item'
        elif 'DECISION' in field_name.upper():
            return 'decision'
        elif 'MEETING' in field_name.upper():
            return 'meeting'
        else:
            return 'general'
    
    def _get_default_meeting_schema(self) -> Dict[str, Dict[str, Any]]:
        """Get default meeting data schema"""
        return {
            'MEETING_TITLE': {'type': 'string', 'default': ''},
            'MEETING_DATE': {'type': 'string', 'default': ''},
            'ATTENDEES_LIST': {'type': 'list', 'default': []},
            'AGENDA_ITEMS': {'type': 'list', 'default': []},
            'KEY_DECISIONS': {'type': 'list', 'default': []},
            'ACTION_ITEMS': {'type': 'list', 'default': []},
            'NEXT_MEETING': {'type': 'string', 'default': ''},
            'MEETING_SUMMARY': {'type': 'string', 'default': ''}
        }
    
    async def _analyze_data_stats(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze data statistics"""
        stats = {
            'total_fields': len(data),
            'populated_fields': sum(1 for v in data.values() if v),
            'empty_fields': sum(1 for v in data.values() if not v),
            'text_fields': sum(1 for v in data.values() if isinstance(v, str) and v.strip()),
            'list_fields': sum(1 for v in data.values() if isinstance(v, list) and v),
            'total_text_length': sum(len(str(v)) for v in data.values() if v),
            'average_text_length': 0
        }
        
        text_lengths = [len(str(v)) for v in data.values() if isinstance(v, str) and v.strip()]
        if text_lengths:
            stats['average_text_length'] = sum(text_lengths) / len(text_lengths)
        
        return stats
    
    async def _deep_copy_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Create deep copy of data"""
        import copy
        return copy.deepcopy(data)
    
    async def _post_process_cleanup(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Final cleanup of optimized data"""
        cleaned_data = {}
        
        for field_name, field_value in data.items():
            if isinstance(field_value, str):
                # Final text cleanup
                cleaned_value = field_value.strip()
                if cleaned_value:
                    cleaned_data[field_name] = cleaned_value
            
            elif isinstance(field_value, list):
                # Final list cleanup
                cleaned_list = [item for item in field_value if item and str(item).strip()]
                if cleaned_list:
                    cleaned_data[field_name] = cleaned_list
            
            else:
                if field_value:
                    cleaned_data[field_name] = field_value
        
        return cleaned_data