#!/usr/bin/env python3
"""Debug AI response to see actual content"""

import sys
import os
import asyncio
sys.path.append('src')

from rapid_minutes.ai.ollama_client import OllamaClient
from rapid_minutes.ai.extractor import clean_json_response
import json

async def test_actual_ai_response():
    """Test what the AI actually returns"""

    # Initialize client with same settings as app
    client = OllamaClient(
        base_url="http://172.22.80.1:11434",
        model="gpt-oss:20b"  # Same model from user's configuration
    )

    # Test prompt similar to what the app uses
    test_prompt = '''
You are an expert meeting minutes analyzer. Extract basic meeting information from the following text.
Return ONLY a JSON object with these exact fields (use null for missing information):
{
    "title": "meeting title or subject",
    "date": "meeting date in YYYY-MM-DD format",
    "time": "meeting time",
    "duration": "meeting duration",
    "location": "meeting location or platform",
    "meeting_type": "type of meeting",
    "organizer": "meeting organizer name"
}

Text to analyze:
會議記錄測試文件

會議主題：產品開發進度討論
日期：2024-09-15
時間：下午 2:00-3:00
主持人：張經理

JSON Response:'''

    try:
        print("🚀 Testing AI response...")

        response = await client.generate(
            prompt=test_prompt,
            format='json',
            options={'temperature': 0.1, 'top_p': 0.9}
        )

        print(f"\n📝 Raw AI Response ({len(response.content)} chars):")
        print(f"Raw: {repr(response.content)}")
        print(f"Display: {response.content}")

        print(f"\n🧹 After cleaning:")
        cleaned = clean_json_response(response.content)
        print(f"Cleaned: {repr(cleaned)}")
        print(f"Display: {cleaned}")

        print(f"\n🔍 JSON parsing test:")
        try:
            parsed = json.loads(cleaned)
            print(f"✅ Successfully parsed: {parsed}")
        except json.JSONDecodeError as e:
            print(f"❌ JSON parse failed: {e}")
            # Show character by character analysis
            print(f"Character analysis:")
            for i, char in enumerate(cleaned[:50]):
                print(f"  {i:2d}: {repr(char)} (ord: {ord(char)})")

    except Exception as e:
        print(f"💥 Test failed: {e}")
    finally:
        await client.close()

if __name__ == "__main__":
    asyncio.run(test_actual_ai_response())