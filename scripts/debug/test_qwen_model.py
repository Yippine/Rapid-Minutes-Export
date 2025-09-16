#!/usr/bin/env python3
"""Test qwen2.5-coder:7b model for meeting extraction"""

import sys
import os
import asyncio
sys.path.append('src')

from rapid_minutes.ai.ollama_client import OllamaClient
from rapid_minutes.ai.extractor import clean_json_response
import json

async def test_qwen_extraction():
    """Test qwen2.5-coder:7b model with meeting extraction prompt"""

    client = OllamaClient(
        base_url="http://172.22.80.1:11434",
        model="qwen2.5-coder:7b"
    )

    test_prompt = '''You are an expert meeting minutes analyzer. Extract basic meeting information from the following text.
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

出席人員：
- 張經理（產品經理）
- 李工程師（技術開發）

JSON Response:'''

    try:
        print("🧪 Testing qwen2.5-coder:7b model...")

        response = await client.generate(
            prompt=test_prompt,
            format='json',
            options={'temperature': 0.1, 'top_p': 0.9}
        )

        print(f"\n📝 Raw Response ({len(response.content)} chars):")
        print(f"Content: {repr(response.content[:200])}...")

        if response.content:
            print(f"\n🧹 After cleaning:")
            cleaned = clean_json_response(response.content)
            print(f"Cleaned: {cleaned}")

            try:
                parsed = json.loads(cleaned)
                print(f"\n✅ Successfully extracted meeting info:")
                for key, value in parsed.items():
                    print(f"  {key}: {value}")
                return True
            except json.JSONDecodeError as e:
                print(f"\n❌ JSON parse failed: {e}")
                return False
        else:
            print(f"\n❌ Model returned empty response!")
            return False

    except Exception as e:
        print(f"💥 Test failed: {e}")
        return False
    finally:
        await client.close()

if __name__ == "__main__":
    success = asyncio.run(test_qwen_extraction())
    print(f"\n{'🎉 Test PASSED' if success else '💔 Test FAILED'}")