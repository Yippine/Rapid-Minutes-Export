"""
Optimization Types and Data Structures
Extracted from result_optimizer.py for better organization
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Any
from datetime import datetime


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
    """Result of optimization operation"""
    rule_id: str
    success: bool
    improvements: List[str] = field(default_factory=list)
    changes_made: Dict[str, Any] = field(default_factory=dict)
    execution_time_ms: float = 0.0
    error_message: str = ""


@dataclass
class OptimizationReport:
    """Complete optimization report"""
    total_rules_applied: int = 0
    successful_optimizations: int = 0
    failed_optimizations: int = 0
    results: List[OptimizationResult] = field(default_factory=list)
    start_time: datetime = field(default_factory=datetime.utcnow)
    end_time: datetime = field(default_factory=datetime.utcnow)
    processing_time_ms: float = 0.0
    improvements_summary: Dict[str, int] = field(default_factory=dict)
    data_quality_score: float = 0.0  # 0.0 - 1.0