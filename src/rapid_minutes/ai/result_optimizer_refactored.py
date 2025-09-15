"""
AI Result Optimizer - Refactored Version
Lightweight facade that uses the refactored optimization components
Maintains backward compatibility while using the new modular architecture
"""

import logging
from typing import Dict, Any, Optional, List

from .optimization import (
    OptimizationCoordinator,
    OptimizationType,
    OptimizationLevel,
    OptimizationRule,
    OptimizationResult,
    OptimizationReport
)

logger = logging.getLogger(__name__)


class ResultOptimizer:
    """
    Refactored Result Optimizer - now a lightweight facade
    Delegates actual work to specialized optimization components
    """

    def __init__(self, optimization_level: OptimizationLevel = OptimizationLevel.STANDARD):
        """
        Initialize with optimization coordinator

        Args:
            optimization_level: Level of optimization to apply
        """
        self.optimization_level = optimization_level
        self.coordinator = OptimizationCoordinator(optimization_level)
        logger.info(f"ResultOptimizer initialized with level: {optimization_level.value}")

    async def optimize_extraction_results(
        self,
        extraction_data: Dict[str, Any],
        optimization_rules: Optional[List[OptimizationRule]] = None,
        target_schema: Optional[str] = None
    ) -> tuple[Dict[str, Any], OptimizationReport]:
        """
        Optimize AI extraction results

        Args:
            extraction_data: Raw extraction data from AI
            optimization_rules: Custom optimization rules to apply
            target_schema: Target data schema for normalization

        Returns:
            Tuple of (optimized_data, optimization_report)
        """
        try:
            logger.info("Starting result optimization process")

            # Delegate to coordinator
            optimized_data, report = await self.coordinator.optimize_extraction_results(
                extraction_data=extraction_data,
                target_schema=target_schema or "meeting_minutes",
                custom_rules=optimization_rules
            )

            logger.info(f"Optimization completed: {report.successful_optimizations}/{report.total_rules_applied} rules successful")
            return optimized_data, report

        except Exception as e:
            logger.error(f"Optimization process failed: {e}")
            # Return original data with error report
            error_report = OptimizationReport(
                total_rules_applied=0,
                successful_optimizations=0,
                failed_optimizations=1
            )
            return extraction_data, error_report

    async def enhance_text_content(
        self,
        content: str,
        enhancement_type: str = "general"
    ) -> tuple[str, List[str]]:
        """
        Enhance text content quality

        Args:
            content: Text content to enhance
            enhancement_type: Type of enhancement to apply

        Returns:
            Tuple of (enhanced_content, improvements_made)
        """
        try:
            return await self.coordinator.content_enhancer.enhance_text_content(
                content, enhancement_type
            )
        except Exception as e:
            logger.error(f"Text enhancement failed: {e}")
            return content, []

    async def normalize_data_structure(
        self,
        data: Dict[str, Any],
        target_schema: Optional[str] = None
    ) -> tuple[Dict[str, Any], List[str]]:
        """
        Normalize data structure

        Args:
            data: Data to normalize
            target_schema: Target schema for normalization

        Returns:
            Tuple of (normalized_data, normalization_actions)
        """
        try:
            return await self.coordinator.structure_normalizer.normalize_data_structure(
                data, target_schema
            )
        except Exception as e:
            logger.error(f"Structure normalization failed: {e}")
            return data, []

    def get_optimization_summary(self, report: OptimizationReport) -> Dict[str, Any]:
        """
        Get optimization summary

        Args:
            report: Optimization report

        Returns:
            Summary dictionary
        """
        return self.coordinator.get_optimization_summary(report)

    def get_available_optimization_types(self) -> List[str]:
        """Get list of available optimization types"""
        return [opt_type.value for opt_type in OptimizationType]

    def get_optimization_stats(self) -> Dict[str, Any]:
        """Get optimization statistics"""
        return {
            'optimization_level': self.optimization_level.value,
            'available_rules': len(self.coordinator.optimization_rules),
            'content_enhancer_stats': self.coordinator.content_enhancer.get_enhancement_stats(),
            'structure_normalizer_stats': self.coordinator.structure_normalizer.get_normalization_stats()
        }


# Backward compatibility - create default instance
default_optimizer = ResultOptimizer()


# Convenience functions for backward compatibility
async def optimize_extraction_results(
    extraction_data: Dict[str, Any],
    optimization_level: OptimizationLevel = OptimizationLevel.STANDARD
) -> tuple[Dict[str, Any], OptimizationReport]:
    """
    Convenience function for optimizing extraction results

    Args:
        extraction_data: Raw extraction data
        optimization_level: Optimization level to apply

    Returns:
        Tuple of (optimized_data, report)
    """
    optimizer = ResultOptimizer(optimization_level)
    return await optimizer.optimize_extraction_results(extraction_data)


async def enhance_text_content(
    content: str,
    enhancement_type: str = "general"
) -> tuple[str, List[str]]:
    """
    Convenience function for text enhancement

    Args:
        content: Text to enhance
        enhancement_type: Type of enhancement

    Returns:
        Tuple of (enhanced_text, improvements)
    """
    return await default_optimizer.enhance_text_content(content, enhancement_type)


async def normalize_data_structure(
    data: Dict[str, Any],
    target_schema: Optional[str] = None
) -> tuple[Dict[str, Any], List[str]]:
    """
    Convenience function for data normalization

    Args:
        data: Data to normalize
        target_schema: Target schema

    Returns:
        Tuple of (normalized_data, actions)
    """
    return await default_optimizer.normalize_data_structure(data, target_schema)


# Export the refactored components
__all__ = [
    'ResultOptimizer',
    'OptimizationType',
    'OptimizationLevel',
    'OptimizationRule',
    'OptimizationResult',
    'OptimizationReport',
    'optimize_extraction_results',
    'enhance_text_content',
    'normalize_data_structure'
]