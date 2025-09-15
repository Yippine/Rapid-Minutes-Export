"""
Structure Normalization Specialist
Single Responsibility: Data structure normalization and standardization
"""

import logging
from typing import Dict, List, Any, Optional


logger = logging.getLogger(__name__)


class StructureNormalizer:
    """
    Specialized class for data structure normalization
    Follows SRP - only handles data structure standardization
    """

    def __init__(self):
        self.standard_fields = self._initialize_standard_fields()
        self.field_mappings = self._initialize_field_mappings()

    def _initialize_standard_fields(self) -> Dict[str, List[str]]:
        """Initialize standard field structures"""
        return {
            'basic_info': [
                'title', 'date', 'time', 'location', 'organizer', 'meeting_type'
            ],
            'attendees': [
                'name', 'role', 'email', 'present', 'department'
            ],
            'agenda_item': [
                'title', 'description', 'duration', 'presenter', 'priority'
            ],
            'action_item': [
                'task', 'assignee', 'deadline', 'priority', 'status', 'description'
            ],
            'decision': [
                'decision', 'rationale', 'impact', 'responsible_party', 'implementation_date'
            ]
        }

    def _initialize_field_mappings(self) -> Dict[str, str]:
        """Initialize field name mappings for normalization"""
        return {
            # Basic info mappings
            'meeting_title': 'title',
            'subject': 'title',
            'topic': 'title',
            'meeting_date': 'date',
            'when': 'date',
            'meeting_time': 'time',
            'start_time': 'time',
            'venue': 'location',
            'room': 'location',
            'chair': 'organizer',
            'facilitator': 'organizer',

            # Attendee mappings
            'participant': 'name',
            'attendee': 'name',
            'member': 'name',
            'position': 'role',
            'job_title': 'role',
            'attendance': 'present',
            'attended': 'present',

            # Action item mappings
            'action': 'task',
            'todo': 'task',
            'responsibility': 'task',
            'owner': 'assignee',
            'responsible': 'assignee',
            'due_date': 'deadline',
            'target_date': 'deadline',

            # Decision mappings
            'conclusion': 'decision',
            'resolution': 'decision',
            'outcome': 'decision',
            'reason': 'rationale',
            'justification': 'rationale'
        }

    async def normalize_data_structure(
        self,
        data: Dict[str, Any],
        target_schema: Optional[str] = None
    ) -> tuple[Dict[str, Any], List[str]]:
        """
        Normalize data structure to standard format

        Args:
            data: Raw data to normalize
            target_schema: Target schema name (optional)

        Returns:
            Tuple of (normalized_data, normalization_actions)
        """
        if not isinstance(data, dict):
            return data, []

        normalization_actions = []
        normalized_data = {}

        try:
            # Normalize top-level structure
            normalized_data, top_level_actions = self._normalize_top_level_fields(data)
            normalization_actions.extend(top_level_actions)

            # Normalize nested structures
            for field_name, field_value in normalized_data.items():
                if isinstance(field_value, list):
                    normalized_data[field_name], list_actions = self._normalize_list_items(
                        field_value, field_name
                    )
                    normalization_actions.extend(list_actions)
                elif isinstance(field_value, dict):
                    normalized_data[field_name], dict_actions = self._normalize_dict_structure(
                        field_value, field_name
                    )
                    normalization_actions.extend(dict_actions)

            # Apply schema-specific normalization
            if target_schema:
                normalized_data, schema_actions = self._apply_schema_normalization(
                    normalized_data, target_schema
                )
                normalization_actions.extend(schema_actions)

            # Validate and fill missing required fields
            normalized_data, validation_actions = self._validate_and_fill_structure(
                normalized_data
            )
            normalization_actions.extend(validation_actions)

            logger.debug(f"Structure normalized: {len(normalization_actions)} actions performed")
            return normalized_data, normalization_actions

        except Exception as e:
            logger.error(f"Structure normalization failed: {e}")
            return data, []

    def _normalize_top_level_fields(self, data: Dict[str, Any]) -> tuple[Dict[str, Any], List[str]]:
        """Normalize top-level field names"""
        actions = []
        normalized = {}

        for key, value in data.items():
            # Normalize field name
            normalized_key = self.field_mappings.get(key.lower(), key)

            if normalized_key != key:
                actions.append(f"Normalized field name: {key} -> {normalized_key}")

            # Handle duplicate fields by merging
            if normalized_key in normalized:
                if isinstance(normalized[normalized_key], list) and isinstance(value, list):
                    normalized[normalized_key].extend(value)
                    actions.append(f"Merged duplicate list field: {normalized_key}")
                elif isinstance(normalized[normalized_key], dict) and isinstance(value, dict):
                    normalized[normalized_key].update(value)
                    actions.append(f"Merged duplicate dict field: {normalized_key}")
                else:
                    # Keep the more detailed value
                    if len(str(value)) > len(str(normalized[normalized_key])):
                        normalized[normalized_key] = value
                        actions.append(f"Replaced field with more detailed value: {normalized_key}")
            else:
                normalized[normalized_key] = value

        return normalized, actions

    def _normalize_list_items(
        self,
        items: List[Any],
        field_name: str
    ) -> tuple[List[Any], List[str]]:
        """Normalize items in a list"""
        actions = []
        normalized_items = []

        item_type = self._get_item_type_from_field_name(field_name)

        for item in items:
            if isinstance(item, dict):
                normalized_item, item_actions = self._normalize_dict_structure(item, item_type)
                normalized_items.append(normalized_item)
                actions.extend(item_actions)
            else:
                # Handle string items that should be dictionaries
                if item_type and isinstance(item, str):
                    normalized_item = self._convert_string_to_dict(item, item_type)
                    normalized_items.append(normalized_item)
                    actions.append(f"Converted string to {item_type} structure: {item[:50]}...")
                else:
                    normalized_items.append(item)

        return normalized_items, actions

    def _normalize_dict_structure(
        self,
        data: Dict[str, Any],
        structure_type: Optional[str] = None
    ) -> tuple[Dict[str, Any], List[str]]:
        """Normalize dictionary structure"""
        actions = []
        normalized = {}

        # Get standard fields for this structure type
        standard_fields = self.standard_fields.get(structure_type, [])

        # Normalize field names
        for key, value in data.items():
            normalized_key = self.field_mappings.get(key.lower(), key)

            if normalized_key != key:
                actions.append(f"Normalized {structure_type} field: {key} -> {normalized_key}")

            normalized[normalized_key] = value

        # Add missing standard fields with default values
        if standard_fields:
            for field in standard_fields:
                if field not in normalized:
                    default_value = self._get_default_value(field)
                    if default_value is not None:
                        normalized[field] = default_value
                        actions.append(f"Added missing {structure_type} field: {field}")

        return normalized, actions

    def _get_item_type_from_field_name(self, field_name: str) -> Optional[str]:
        """Determine item type from field name"""
        type_mappings = {
            'attendees': 'attendees',
            'participants': 'attendees',
            'agenda': 'agenda_item',
            'agenda_items': 'agenda_item',
            'action_items': 'action_item',
            'actions': 'action_item',
            'todos': 'action_item',
            'decisions': 'decision',
            'resolutions': 'decision'
        }
        return type_mappings.get(field_name.lower())

    def _convert_string_to_dict(self, text: str, structure_type: str) -> Dict[str, Any]:
        """Convert string to structured dictionary"""
        if structure_type == 'attendees':
            # Try to parse "Name (Role)" format
            match = re.match(r'^(.+?)\s*\((.+?)\)\s*$', text.strip())
            if match:
                return {
                    'name': match.group(1).strip(),
                    'role': match.group(2).strip(),
                    'present': True
                }
            else:
                return {'name': text.strip(), 'role': '', 'present': True}

        elif structure_type == 'action_item':
            return {
                'task': text.strip(),
                'assignee': '',
                'deadline': '',
                'status': 'pending'
            }

        elif structure_type == 'decision':
            return {
                'decision': text.strip(),
                'rationale': '',
                'impact': ''
            }

        elif structure_type == 'agenda_item':
            return {
                'title': text.strip(),
                'description': '',
                'presenter': ''
            }

        else:
            return {'content': text.strip()}

    def _apply_schema_normalization(
        self,
        data: Dict[str, Any],
        schema: str
    ) -> tuple[Dict[str, Any], List[str]]:
        """Apply schema-specific normalization rules"""
        actions = []
        normalized = data.copy()

        if schema == 'meeting_minutes':
            # Ensure required top-level sections exist
            required_sections = ['basic_info', 'attendees', 'agenda', 'action_items', 'decisions']
            for section in required_sections:
                if section not in normalized:
                    normalized[section] = [] if section != 'basic_info' else {}
                    actions.append(f"Added missing section: {section}")

        elif schema == 'action_tracking':
            # Focus on action items structure
            if 'action_items' in normalized:
                for action in normalized['action_items']:
                    if isinstance(action, dict) and 'status' not in action:
                        action['status'] = 'pending'
                        actions.append("Added default status to action item")

        return normalized, actions

    def _validate_and_fill_structure(
        self,
        data: Dict[str, Any]
    ) -> tuple[Dict[str, Any], List[str]]:
        """Validate structure and fill missing critical fields"""
        actions = []
        validated = data.copy()

        # Ensure basic_info has minimum required fields
        if 'basic_info' in validated and isinstance(validated['basic_info'], dict):
            basic_info = validated['basic_info']
            if not basic_info.get('title'):
                basic_info['title'] = 'Meeting'
                actions.append("Added default meeting title")

        # Ensure lists are properly formatted
        list_fields = ['attendees', 'agenda', 'action_items', 'decisions', 'key_outcomes']
        for field in list_fields:
            if field in validated and not isinstance(validated[field], list):
                if validated[field] is None:
                    validated[field] = []
                else:
                    validated[field] = [validated[field]]
                actions.append(f"Converted {field} to list format")

        return validated, actions

    def _get_default_value(self, field_name: str) -> Any:
        """Get default value for a field"""
        defaults = {
            'present': True,
            'status': 'pending',
            'priority': 'medium',
            'role': '',
            'email': '',
            'department': '',
            'description': '',
            'rationale': '',
            'impact': ''
        }
        return defaults.get(field_name)

    def get_normalization_stats(self) -> Dict[str, Any]:
        """Get normalization statistics"""
        return {
            'standard_structures': len(self.standard_fields),
            'field_mappings': len(self.field_mappings),
            'supported_schemas': ['meeting_minutes', 'action_tracking']
        }