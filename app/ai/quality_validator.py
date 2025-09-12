"""
AI Processing Quality Validator (A4 - AI Processing Layer)
Quality validation and verification system for AI processing results
Implements SESE principle - Simple, Effective, Systematic, Exhaustive validation
"""

import logging
import re
import json
from typing import Dict, List, Optional, Any, Tuple, Union
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta
from enum import Enum
import statistics
from collections import defaultdict

logger = logging.getLogger(__name__)


class ValidationLevel(Enum):
    """Validation strictness levels"""
    BASIC = "basic"
    STANDARD = "standard"
    STRICT = "strict"
    COMPREHENSIVE = "comprehensive"


class ValidationCategory(Enum):
    """Validation categories"""
    CONTENT_QUALITY = "content_quality"
    STRUCTURE_COMPLIANCE = "structure_compliance"
    DATA_COMPLETENESS = "data_completeness"
    CONSISTENCY = "consistency"
    ACCURACY = "accuracy"
    FORMAT_VALIDATION = "format_validation"


class QualityMetric(Enum):
    """Quality metrics"""
    COMPLETENESS = "completeness"
    ACCURACY = "accuracy"
    CONSISTENCY = "consistency"
    CLARITY = "clarity"
    RELEVANCE = "relevance"
    STRUCTURE = "structure"


@dataclass
class ValidationRule:
    """Individual validation rule"""
    rule_id: str
    name: str
    description: str
    category: ValidationCategory
    metric: QualityMetric
    weight: float = 1.0
    enabled: bool = True
    min_threshold: float = 0.0
    max_threshold: float = 1.0
    required_fields: List[str] = field(default_factory=list)
    validation_pattern: Optional[str] = None
    custom_validator: Optional[str] = None


@dataclass
class ValidationResult:
    """Validation result for a single rule"""
    rule_id: str
    passed: bool
    score: float
    message: str
    details: Dict[str, Any] = field(default_factory=dict)
    suggestions: List[str] = field(default_factory=list)


@dataclass
class QualityReport:
    """Complete quality validation report"""
    process_id: str
    validation_timestamp: datetime
    validation_level: ValidationLevel
    overall_score: float
    overall_passed: bool
    category_scores: Dict[ValidationCategory, float] = field(default_factory=dict)
    metric_scores: Dict[QualityMetric, float] = field(default_factory=dict)
    validation_results: List[ValidationResult] = field(default_factory=list)
    failed_validations: List[ValidationResult] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    recommendations: List[str] = field(default_factory=list)
    processing_time_ms: float = 0.0
    input_stats: Dict[str, Any] = field(default_factory=dict)
    output_stats: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ContentAnalysis:
    """Content analysis results"""
    word_count: int = 0
    sentence_count: int = 0
    paragraph_count: int = 0
    unique_words: int = 0
    readability_score: float = 0.0
    sentiment_score: float = 0.0
    key_topics: List[str] = field(default_factory=list)
    named_entities: List[str] = field(default_factory=list)
    language_confidence: float = 0.0
    detected_language: str = "zh-TW"


