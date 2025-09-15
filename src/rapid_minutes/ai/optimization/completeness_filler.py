"""
Completeness Filler
Single Responsibility: Fill missing content and ensure data completeness
"""

import logging
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime
import re

logger = logging.getLogger(__name__)


class CompletenessFiller:
    """
    Specialized class for filling missing content and ensuring completeness
    Follows SRP - only handles completeness validation and filling
    """

    def __init__(self):
        self.default_values = self._initialize_default_values()
        self.completion_patterns = self._initialize_completion_patterns()

    def _initialize_default_values(self) -> Dict[str, Any]:
        """Initialize default values for missing fields"""
        return {
            'basic_info': {
                'title': 'Meeting',
                'date': datetime.now().strftime('%Y-%m-%d'),
                'time': '00:00',
                'location': 'TBD',
                'organizer': 'TBD',
                'meeting_type': 'General'
            },
            'attendee': {
                'name': 'Unnamed Participant',
                'role': 'Participant',
                'present': True,
                'email': '',
                'department': ''
            },
            'action_item': {
                'task': 'Action required',
                'assignee': 'TBD',
                'deadline': 'TBD',
                'priority': 'Medium',
                'status': 'Pending',
                'description': ''
            },
            'decision': {
                'decision': 'Decision made',
                'rationale': 'TBD',
                'impact': 'TBD',
                'responsible_party': 'TBD',
                'implementation_date': 'TBD'
            },
            'agenda_item': {
                'title': 'Agenda item',
                'description': '',
                'duration': 'TBD',
                'presenter': 'TBD',
                'priority': 'Medium'
            }
        }

    def _initialize_completion_patterns(self) -> Dict[str, List[str]]:
        """Initialize patterns for content completion"""
        return {
            'action_verbs': [
                'review', 'complete', 'prepare', 'schedule', 'follow up',
                'contact', 'update', 'implement', 'analyze', 'research'
            ],
            'time_patterns': [
                r'\b(by|before|until)\s+(\w+\s+\d{1,2})',
                r'\b(next|this)\s+(week|month|friday|monday)',
                r'\b\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b'
            ],
            'responsibility_patterns': [
                r'\b(\w+)\s+(will|to|should)\s+',
                r'\b(\w+)\s+responsible\s+for\b',
                r'\bassigned\s+to\s+(\w+)\b'
            ]
        }

    async def fill_missing_content(
        self,
        data: Dict[str, Any],
        completion_level: str = "standard"
    ) -> Tuple[Dict[str, Any], List[str]]:
        """
        Fill missing content and ensure completeness

        Args:
            data: Data to complete
            completion_level: Level of completion (minimal, standard, comprehensive)

        Returns:
            Tuple of (completed_data, completion_actions)
        """
        actions = []
        completed_data = data.copy()

        try:
            # Fill missing top-level sections
            completed_data, section_actions = self._fill_missing_sections(completed_data)
            actions.extend(section_actions)

            # Fill missing fields in existing sections
            completed_data, field_actions = self._fill_missing_fields(
                completed_data, completion_level
            )
            actions.extend(field_actions)

            # Enhance incomplete content
            if completion_level in ["standard", "comprehensive"]:
                completed_data, enhancement_actions = self._enhance_incomplete_content(
                    completed_data
                )
                actions.extend(enhancement_actions)

            # Add inferred information
            if completion_level == "comprehensive":
                completed_data, inference_actions = self._add_inferred_information(
                    completed_data
                )
                actions.extend(inference_actions)

            logger.debug(f"Content completion: {len(actions)} actions taken")
            return completed_data, actions

        except Exception as e:
            logger.error(f"Content completion failed: {e}")
            return data, []

    def _fill_missing_sections(self, data: Dict[str, Any]) -> Tuple[Dict[str, Any], List[str]]:
        """Fill missing top-level sections"""
        actions = []
        completed = data.copy()

        required_sections = ['basic_info', 'attendees', 'agenda', 'action_items', 'decisions']

        for section in required_sections:
            if section not in completed:
                if section == 'basic_info':
                    completed[section] = self.default_values['basic_info'].copy()
                else:
                    completed[section] = []
                actions.append(f"Added missing section: {section}")

        return completed, actions

    def _fill_missing_fields(
        self,
        data: Dict[str, Any],
        completion_level: str
    ) -> Tuple[Dict[str, Any], List[str]]:
        """Fill missing fields in existing sections"""
        actions = []
        completed = data.copy()

        # Fill basic_info fields
        if 'basic_info' in completed and isinstance(completed['basic_info'], dict):
            basic_info = completed['basic_info']
            for field, default_value in self.default_values['basic_info'].items():
                if field not in basic_info or not basic_info[field]:
                    if completion_level == "minimal" and field in ['location', 'organizer']:
                        continue  # Skip optional fields in minimal mode
                    basic_info[field] = default_value
                    actions.append(f"Added missing basic_info field: {field}")

        # Fill list item fields
        list_sections = ['attendees', 'action_items', 'decisions', 'agenda']
        for section in list_sections:
            if section in completed and isinstance(completed[section], list):
                for i, item in enumerate(completed[section]):
                    if isinstance(item, dict):
                        item_type = section[:-1] if section.endswith('s') else section
                        if item_type == 'attendee':
                            item_type = 'attendee'
                        elif item_type == 'action_item':
                            item_type = 'action_item'

                        if item_type in self.default_values:
                            for field, default_value in self.default_values[item_type].items():
                                if field not in item or not item[field]:
                                    if completion_level == "minimal" and field in ['email', 'department', 'description']:
                                        continue
                                    item[field] = default_value
                                    actions.append(f"Added missing {item_type} field: {field} to item {i}")

        return completed, actions

    def _enhance_incomplete_content(
        self,
        data: Dict[str, Any]
    ) -> Tuple[Dict[str, Any], List[str]]:
        """Enhance incomplete content with intelligent completion"""
        actions = []
        enhanced = data.copy()

        # Enhance action items
        if 'action_items' in enhanced:
            for i, action in enumerate(enhanced['action_items']):
                if isinstance(action, dict):
                    # Try to extract assignee from task text
                    if not action.get('assignee') or action['assignee'] == 'TBD':
                        extracted_assignee = self._extract_assignee_from_text(
                            action.get('task', '')
                        )
                        if extracted_assignee:
                            action['assignee'] = extracted_assignee
                            actions.append(f"Extracted assignee from action item {i}: {extracted_assignee}")

                    # Try to extract deadline from task text
                    if not action.get('deadline') or action['deadline'] == 'TBD':
                        extracted_deadline = self._extract_deadline_from_text(
                            action.get('task', '')
                        )
                        if extracted_deadline:
                            action['deadline'] = extracted_deadline
                            actions.append(f"Extracted deadline from action item {i}: {extracted_deadline}")

                    # Improve task description
                    if action.get('task') and not action.get('task').strip().lower().startswith(tuple(self.completion_patterns['action_verbs'])):
                        action['task'] = self._improve_action_task_text(action['task'])
                        actions.append(f"Improved action item {i} task format")

        # Enhance decisions with rationale
        if 'decisions' in enhanced:
            for i, decision in enumerate(enhanced['decisions']):
                if isinstance(decision, dict):
                    if not decision.get('rationale') or decision['rationale'] == 'TBD':
                        inferred_rationale = self._infer_decision_rationale(
                            decision.get('decision', ''), enhanced
                        )
                        if inferred_rationale:
                            decision['rationale'] = inferred_rationale
                            actions.append(f"Inferred rationale for decision {i}")

        return enhanced, actions

    def _add_inferred_information(
        self,
        data: Dict[str, Any]
    ) -> Tuple[Dict[str, Any], List[str]]:
        """Add inferred information based on context"""
        actions = []
        inferred = data.copy()

        # Infer meeting duration
        if 'basic_info' in inferred and 'agenda' in inferred:
            if not inferred['basic_info'].get('duration'):
                estimated_duration = self._estimate_meeting_duration(inferred['agenda'])
                if estimated_duration:
                    inferred['basic_info']['duration'] = estimated_duration
                    actions.append(f"Estimated meeting duration: {estimated_duration}")

        # Add key outcomes if missing
        if 'key_outcomes' not in inferred or not inferred['key_outcomes']:
            inferred_outcomes = self._infer_key_outcomes(inferred)
            if inferred_outcomes:
                inferred['key_outcomes'] = inferred_outcomes
                actions.append(f"Inferred {len(inferred_outcomes)} key outcomes")

        # Add follow-up meeting suggestion
        if self._should_suggest_followup(inferred):
            if 'next_steps' not in inferred:
                inferred['next_steps'] = []
            inferred['next_steps'].append({
                'action': 'Schedule follow-up meeting',
                'timeline': 'Within 2 weeks',
                'purpose': 'Review progress on action items'
            })
            actions.append("Added follow-up meeting suggestion")

        return inferred, actions

    def _extract_assignee_from_text(self, text: str) -> Optional[str]:
        """Extract assignee name from action text"""
        for pattern in self.completion_patterns['responsibility_patterns']:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(1).strip().title()
        return None

    def _extract_deadline_from_text(self, text: str) -> Optional[str]:
        """Extract deadline from action text"""
        for pattern in self.completion_patterns['time_patterns']:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(0).strip()
        return None

    def _improve_action_task_text(self, task: str) -> str:
        """Improve action task text format"""
        task = task.strip()
        if not task:
            return task

        # Add action verb if missing
        action_verbs = self.completion_patterns['action_verbs']
        if not any(task.lower().startswith(verb) for verb in action_verbs):
            # Try to identify appropriate verb based on content
            if any(word in task.lower() for word in ['report', 'document', 'write']):
                task = f"Prepare {task.lower()}"
            elif any(word in task.lower() for word in ['call', 'contact', 'reach']):
                task = f"Contact {task.lower()}"
            elif any(word in task.lower() for word in ['check', 'verify', 'confirm']):
                task = f"Review {task.lower()}"
            else:
                task = f"Complete {task.lower()}"

        # Capitalize first letter
        if task:
            task = task[0].upper() + task[1:]

        return task

    def _infer_decision_rationale(self, decision: str, context: Dict[str, Any]) -> Optional[str]:
        """Infer rationale for a decision based on context"""
        # Simple heuristics based on decision content
        if any(word in decision.lower() for word in ['approve', 'accept', 'proceed']):
            return "Based on meeting discussion and analysis"
        elif any(word in decision.lower() for word in ['reject', 'decline', 'cancel']):
            return "Due to identified risks and constraints"
        elif any(word in decision.lower() for word in ['postpone', 'delay', 'defer']):
            return "Pending additional information and resources"
        return None

    def _estimate_meeting_duration(self, agenda: List[Any]) -> Optional[str]:
        """Estimate meeting duration based on agenda"""
        if not agenda:
            return None

        # Simple estimation: 15 minutes per agenda item + 15 minutes buffer
        estimated_minutes = len(agenda) * 15 + 15
        hours = estimated_minutes // 60
        minutes = estimated_minutes % 60

        if hours > 0:
            return f"{hours}h {minutes}m" if minutes > 0 else f"{hours}h"
        else:
            return f"{minutes}m"

    def _infer_key_outcomes(self, data: Dict[str, Any]) -> List[str]:
        """Infer key outcomes from decisions and action items"""
        outcomes = []

        # Add outcomes based on decisions
        if 'decisions' in data:
            decision_count = len([d for d in data['decisions'] if isinstance(d, dict)])
            if decision_count > 0:
                outcomes.append(f"{decision_count} key decision(s) made")

        # Add outcomes based on action items
        if 'action_items' in data:
            action_count = len([a for a in data['action_items'] if isinstance(a, dict)])
            if action_count > 0:
                outcomes.append(f"{action_count} action item(s) assigned")

        return outcomes

    def _should_suggest_followup(self, data: Dict[str, Any]) -> bool:
        """Determine if a follow-up meeting should be suggested"""
        # Suggest follow-up if there are action items or pending decisions
        action_items = data.get('action_items', [])
        pending_actions = len([a for a in action_items if isinstance(a, dict)])

        return pending_actions > 0

    def get_completion_stats(self) -> Dict[str, Any]:
        """Get completion statistics"""
        return {
            'available_default_sections': len(self.default_values),
            'completion_patterns': len(self.completion_patterns),
            'action_verbs': len(self.completion_patterns.get('action_verbs', [])),
            'time_patterns': len(self.completion_patterns.get('time_patterns', [])),
            'responsibility_patterns': len(self.completion_patterns.get('responsibility_patterns', []))
        }