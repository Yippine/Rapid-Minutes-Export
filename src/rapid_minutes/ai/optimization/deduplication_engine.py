"""
Deduplication Engine
Single Responsibility: Remove duplicate content and normalize similar entries
"""

import logging
from typing import Dict, List, Any, Tuple
from difflib import SequenceMatcher
from collections import defaultdict

logger = logging.getLogger(__name__)


class DeduplicationEngine:
    """
    Specialized class for content deduplication
    Follows SRP - only handles duplicate detection and removal
    """

    def __init__(self, similarity_threshold: float = 0.8):
        self.similarity_threshold = similarity_threshold
        self.deduplication_stats = {
            'duplicates_found': 0,
            'duplicates_removed': 0,
            'similar_items_merged': 0
        }

    async def deduplicate_content(
        self,
        data: Dict[str, Any],
        aggressive: bool = False
    ) -> Tuple[Dict[str, Any], List[str]]:
        """
        Remove duplicate content from data structure

        Args:
            data: Data to deduplicate
            aggressive: Use more aggressive deduplication

        Returns:
            Tuple of (deduplicated_data, actions_taken)
        """
        actions = []
        deduplicated_data = data.copy()

        try:
            # Deduplicate list fields
            list_fields = ['attendees', 'agenda', 'action_items', 'decisions', 'key_outcomes']
            for field in list_fields:
                if field in deduplicated_data and isinstance(deduplicated_data[field], list):
                    original_count = len(deduplicated_data[field])
                    deduplicated_data[field], field_actions = self._deduplicate_list(
                        deduplicated_data[field], field, aggressive
                    )
                    actions.extend(field_actions)

                    if len(deduplicated_data[field]) < original_count:
                        removed_count = original_count - len(deduplicated_data[field])
                        actions.append(f"Removed {removed_count} duplicates from {field}")
                        self.deduplication_stats['duplicates_removed'] += removed_count

            logger.debug(f"Deduplication completed: {len(actions)} actions taken")
            return deduplicated_data, actions

        except Exception as e:
            logger.error(f"Deduplication failed: {e}")
            return data, []

    def _deduplicate_list(
        self,
        items: List[Any],
        field_name: str,
        aggressive: bool = False
    ) -> Tuple[List[Any], List[str]]:
        """Deduplicate items in a list"""
        if not items:
            return items, []

        actions = []
        deduplicated_items = []
        seen_items = set()
        similar_groups = defaultdict(list)

        for item in items:
            # Create a key for exact duplicate detection
            item_key = self._create_item_key(item, field_name)

            # Check for exact duplicates
            if item_key in seen_items:
                actions.append(f"Removed exact duplicate: {item_key[:50]}...")
                self.deduplication_stats['duplicates_found'] += 1
                continue

            seen_items.add(item_key)

            # Check for similar items if aggressive mode
            if aggressive:
                similar_item = self._find_similar_item(item, deduplicated_items, field_name)
                if similar_item:
                    # Merge similar items
                    merged_item = self._merge_similar_items(similar_item, item, field_name)
                    # Replace the similar item with merged version
                    for i, existing_item in enumerate(deduplicated_items):
                        if self._items_are_similar(existing_item, similar_item, field_name):
                            deduplicated_items[i] = merged_item
                            break
                    actions.append(f"Merged similar items in {field_name}")
                    self.deduplication_stats['similar_items_merged'] += 1
                    continue

            deduplicated_items.append(item)

        return deduplicated_items, actions

    def _create_item_key(self, item: Any, field_name: str) -> str:
        """Create a key for duplicate detection"""
        if isinstance(item, str):
            return self._normalize_text_for_comparison(item)
        elif isinstance(item, dict):
            # Create key based on field type
            if field_name == 'attendees':
                name = item.get('name', '')
                role = item.get('role', '')
                return f"{self._normalize_text_for_comparison(name)}|{self._normalize_text_for_comparison(role)}"
            elif field_name == 'action_items':
                task = item.get('task', '')
                assignee = item.get('assignee', '')
                return f"{self._normalize_text_for_comparison(task)}|{assignee.lower()}"
            elif field_name == 'decisions':
                decision = item.get('decision', '')
                return self._normalize_text_for_comparison(decision)
            else:
                # Generic key for other dict types
                primary_field = self._get_primary_field(item)
                return self._normalize_text_for_comparison(str(item.get(primary_field, '')))
        else:
            return str(item).lower().strip()

    def _normalize_text_for_comparison(self, text: str) -> str:
        """Normalize text for comparison"""
        if not isinstance(text, str):
            return str(text)

        # Convert to lowercase, remove extra spaces, and strip
        normalized = ' '.join(text.lower().split())

        # Remove common variations
        replacements = {
            'mr.': 'mr',
            'mrs.': 'mrs',
            'dr.': 'dr',
            '&': 'and',
            '+': 'and'
        }

        for old, new in replacements.items():
            normalized = normalized.replace(old, new)

        return normalized

    def _find_similar_item(
        self,
        target_item: Any,
        existing_items: List[Any],
        field_name: str
    ) -> Any:
        """Find similar item in existing items"""
        for existing_item in existing_items:
            if self._items_are_similar(target_item, existing_item, field_name):
                return existing_item
        return None

    def _items_are_similar(
        self,
        item1: Any,
        item2: Any,
        field_name: str
    ) -> bool:
        """Check if two items are similar"""
        # Get comparison text for both items
        text1 = self._get_comparison_text(item1, field_name)
        text2 = self._get_comparison_text(item2, field_name)

        # Calculate similarity
        similarity = SequenceMatcher(None, text1, text2).ratio()
        return similarity >= self.similarity_threshold

    def _get_comparison_text(self, item: Any, field_name: str) -> str:
        """Get text for comparison from item"""
        if isinstance(item, str):
            return self._normalize_text_for_comparison(item)
        elif isinstance(item, dict):
            if field_name == 'attendees':
                return self._normalize_text_for_comparison(item.get('name', ''))
            elif field_name == 'action_items':
                return self._normalize_text_for_comparison(item.get('task', ''))
            elif field_name == 'decisions':
                return self._normalize_text_for_comparison(item.get('decision', ''))
            else:
                primary_field = self._get_primary_field(item)
                return self._normalize_text_for_comparison(str(item.get(primary_field, '')))
        else:
            return self._normalize_text_for_comparison(str(item))

    def _get_primary_field(self, item: Dict[str, Any]) -> str:
        """Get primary field for comparison"""
        priority_fields = ['title', 'name', 'task', 'decision', 'content', 'description']
        for field in priority_fields:
            if field in item and item[field]:
                return field
        # Return first non-empty field
        for key, value in item.items():
            if value and isinstance(value, str):
                return key
        return list(item.keys())[0] if item else ''

    def _merge_similar_items(
        self,
        item1: Any,
        item2: Any,
        field_name: str
    ) -> Any:
        """Merge two similar items"""
        if isinstance(item1, dict) and isinstance(item2, dict):
            merged = item1.copy()

            # Merge fields, preferring more detailed information
            for key, value in item2.items():
                if key not in merged or not merged[key]:
                    merged[key] = value
                elif len(str(value)) > len(str(merged[key])):
                    merged[key] = value
                elif key in ['description', 'notes', 'details'] and merged[key] != value:
                    # Combine descriptions
                    merged[key] = f"{merged[key]}; {value}"

            return merged
        elif isinstance(item1, str) and isinstance(item2, str):
            # Return the longer string
            return item1 if len(item1) > len(item2) else item2
        else:
            # Return the more complex item
            return item1 if isinstance(item1, dict) else item2

    def get_deduplication_stats(self) -> Dict[str, Any]:
        """Get deduplication statistics"""
        return self.deduplication_stats.copy()

    def reset_stats(self) -> None:
        """Reset deduplication statistics"""
        self.deduplication_stats = {
            'duplicates_found': 0,
            'duplicates_removed': 0,
            'similar_items_merged': 0
        }