class QualityValidator:
    """
    AI Processing Quality Validator
    Comprehensive validation system for AI processing results
    """
    
    def __init__(self, validation_level: ValidationLevel = ValidationLevel.STANDARD):
        """Initialize quality validator"""
        self.validation_level = validation_level
        self.validation_rules: Dict[str, ValidationRule] = {}
        
        # Quality thresholds based on validation level
        self.quality_thresholds = {
            ValidationLevel.BASIC: 0.6,
            ValidationLevel.STANDARD: 0.75,
            ValidationLevel.STRICT: 0.85,
            ValidationLevel.COMPREHENSIVE: 0.9
        }
        
        # Required fields for meeting minutes
        self.required_meeting_fields = [
            'MEETING_TITLE', 'MEETING_DATE', 'ATTENDEES_LIST',
            'AGENDA_ITEMS', 'KEY_DECISIONS', 'ACTION_ITEMS'
        ]
        
        # Initialize validation rules
        self._initialize_validation_rules()
        
        logger.info(f"🔍 Quality Validator initialized - Level: {validation_level.value}")
    
    async def validate_processing_result(
        self,
        process_id: str,
        input_text: str,
        extracted_data: Dict[str, Any],
        additional_context: Optional[Dict[str, Any]] = None
    ) -> QualityReport:
        """
        Validate AI processing result comprehensively
        
        Args:
            process_id: Processing operation ID
            input_text: Original input text
            extracted_data: AI-extracted structured data
            additional_context: Additional context for validation
            
        Returns:
            QualityReport with validation results
        """
        start_time = datetime.utcnow()
        
        try:
            # Analyze input and output
            input_analysis = await self._analyze_content(input_text)
            output_analysis = await self._analyze_extracted_data(extracted_data)
            
            # Initialize report
            report = QualityReport(
                process_id=process_id,
                validation_timestamp=start_time,
                validation_level=self.validation_level,
                overall_score=0.0,
                overall_passed=False,
                input_stats=asdict(input_analysis),
                output_stats=output_analysis
            )
            
            # Run all validation rules
            validation_results = []
            category_scores = defaultdict(list)
            metric_scores = defaultdict(list)
            
            for rule in self.validation_rules.values():
                if rule.enabled:
                    result = await self._execute_validation_rule(
                        rule, input_text, extracted_data, input_analysis, additional_context
                    )
                    
                    validation_results.append(result)
                    category_scores[rule.category].append(result.score * rule.weight)
                    metric_scores[rule.metric].append(result.score * rule.weight)
                    
                    if not result.passed:
                        report.failed_validations.append(result)
            
            # Calculate scores
            report.validation_results = validation_results
            report.category_scores = {
                category: sum(scores) / len(scores) if scores else 0.0
                for category, scores in category_scores.items()
            }
            report.metric_scores = {
                metric: sum(scores) / len(scores) if scores else 0.0
                for metric, scores in metric_scores.items()
            }
            
            # Calculate overall score
            all_scores = [result.score for result in validation_results]
            report.overall_score = sum(all_scores) / len(all_scores) if all_scores else 0.0
            
            # Determine pass/fail
            quality_threshold = self.quality_thresholds[self.validation_level]
            report.overall_passed = (
                report.overall_score >= quality_threshold and
                len(report.failed_validations) == 0
            )
            
            # Generate recommendations
            report.recommendations = await self._generate_recommendations(report)
            report.warnings = await self._generate_warnings(report, input_analysis)
            
            # Calculate processing time
            end_time = datetime.utcnow()
            report.processing_time_ms = (end_time - start_time).total_seconds() * 1000
            
            logger.info(f"✅ Quality validation completed: {process_id} - Score: {report.overall_score:.2f}")
            return report
            
        except Exception as e:
            logger.error(f"❌ Quality validation failed for {process_id}: {e}")
            
            # Return failed report
            return QualityReport(
                process_id=process_id,
                validation_timestamp=start_time,
                validation_level=self.validation_level,
                overall_score=0.0,
                overall_passed=False,
                warnings=[f"Validation failed: {str(e)}"]
            )
    
    async def validate_field_quality(
        self,
        field_name: str,
        field_value: Any,
        expected_type: Optional[str] = None,
        validation_rules: Optional[List[str]] = None
    ) -> ValidationResult:
        """
        Validate individual field quality
        
        Args:
            field_name: Name of the field
            field_value: Value to validate
            expected_type: Expected data type
            validation_rules: Additional validation rules
            
        Returns:
            ValidationResult for the field
        """
        try:
            score = 1.0
            passed = True
            message = f"Field '{field_name}' validation passed"
            details = {}
            suggestions = []
            
            # Basic presence check
            if field_value is None or (isinstance(field_value, str) and not field_value.strip()):
                score = 0.0
                passed = False
                message = f"Field '{field_name}' is empty or null"
                suggestions.append(f"Ensure '{field_name}' has a valid value")
                
                return ValidationResult(
                    rule_id=f"field_{field_name}_presence",
                    passed=passed,
                    score=score,
                    message=message,
                    details=details,
                    suggestions=suggestions
                )
            
            # Type validation
            if expected_type:
                type_valid = await self._validate_field_type(field_value, expected_type)
                if not type_valid:
                    score *= 0.8
                    suggestions.append(f"'{field_name}' should be of type {expected_type}")
            
            # Content quality validation
            if isinstance(field_value, str):
                content_score = await self._validate_text_quality(field_value)
                score *= content_score
                details['content_quality_score'] = content_score
                
                if content_score < 0.7:
                    suggestions.append(f"Improve content quality for '{field_name}'")
            
            # List validation
            elif isinstance(field_value, list):
                list_score = await self._validate_list_quality(field_value)
                score *= list_score
                details['list_quality_score'] = list_score
                details['item_count'] = len(field_value)
                
                if list_score < 0.7:
                    suggestions.append(f"Improve list completeness for '{field_name}'")
            
            # Custom validation rules
            if validation_rules:
                for rule in validation_rules:
                    rule_score = await self._apply_custom_validation(field_value, rule)
                    score *= rule_score
                    details[f'custom_rule_{rule}'] = rule_score
            
            # Final assessment
            passed = score >= 0.6  # Minimum threshold for field validation
            
            return ValidationResult(
                rule_id=f"field_{field_name}_quality",
                passed=passed,
                score=score,
                message=message,
                details=details,
                suggestions=suggestions
            )
            
        except Exception as e:
            return ValidationResult(
                rule_id=f"field_{field_name}_error",
                passed=False,
                score=0.0,
                message=f"Field validation error: {str(e)}",
                suggestions=[f"Check field '{field_name}' for validation issues"]
            )
    
    async def calculate_confidence_score(
        self,
        extracted_data: Dict[str, Any],
        processing_metadata: Optional[Dict[str, Any]] = None
    ) -> float:
        """
        Calculate confidence score for extracted data
        
        Args:
            extracted_data: Extracted data to evaluate
            processing_metadata: Additional processing information
            
        Returns:
            Confidence score (0.0 to 1.0)
        """
        try:
            confidence_factors = []
            
            # Data completeness factor
            required_fields = self.required_meeting_fields
            present_fields = [field for field in required_fields if extracted_data.get(field)]
            completeness_score = len(present_fields) / len(required_fields)
            confidence_factors.append(completeness_score * 0.3)  # 30% weight
            
            # Content quality factor
            total_quality_score = 0.0
            quality_count = 0
            
            for field_name, field_value in extracted_data.items():
                if isinstance(field_value, str) and field_value.strip():
                    quality_score = await self._validate_text_quality(field_value)
                    total_quality_score += quality_score
                    quality_count += 1
            
            content_quality = total_quality_score / quality_count if quality_count > 0 else 0.0
            confidence_factors.append(content_quality * 0.4)  # 40% weight
            
            # Structure consistency factor
            structure_score = await self._validate_data_structure(extracted_data)
            confidence_factors.append(structure_score * 0.2)  # 20% weight
            
            # Processing metadata factor
            if processing_metadata:
                metadata_score = min(1.0, processing_metadata.get('processing_confidence', 0.5))
                confidence_factors.append(metadata_score * 0.1)  # 10% weight
            else:
                confidence_factors.append(0.05)  # Default low confidence
            
            # Calculate final confidence score
            final_confidence = sum(confidence_factors)
            
            return min(1.0, max(0.0, final_confidence))
            
        except Exception as e:
            logger.error(f"❌ Failed to calculate confidence score: {e}")
            return 0.0
    
    def get_validation_summary(self, report: QualityReport) -> Dict[str, Any]:
        """Get validation summary"""
        return {
            'process_id': report.process_id,
            'overall_passed': report.overall_passed,
            'overall_score': round(report.overall_score, 3),
            'validation_level': report.validation_level.value,
            'total_validations': len(report.validation_results),
            'failed_validations': len(report.failed_validations),
            'category_scores': {
                category.value: round(score, 3)
                for category, score in report.category_scores.items()
            },
            'metric_scores': {
                metric.value: round(score, 3)
                for metric, score in report.metric_scores.items()
            },
            'processing_time_ms': round(report.processing_time_ms, 2),
            'recommendations_count': len(report.recommendations),
            'warnings_count': len(report.warnings)
        }
    
    # Private methods
    
    def _initialize_validation_rules(self):
        """Initialize default validation rules"""
        rules = [
            ValidationRule(
                rule_id="content_completeness",
                name="Content Completeness Check",
                description="Validates that all required fields are present and populated",
                category=ValidationCategory.DATA_COMPLETENESS,
                metric=QualityMetric.COMPLETENESS,
                weight=1.5,
                required_fields=self.required_meeting_fields
            ),
            ValidationRule(
                rule_id="text_quality",
                name="Text Quality Assessment",
                description="Evaluates the quality and clarity of extracted text",
                category=ValidationCategory.CONTENT_QUALITY,
                metric=QualityMetric.CLARITY,
                weight=1.2
            ),
            ValidationRule(
                rule_id="structure_compliance",
                name="Structure Compliance Check",
                description="Validates data structure matches expected format",
                category=ValidationCategory.STRUCTURE_COMPLIANCE,
                metric=QualityMetric.STRUCTURE,
                weight=1.0
            ),
            ValidationRule(
                rule_id="data_consistency",
                name="Data Consistency Validation",
                description="Checks for internal consistency in extracted data",
                category=ValidationCategory.CONSISTENCY,
                metric=QualityMetric.CONSISTENCY,
                weight=1.1
            ),
            ValidationRule(
                rule_id="format_validation",
                name="Format Validation",
                description="Validates data formats (dates, names, etc.)",
                category=ValidationCategory.FORMAT_VALIDATION,
                metric=QualityMetric.ACCURACY,
                weight=0.9
            ),
            ValidationRule(
                rule_id="relevance_check",
                name="Content Relevance Check",
                description="Evaluates relevance of extracted content to meeting context",
                category=ValidationCategory.CONTENT_QUALITY,
                metric=QualityMetric.RELEVANCE,
                weight=1.0
            )
        ]
        
        for rule in rules:
            self.validation_rules[rule.rule_id] = rule
    
    async def _execute_validation_rule(
        self,
        rule: ValidationRule,
        input_text: str,
        extracted_data: Dict[str, Any],
        input_analysis: ContentAnalysis,
        additional_context: Optional[Dict[str, Any]]
    ) -> ValidationResult:
        """Execute individual validation rule"""
        try:
            if rule.rule_id == "content_completeness":
                return await self._validate_completeness(rule, extracted_data)
            elif rule.rule_id == "text_quality":
                return await self._validate_text_quality_rule(rule, extracted_data)
            elif rule.rule_id == "structure_compliance":
                return await self._validate_structure_compliance(rule, extracted_data)
            elif rule.rule_id == "data_consistency":
                return await self._validate_data_consistency(rule, input_text, extracted_data)
            elif rule.rule_id == "format_validation":
                return await self._validate_formats(rule, extracted_data)
            elif rule.rule_id == "relevance_check":
                return await self._validate_relevance(rule, input_text, extracted_data, input_analysis)
            else:
                # Default validation
                return ValidationResult(
                    rule_id=rule.rule_id,
                    passed=True,
                    score=0.5,
                    message=f"Default validation for rule '{rule.rule_id}'"
                )
                
        except Exception as e:
            return ValidationResult(
                rule_id=rule.rule_id,
                passed=False,
                score=0.0,
                message=f"Validation rule failed: {str(e)}",
                suggestions=[f"Check rule '{rule.rule_id}' implementation"]
            )
    
    async def _validate_completeness(self, rule: ValidationRule, extracted_data: Dict[str, Any]) -> ValidationResult:
        """Validate data completeness"""
        required_fields = rule.required_fields
        present_fields = []
        missing_fields = []
        
        for field in required_fields:
            value = extracted_data.get(field)
            if value and (not isinstance(value, str) or value.strip()):
                present_fields.append(field)
            else:
                missing_fields.append(field)
        
        score = len(present_fields) / len(required_fields) if required_fields else 1.0
        passed = score >= rule.min_threshold
        
        message = f"Completeness: {len(present_fields)}/{len(required_fields)} required fields present"
        suggestions = [f"Add content for missing field: '{field}'" for field in missing_fields]
        
        return ValidationResult(
            rule_id=rule.rule_id,
            passed=passed,
            score=score,
            message=message,
            details={
                'present_fields': present_fields,
                'missing_fields': missing_fields,
                'total_required': len(required_fields)
            },
            suggestions=suggestions
        )
    
    async def _validate_text_quality_rule(self, rule: ValidationRule, extracted_data: Dict[str, Any]) -> ValidationResult:
        """Validate text quality across all fields"""
        quality_scores = []
        field_details = {}
        
        for field_name, field_value in extracted_data.items():
            if isinstance(field_value, str) and field_value.strip():
                quality_score = await self._validate_text_quality(field_value)
                quality_scores.append(quality_score)
                field_details[field_name] = quality_score
        
        overall_score = sum(quality_scores) / len(quality_scores) if quality_scores else 0.0
        passed = overall_score >= rule.min_threshold
        
        suggestions = []
        for field_name, score in field_details.items():
            if score < 0.7:
                suggestions.append(f"Improve text quality for '{field_name}' (score: {score:.2f})")
        
        return ValidationResult(
            rule_id=rule.rule_id,
            passed=passed,
            score=overall_score,
            message=f"Text quality score: {overall_score:.2f}",
            details=field_details,
            suggestions=suggestions
        )
    
    async def _validate_structure_compliance(self, rule: ValidationRule, extracted_data: Dict[str, Any]) -> ValidationResult:
        """Validate data structure compliance"""
        structure_score = await self._validate_data_structure(extracted_data)
        passed = structure_score >= rule.min_threshold
        
        return ValidationResult(
            rule_id=rule.rule_id,
            passed=passed,
            score=structure_score,
            message=f"Structure compliance score: {structure_score:.2f}",
            details={'structure_score': structure_score}
        )
    
    async def _validate_data_consistency(self, rule: ValidationRule, input_text: str, extracted_data: Dict[str, Any]) -> ValidationResult:
        """Validate data consistency"""
        consistency_checks = []
        
        # Date consistency check
        meeting_date = extracted_data.get('MEETING_DATE', '')
        if meeting_date and isinstance(meeting_date, str):
            date_valid = await self._validate_date_format(meeting_date)
            consistency_checks.append(date_valid)
        
        # Attendees vs content consistency
        attendees = extracted_data.get('ATTENDEES_LIST', [])
        if attendees:
            attendee_consistency = await self._validate_attendee_consistency(attendees, input_text)
            consistency_checks.append(attendee_consistency)
        
        # Action items vs decisions consistency
        actions = extracted_data.get('ACTION_ITEMS', [])
        decisions = extracted_data.get('KEY_DECISIONS', [])
        if actions and decisions:
            action_consistency = await self._validate_action_decision_consistency(actions, decisions)
            consistency_checks.append(action_consistency)
        
        overall_score = sum(consistency_checks) / len(consistency_checks) if consistency_checks else 1.0
        passed = overall_score >= rule.min_threshold
        
        return ValidationResult(
            rule_id=rule.rule_id,
            passed=passed,
            score=overall_score,
            message=f"Data consistency score: {overall_score:.2f}",
            details={'consistency_checks': len(consistency_checks)}
        )
    
    async def _validate_formats(self, rule: ValidationRule, extracted_data: Dict[str, Any]) -> ValidationResult:
        """Validate data formats"""
        format_scores = []
        format_details = {}
        
        # Date format validation
        meeting_date = extracted_data.get('MEETING_DATE', '')
        if meeting_date:
            date_score = 1.0 if await self._validate_date_format(meeting_date) else 0.0
            format_scores.append(date_score)
            format_details['date_format'] = date_score
        
        # List format validation
        for field_name in ['ATTENDEES_LIST', 'AGENDA_ITEMS', 'ACTION_ITEMS']:
            field_value = extracted_data.get(field_name, [])
            if field_value:
                list_score = 1.0 if isinstance(field_value, list) else 0.0
                format_scores.append(list_score)
                format_details[f'{field_name}_format'] = list_score
        
        overall_score = sum(format_scores) / len(format_scores) if format_scores else 1.0
        passed = overall_score >= rule.min_threshold
        
        return ValidationResult(
            rule_id=rule.rule_id,
            passed=passed,
            score=overall_score,
            message=f"Format validation score: {overall_score:.2f}",
            details=format_details
        )
    
    async def _validate_relevance(
        self,
        rule: ValidationRule,
        input_text: str,
        extracted_data: Dict[str, Any],
        input_analysis: ContentAnalysis
    ) -> ValidationResult:
        """Validate content relevance"""
        relevance_score = 0.8  # Base relevance score
        
        # Check if key topics from input are reflected in extracted data
        input_topics = input_analysis.key_topics
        if input_topics:
            topic_matches = 0
            for topic in input_topics:
                for field_value in extracted_data.values():
                    if isinstance(field_value, str) and topic.lower() in field_value.lower():
                        topic_matches += 1
                        break
            
            topic_relevance = topic_matches / len(input_topics)
            relevance_score *= topic_relevance
        
        passed = relevance_score >= rule.min_threshold
        
        return ValidationResult(
            rule_id=rule.rule_id,
            passed=passed,
            score=relevance_score,
            message=f"Content relevance score: {relevance_score:.2f}",
            details={'topic_relevance': relevance_score}
        )
    
    async def _analyze_content(self, text: str) -> ContentAnalysis:
        """Analyze input content"""
        analysis = ContentAnalysis()
        
        if not text or not text.strip():
            return analysis
        
        # Basic text statistics
        sentences = re.split(r'[.!?]+', text)
        paragraphs = text.split('\n\n')
        words = text.split()
        
        analysis.word_count = len(words)
        analysis.sentence_count = len([s for s in sentences if s.strip()])
        analysis.paragraph_count = len([p for p in paragraphs if p.strip()])
        analysis.unique_words = len(set(word.lower() for word in words))
        
        # Simple readability score (based on word/sentence ratio)
        if analysis.sentence_count > 0:
            avg_words_per_sentence = analysis.word_count / analysis.sentence_count
            analysis.readability_score = min(1.0, max(0.0, (20 - avg_words_per_sentence) / 20))
        
        # Extract potential topics (simple keyword extraction)
        word_freq = defaultdict(int)
        for word in words:
            if len(word) > 4 and word.isalpha():
                word_freq[word.lower()] += 1
        
        # Get top topics
        sorted_words = sorted(word_freq.items(), key=lambda x: x[1], reverse=True)
        analysis.key_topics = [word for word, freq in sorted_words[:5]]
        
        analysis.language_confidence = 0.9  # Default for Chinese content
        analysis.detected_language = "zh-TW"
        
        return analysis
    
    async def _analyze_extracted_data(self, extracted_data: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze extracted data"""
        stats = {
            'total_fields': len(extracted_data),
            'populated_fields': sum(1 for v in extracted_data.values() if v),
            'empty_fields': sum(1 for v in extracted_data.values() if not v),
            'text_fields': sum(1 for v in extracted_data.values() if isinstance(v, str)),
            'list_fields': sum(1 for v in extracted_data.values() if isinstance(v, list)),
            'total_text_length': sum(len(str(v)) for v in extracted_data.values() if v)
        }
        
        return stats
    
    async def _validate_text_quality(self, text: str) -> float:
        """Validate quality of a text field"""
        if not text or not text.strip():
            return 0.0
        
        quality_factors = []
        
        # Length factor (not too short, not too long)
        length = len(text.strip())
        if length < 5:
            quality_factors.append(0.2)
        elif length > 1000:
            quality_factors.append(0.8)
        else:
            quality_factors.append(1.0)
        
        # Content diversity (unique words)
        words = text.split()
        if len(words) > 0:
            unique_ratio = len(set(words)) / len(words)
            quality_factors.append(unique_ratio)
        
        # Structure factor (proper punctuation, capitalization)
        structure_score = 0.5
        if text[0].isupper():  # Starts with capital
            structure_score += 0.25
        if text.endswith(('.', '!', '?')):  # Ends with punctuation
            structure_score += 0.25
        quality_factors.append(structure_score)
        
        return sum(quality_factors) / len(quality_factors)
    
    async def _validate_list_quality(self, items: List[Any]) -> float:
        """Validate quality of a list field"""
        if not items:
            return 0.0
        
        # Basic presence score
        presence_score = min(1.0, len(items) / 3)  # Optimal around 3 items
        
        # Content quality for text items
        if all(isinstance(item, str) for item in items):
            text_scores = [await self._validate_text_quality(item) for item in items]
            content_score = sum(text_scores) / len(text_scores) if text_scores else 0.0
            return (presence_score + content_score) / 2
        
        return presence_score
    
    async def _validate_field_type(self, value: Any, expected_type: str) -> bool:
        """Validate field type"""
        type_mapping = {
            'string': str,
            'list': list,
            'dict': dict,
            'int': int,
            'float': float,
            'bool': bool
        }
        
        expected_python_type = type_mapping.get(expected_type.lower())
        if expected_python_type:
            return isinstance(value, expected_python_type)
        
        return True  # Unknown type, assume valid
    
    async def _validate_data_structure(self, extracted_data: Dict[str, Any]) -> float:
        """Validate overall data structure"""
        structure_checks = []
        
        # Check required field types
        type_checks = {
            'MEETING_TITLE': str,
            'MEETING_DATE': str,
            'ATTENDEES_LIST': list,
            'AGENDA_ITEMS': list,
            'KEY_DECISIONS': list,
            'ACTION_ITEMS': list
        }
        
        for field_name, expected_type in type_checks.items():
            value = extracted_data.get(field_name)
            if value is not None:
                type_valid = isinstance(value, expected_type)
                structure_checks.append(1.0 if type_valid else 0.0)
        
        return sum(structure_checks) / len(structure_checks) if structure_checks else 1.0
    
    async def _validate_date_format(self, date_str: str) -> bool:
        """Validate date format"""
        import re
        from datetime import datetime
        
        # Common date patterns
        date_patterns = [
            r'\d{4}-\d{2}-\d{2}',  # YYYY-MM-DD
            r'\d{2}/\d{2}/\d{4}',  # MM/DD/YYYY
            r'\d{4}/\d{2}/\d{2}',  # YYYY/MM/DD
            r'\d{1,2}月\d{1,2}日',  # Chinese format
        ]
        
        for pattern in date_patterns:
            if re.search(pattern, date_str):
                return True
        
        return False
    
    async def _validate_attendee_consistency(self, attendees: List[str], input_text: str) -> float:
        """Validate attendee consistency with input text"""
        if not attendees:
            return 0.0
        
        found_count = 0
        for attendee in attendees:
            if isinstance(attendee, str) and attendee.strip():
                # Check if attendee name appears in input text
                if attendee.lower() in input_text.lower():
                    found_count += 1
        
        return found_count / len(attendees)
    
    async def _validate_action_decision_consistency(self, actions: List[str], decisions: List[str]) -> float:
        """Validate consistency between actions and decisions"""
        # Simple check: action items should be related to decisions
        if not actions or not decisions:
            return 1.0  # No conflict if one is empty
        
        # For now, just check that both exist and have reasonable content
        action_quality = sum(1 for action in actions if isinstance(action, str) and len(action.strip()) > 10)
        decision_quality = sum(1 for decision in decisions if isinstance(decision, str) and len(decision.strip()) > 10)
        
        action_score = action_quality / len(actions) if actions else 0
        decision_score = decision_quality / len(decisions) if decisions else 0
        
        return (action_score + decision_score) / 2
    
    async def _apply_custom_validation(self, value: Any, rule: str) -> float:
        """Apply custom validation rule"""
        # Implement custom validation rules as needed
        # For now, return default score
        return 0.8
    
    async def _generate_recommendations(self, report: QualityReport) -> List[str]:
        """Generate quality improvement recommendations"""
        recommendations = []
        
        # Based on failed validations
        for failed_validation in report.failed_validations:
            recommendations.extend(failed_validation.suggestions)
        
        # Based on low category scores
        for category, score in report.category_scores.items():
            if score < 0.7:
                if category == ValidationCategory.DATA_COMPLETENESS:
                    recommendations.append("Add missing required fields to improve completeness")
                elif category == ValidationCategory.CONTENT_QUALITY:
                    recommendations.append("Enhance content quality with more detailed and clear information")
                elif category == ValidationCategory.STRUCTURE_COMPLIANCE:
                    recommendations.append("Ensure data follows the expected structure format")
                elif category == ValidationCategory.CONSISTENCY:
                    recommendations.append("Review data for internal consistency issues")
        
        # Remove duplicates while preserving order
        seen = set()
        unique_recommendations = []
        for rec in recommendations:
            if rec not in seen:
                seen.add(rec)
                unique_recommendations.append(rec)
        
        return unique_recommendations[:10]  # Limit to top 10 recommendations
    
    async def _generate_warnings(self, report: QualityReport, input_analysis: ContentAnalysis) -> List[str]:
        """Generate quality warnings"""
        warnings = []
        
        # Low overall score warning
        if report.overall_score < 0.6:
            warnings.append("Overall quality score is below acceptable threshold")
        
        # Input quality warnings
        if input_analysis.word_count < 50:
            warnings.append("Input text appears to be very short for meeting minutes")
        
        if input_analysis.readability_score < 0.3:
            warnings.append("Input text has poor readability score")
        
        # Processing warnings
        if report.processing_time_ms > 10000:  # 10 seconds
            warnings.append("Quality validation took longer than expected")
        
        return warnings