"""
AI Optimization Module
Refactored from the monolithic result_optimizer.py into specialized components
"""

from .content_enhancer import ContentEnhancer
from .structure_normalizer import StructureNormalizer
from .deduplication_engine import DeduplicationEngine
from .completeness_filler import CompletenessFiller
from .optimization_coordinator import OptimizationCoordinator
from .optimization_types import (
    OptimizationType,
    OptimizationLevel,
    OptimizationRule,
    OptimizationResult,
    OptimizationReport
)

__all__ = [
    'ContentEnhancer',
    'StructureNormalizer',
    'DeduplicationEngine',
    'CompletenessFiller',
    'OptimizationCoordinator',
    'OptimizationType',
    'OptimizationLevel',
    'OptimizationRule',
    'OptimizationResult',
    'OptimizationReport'
]