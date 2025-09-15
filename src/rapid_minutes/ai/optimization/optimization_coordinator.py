"""
Optimization Coordinator
Orchestrates the optimization process using specialized components
Replaces the monolithic ResultOptimizer class
"""

import logging
from typing import Dict, List, Any, Optional
from datetime import datetime

from .optimization_types import (
    OptimizationType,
    OptimizationLevel,
    OptimizationRule,
    OptimizationResult,
    OptimizationReport
)
from .content_enhancer import ContentEnhancer
from .structure_normalizer import StructureNormalizer

logger = logging.getLogger(__name__)


class OptimizationCoordinator:
    """
    Coordinates optimization operations using specialized components
    Follows the Coordinator pattern - delegates work to specialists
    """

    def __init__(self, optimization_level: OptimizationLevel = OptimizationLevel.STANDARD):
        self.optimization_level = optimization_level
        self.content_enhancer = ContentEnhancer()
        self.structure_normalizer = StructureNormalizer()
        self.optimization_rules = self._initialize_optimization_rules()

    def _initialize_optimization_rules(self) -> List[OptimizationRule]:
        """Initialize optimization rules based on level"""
        rules = []

        # Content enhancement rules
        rules.append(OptimizationRule(
            rule_id="content_basic_enhancement",
            name="Basic Content Enhancement",
            description="Apply basic grammar and formatting fixes",
            optimization_type=OptimizationType.CONTENT_ENHANCEMENT,
            priority=5,
            target_fields=["all_text_fields"]
        ))

        # Structure normalization rules
        rules.append(OptimizationRule(
            rule_id="structure_normalization",
            name="Structure Normalization",
            description="Normalize data structure to standard format",
            optimization_type=OptimizationType.STRUCTURE_NORMALIZATION,
            priority=4,
            target_fields=["all_structures"]
        ))

        # Add more rules based on optimization level
        if self.optimization_level in [OptimizationLevel.AGGRESSIVE, OptimizationLevel.COMPREHENSIVE]:
            rules.append(OptimizationRule(
                rule_id="advanced_content_enhancement",
                name="Advanced Content Enhancement",
                description="Apply advanced text quality improvements",
                optimization_type=OptimizationType.QUALITY_IMPROVEMENT,
                priority=3,
                target_fields=["meeting_text", "action_items", "decisions"]
            ))

        return sorted(rules, key=lambda r: r.priority, reverse=True)

    async def optimize_extraction_results(
        self,
        extraction_data: Dict[str, Any],
        target_schema: Optional[str] = None,
        custom_rules: Optional[List[OptimizationRule]] = None
    ) -> tuple[Dict[str, Any], OptimizationReport]:
        """
        Main optimization entry point

        Args:
            extraction_data: Raw AI extraction results
            target_schema: Target data schema
            custom_rules: Additional custom optimization rules

        Returns:
            Tuple of (optimized_data, optimization_report)
        """
        start_time = datetime.utcnow()
        report = OptimizationReport(start_time=start_time)
        optimized_data = extraction_data.copy()

        try:
            # Get applicable rules
            applicable_rules = self._get_applicable_rules(extraction_data, custom_rules)
            report.total_rules_applied = len(applicable_rules)

            logger.info(f"Starting optimization with {len(applicable_rules)} rules")

            # Apply optimization rules in priority order
            for rule in applicable_rules:
                try:
                    result = await self._apply_optimization_rule(optimized_data, rule, target_schema)
                    report.results.append(result)

                    if result.success:
                        report.successful_optimizations += 1
                        # Update improvements summary
                        for improvement in result.improvements:
                            improvement_type = improvement.split(':')[0]
                            report.improvements_summary[improvement_type] = (
                                report.improvements_summary.get(improvement_type, 0) + 1
                            )
                    else:
                        report.failed_optimizations += 1
                        logger.warning(f"Rule {rule.rule_id} failed: {result.error_message}")

                except Exception as e:
                    error_result = OptimizationResult(
                        rule_id=rule.rule_id,
                        success=False,
                        error_message=str(e)
                    )
                    report.results.append(error_result)
                    report.failed_optimizations += 1
                    logger.error(f"Error applying rule {rule.rule_id}: {e}")

            # Calculate final metrics
            end_time = datetime.utcnow()
            report.end_time = end_time
            report.processing_time_ms = (end_time - start_time).total_seconds() * 1000
            report.data_quality_score = self._calculate_quality_score(optimized_data, report)

            logger.info(f"Optimization completed: {report.successful_optimizations}/{report.total_rules_applied} rules successful")
            return optimized_data, report

        except Exception as e:
            logger.error(f"Optimization process failed: {e}")
            report.end_time = datetime.utcnow()
            return extraction_data, report

    def _get_applicable_rules(
        self,
        data: Dict[str, Any],
        custom_rules: Optional[List[OptimizationRule]] = None
    ) -> List[OptimizationRule]:
        """Get applicable optimization rules for the data"""
        rules = self.optimization_rules.copy()

        if custom_rules:
            rules.extend(custom_rules)

        # Filter enabled rules
        applicable_rules = [rule for rule in rules if rule.enabled]

        # Filter by optimization level
        if self.optimization_level == OptimizationLevel.MINIMAL:
            applicable_rules = [rule for rule in applicable_rules if rule.priority >= 4]
        elif self.optimization_level == OptimizationLevel.STANDARD:
            applicable_rules = [rule for rule in applicable_rules if rule.priority >= 3]

        return applicable_rules

    async def _apply_optimization_rule(
        self,
        data: Dict[str, Any],
        rule: OptimizationRule,
        target_schema: Optional[str] = None
    ) -> OptimizationResult:
        """Apply a specific optimization rule"""
        start_time = datetime.utcnow()

        try:
            if rule.optimization_type == OptimizationType.CONTENT_ENHANCEMENT:
                improvements = await self._apply_content_enhancement(data, rule)
            elif rule.optimization_type == OptimizationType.STRUCTURE_NORMALIZATION:
                improvements = await self._apply_structure_normalization(data, rule, target_schema)
            elif rule.optimization_type == OptimizationType.QUALITY_IMPROVEMENT:
                improvements = await self._apply_quality_improvement(data, rule)
            else:
                improvements = []

            end_time = datetime.utcnow()
            execution_time = (end_time - start_time).total_seconds() * 1000

            return OptimizationResult(
                rule_id=rule.rule_id,
                success=True,
                improvements=improvements,
                execution_time_ms=execution_time
            )

        except Exception as e:
            end_time = datetime.utcnow()
            execution_time = (end_time - start_time).total_seconds() * 1000

            return OptimizationResult(
                rule_id=rule.rule_id,
                success=False,
                error_message=str(e),
                execution_time_ms=execution_time
            )

    async def _apply_content_enhancement(
        self,
        data: Dict[str, Any],
        rule: OptimizationRule
    ) -> List[str]:
        """Apply content enhancement using ContentEnhancer"""
        improvements = []

        # Enhance text fields recursively
        await self._enhance_text_fields_recursive(data, improvements)

        return improvements

    async def _enhance_text_fields_recursive(
        self,
        data: Any,
        improvements: List[str],
        path: str = ""
    ) -> None:
        """Recursively enhance text fields in data structure"""
        if isinstance(data, dict):
            for key, value in data.items():
                current_path = f"{path}.{key}" if path else key
                await self._enhance_text_fields_recursive(value, improvements, current_path)
        elif isinstance(data, list):
            for i, item in enumerate(data):
                current_path = f"{path}[{i}]" if path else f"[{i}]"
                await self._enhance_text_fields_recursive(item, improvements, current_path)
        elif isinstance(data, str) and len(data.strip()) > 0:
            # Determine enhancement type from path
            enhancement_type = self._get_enhancement_type_from_path(path)
            enhanced_text, text_improvements = await self.content_enhancer.enhance_text_content(
                data, enhancement_type
            )

            # Update the data in-place
            self._update_data_at_path(data, path, enhanced_text)
            improvements.extend([f"{path}: {imp}" for imp in text_improvements])

    def _get_enhancement_type_from_path(self, path: str) -> str:
        """Determine enhancement type from data path"""
        path_lower = path.lower()
        if 'action' in path_lower:
            return 'action'
        elif 'decision' in path_lower:
            return 'decision'
        elif any(term in path_lower for term in ['title', 'topic', 'subject']):
            return 'meeting'
        else:
            return 'general'

    def _update_data_at_path(self, root_data: Any, path: str, new_value: str) -> None:
        """Update data at specified path (simplified implementation)"""
        # This would need a more sophisticated implementation
        # For now, this is a placeholder
        pass

    async def _apply_structure_normalization(
        self,
        data: Dict[str, Any],
        rule: OptimizationRule,
        target_schema: Optional[str] = None
    ) -> List[str]:
        """Apply structure normalization using StructureNormalizer"""
        normalized_data, actions = await self.structure_normalizer.normalize_data_structure(
            data, target_schema
        )

        # Update the original data structure
        data.clear()
        data.update(normalized_data)

        return actions

    async def _apply_quality_improvement(
        self,
        data: Dict[str, Any],
        rule: OptimizationRule
    ) -> List[str]:
        """Apply quality improvements"""
        improvements = []

        # Apply advanced content enhancement for specific fields
        if rule.target_fields:
            for field in rule.target_fields:
                if field in data and isinstance(data[field], str):
                    enhanced_text, text_improvements = await self.content_enhancer.enhance_text_content(
                        data[field], "general"
                    )
                    data[field] = enhanced_text
                    improvements.extend([f"{field}: {imp}" for imp in text_improvements])

        return improvements

    def _calculate_quality_score(
        self,
        data: Dict[str, Any],
        report: OptimizationReport
    ) -> float:
        """Calculate overall data quality score"""
        base_score = 0.5  # Base score

        # Add points for successful optimizations
        success_rate = report.successful_optimizations / max(report.total_rules_applied, 1)
        success_points = success_rate * 0.3

        # Add points for data completeness
        completeness_score = self._assess_data_completeness(data)
        completeness_points = completeness_score * 0.2

        total_score = min(base_score + success_points + completeness_points, 1.0)
        return round(total_score, 2)

    def _assess_data_completeness(self, data: Dict[str, Any]) -> float:
        """Assess data completeness (0.0 to 1.0)"""
        required_fields = ['basic_info', 'attendees', 'agenda', 'action_items', 'decisions']
        present_fields = sum(1 for field in required_fields if field in data and data[field])
        return present_fields / len(required_fields)

    def get_optimization_summary(self, report: OptimizationReport) -> Dict[str, Any]:
        """Get optimization summary"""
        return {
            'total_rules': report.total_rules_applied,
            'successful': report.successful_optimizations,
            'failed': report.failed_optimizations,
            'success_rate': report.successful_optimizations / max(report.total_rules_applied, 1),
            'processing_time_ms': report.processing_time_ms,
            'quality_score': report.data_quality_score,
            'improvements_by_type': report.improvements_summary
        }