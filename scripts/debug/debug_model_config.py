#!/usr/bin/env python3
"""Debug model configuration"""

import sys
sys.path.append('src')

from rapid_minutes.ai.model_config import ModelConfig

def debug_model_config():
    """Debug model configuration settings"""

    models_to_test = ['gpt-oss:20b', 'qwen2.5-coder:7b', 'unknown-model']

    for model in models_to_test:
        print(f"\n{'='*50}")
        print(f"Model: {model}")
        print(f"{'='*50}")

        should_use_json = ModelConfig.should_use_json_format(model)
        options = ModelConfig.get_model_options(model)

        print(f"Should use JSON format: {should_use_json}")
        print(f"Model options: {options}")

        # Simulate what the extractor would do
        from rapid_minutes.ai.extractor import StructuredDataExtractor

        dummy_extractor = StructuredDataExtractor()
        dummy_extractor.ollama_client.model = model  # Override model

        gen_params = dummy_extractor._get_generation_params(options)
        print(f"Generation parameters: {gen_params}")

if __name__ == "__main__":
    debug_model_config()