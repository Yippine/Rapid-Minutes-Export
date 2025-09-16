#!/usr/bin/env python3
"""Debug gpt-oss:20b model issues"""

import sys
import os
import asyncio
sys.path.append('src')

from rapid_minutes.ai.ollama_client import OllamaClient
import json

async def debug_gpt_oss_model():
    """Debug different ways to call gpt-oss:20b"""

    client = OllamaClient(
        base_url="http://172.22.80.1:11434",
        model="gpt-oss:20b"
    )

    simple_prompt = "Hello, how are you?"

    meeting_prompt = '''Extract meeting information from:
會議主題：產品開發進度討論
日期：2024-09-15
主持人：張經理

Return as JSON:'''

    tests = [
        {
            "name": "Simple prompt without JSON format",
            "prompt": simple_prompt,
            "format": None,
            "options": {}
        },
        {
            "name": "Simple prompt with JSON format",
            "prompt": simple_prompt,
            "format": "json",
            "options": {}
        },
        {
            "name": "Meeting prompt without JSON format",
            "prompt": meeting_prompt,
            "format": None,
            "options": {}
        },
        {
            "name": "Meeting prompt with JSON format",
            "prompt": meeting_prompt,
            "format": "json",
            "options": {}
        },
        {
            "name": "Meeting prompt with JSON format + temp 0.1",
            "prompt": meeting_prompt,
            "format": "json",
            "options": {"temperature": 0.1}
        },
        {
            "name": "Meeting prompt with JSON format + temp 0.7",
            "prompt": meeting_prompt,
            "format": "json",
            "options": {"temperature": 0.7}
        }
    ]

    try:
        for i, test in enumerate(tests, 1):
            print(f"\n{'='*60}")
            print(f"Test {i}: {test['name']}")
            print(f"{'='*60}")

            try:
                response = await client.generate(
                    prompt=test['prompt'],
                    format=test['format'],
                    options=test['options']
                )

                print(f"Response length: {len(response.content)}")
                print(f"Response content: {repr(response.content)}")

                if response.content:
                    print(f"First 200 chars: {response.content[:200]}")

                    if test['format'] == 'json' and response.content:
                        try:
                            parsed = json.loads(response.content)
                            print(f"✅ Valid JSON: {parsed}")
                        except:
                            print("❌ Invalid JSON format")
                else:
                    print("❌ EMPTY RESPONSE")

            except Exception as e:
                print(f"💥 Test failed: {e}")

    finally:
        await client.close()

if __name__ == "__main__":
    asyncio.run(debug_gpt_oss_model())