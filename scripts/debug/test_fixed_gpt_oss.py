#!/usr/bin/env python3
"""Test fixed gpt-oss:20b model with new configuration"""

import sys
import os
import asyncio
sys.path.append('src')

from rapid_minutes.ai.ollama_client import OllamaClient
from rapid_minutes.ai.extractor import StructuredDataExtractor
import json

async def test_fixed_gpt_oss():
    """Test gpt-oss:20b with fixed configuration"""

    extractor = StructuredDataExtractor()

    test_text = '''會議記錄測試文件

會議主題：產品開發進度討論
日期：2024-09-15
時間：下午 2:00-3:00
主持人：張經理

出席人員：
- 張經理（產品經理）
- 李工程師（技術開發）
- 王設計師（UI/UX設計）

決議事項：
1. 後端API將在9月20日前完成
2. UI測試結果將在9月18日前提交

行動項目：
- 李工程師：完成剩餘API開發（期限：9月20日）
- 王設計師：提交UI測試報告（期限：9月18日）'''

    try:
        print("🧪 Testing fixed gpt-oss:20b configuration...")
        print(f"Model: {extractor.ollama_client.model}")

        result = await extractor.extract_meeting_minutes(test_text)

        print(f"\n📊 Extraction Result:")
        print(f"Status: {result.status.value}")
        print(f"Confidence: {result.confidence_score}")

        if result.minutes:
            minutes = result.minutes
            print(f"\n📝 Extracted Meeting Minutes:")
            print(f"Title: {minutes.basic_info.title}")
            print(f"Date: {minutes.basic_info.date}")
            print(f"Organizer: {minutes.basic_info.organizer}")
            print(f"Attendees: {len(minutes.attendees)}")
            print(f"Agenda Items: {len(minutes.agenda)}")
            print(f"Action Items: {len(minutes.action_items)}")
            print(f"Decisions: {len(minutes.decisions)}")
            print(f"Key Outcomes: {len(minutes.key_outcomes)}")

            # Show some details
            if minutes.attendees:
                print(f"\n👥 Attendees:")
                for attendee in minutes.attendees[:3]:  # Show first 3
                    print(f"  - {attendee.name} ({attendee.role or 'N/A'})")

            if minutes.decisions:
                print(f"\n📋 Decisions:")
                for decision in minutes.decisions[:2]:  # Show first 2
                    print(f"  - {decision.decision}")

            return True
        else:
            print(f"❌ No minutes extracted")
            if result.error_message:
                print(f"Error: {result.error_message}")
            return False

    except Exception as e:
        print(f"💥 Test failed: {e}")
        return False

if __name__ == "__main__":
    success = asyncio.run(test_fixed_gpt_oss())
    print(f"\n{'🎉 FIXED! gpt-oss:20b works correctly' if success else '💔 Still broken'}")