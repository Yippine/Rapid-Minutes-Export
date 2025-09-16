#!/usr/bin/env python3
"""Test single extraction method with fixed configuration"""

import sys
import asyncio
sys.path.append('src')

from rapid_minutes.ai.extractor import StructuredDataExtractor

async def test_single_extraction():
    """Test single basic_info extraction"""

    extractor = StructuredDataExtractor()

    test_text = '''會議記錄測試文件

會議主題：產品開發進度討論
日期：2024-09-15
時間：下午 2:00-3:00
主持人：張經理'''

    try:
        print(f"🧪 Testing basic_info extraction with model: {extractor.ollama_client.model}")

        # Test the fixed _extract_basic_info method
        basic_info = await extractor._extract_basic_info(test_text)

        print(f"\n📝 Extracted basic info:")
        print(f"Title: {basic_info.title}")
        print(f"Date: {basic_info.date}")
        print(f"Time: {basic_info.time}")
        print(f"Organizer: {basic_info.organizer}")

        return basic_info.title is not None

    except Exception as e:
        print(f"💥 Test failed: {e}")
        return False
    finally:
        await extractor.ollama_client.close()

if __name__ == "__main__":
    success = asyncio.run(test_single_extraction())
    print(f"\n{'✅ SUCCESS' if success else '❌ FAILED'}")