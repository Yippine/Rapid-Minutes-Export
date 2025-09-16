#!/usr/bin/env python3
"""Test JSON cleaning function"""

import sys
import os
sys.path.append('src')

from rapid_minutes.ai.extractor import clean_json_response
import json

# Test samples based on the actual error pattern
test_samples = [
    # Control character at beginning (from logs)
    '\x04\n    "title": "test"',

    # Normal JSON with markdown formatting
    '```json\n{"title": "test"}\n```',

    # JSON with extra text
    'Here is the JSON response:\n{"title": "test", "date": "2024-09-15"}',

    # Array response
    'Response:\n[{"name": "John", "role": "Manager"}]',

    # Malformed with control characters
    '\x00\x01{"title": "test"}\x02\x03',
]

def test_json_cleaning():
    print("Testing JSON cleaning function...")

    for i, sample in enumerate(test_samples, 1):
        print(f"\nTest {i}: {repr(sample[:30])}...")

        try:
            cleaned = clean_json_response(sample)
            print(f"Cleaned: {repr(cleaned[:50])}")

            # Try to parse as JSON
            try:
                parsed = json.loads(cleaned)
                print(f"✅ Successfully parsed: {type(parsed)}")
                print(f"   Content: {parsed}")
            except json.JSONDecodeError as e:
                print(f"❌ Still cannot parse JSON: {e}")

        except Exception as e:
            print(f"💥 Cleaning failed: {e}")

if __name__ == "__main__":
    test_json_cleaning()