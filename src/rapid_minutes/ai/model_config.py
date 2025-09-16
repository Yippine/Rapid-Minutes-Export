"""
Model-specific configuration and behavior adjustments
Handles different model quirks and requirements
"""

from typing import Dict, Optional, Any

class ModelConfig:
    """Configuration for different Ollama models"""

    # Models that have issues with format='json' parameter
    PROBLEMATIC_JSON_MODELS = {
        'gpt-oss:20b'
    }

    # Model-specific generation options
    MODEL_OPTIONS = {
        'gpt-oss:20b': {
            'temperature': 0.1,
            'top_p': 0.9,
            # Remove format parameter for this model
            'use_json_format': False
        },
        'qwen2.5-coder:7b': {
            'temperature': 0.1,
            'top_p': 0.9,
            'use_json_format': True
        },
        'default': {
            'temperature': 0.1,
            'top_p': 0.9,
            'use_json_format': True
        }
    }

    @classmethod
    def should_use_json_format(cls, model_name: str) -> bool:
        """Check if model supports format='json' parameter"""
        return model_name not in cls.PROBLEMATIC_JSON_MODELS

    @classmethod
    def get_model_options(cls, model_name: str) -> Dict[str, Any]:
        """Get model-specific generation options"""
        return cls.MODEL_OPTIONS.get(model_name, cls.MODEL_OPTIONS['default'])