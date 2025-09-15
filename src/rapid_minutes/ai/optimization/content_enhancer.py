"""
Content Enhancement Specialist
Single Responsibility: Text content quality improvement and enhancement
"""

import logging
import re
from typing import Dict, List, Tuple, Optional, Any


logger = logging.getLogger(__name__)


class ContentEnhancer:
    """
    Specialized class for content enhancement operations
    Follows SRP - only handles text content improvements
    """

    def __init__(self):
        self.enhancement_patterns = self._initialize_patterns()

    def _initialize_patterns(self) -> Dict[str, Any]:
        """Initialize text enhancement patterns"""
        return {
            'grammar_fixes': [
                (r'\s+', ' '),  # Multiple spaces to single
                (r'([.!?])\s*([a-z])', r'\1 \2'),  # Space after sentence end
                (r'\s+([.!?,:;])', r'\1'),  # Remove space before punctuation
            ],
            'formatting_fixes': [
                (r'([a-z])([A-Z])', r'\1 \2'),  # camelCase to normal
                (r'-\s*\n\s*', ''),  # Remove hyphenated line breaks
            ],
            'quality_improvements': [
                (r'\b(gonna|wanna|gotta)\b', lambda m: {
                    'gonna': 'going to',
                    'wanna': 'want to',
                    'gotta': 'have to'
                }.get(m.group(1).lower(), m.group(1))),
            ]
        }

    async def enhance_text_content(
        self,
        content: str,
        enhancement_type: str = "general",
        context: Optional[Dict[str, Any]] = None
    ) -> Tuple[str, List[str]]:
        """
        Enhance text content quality

        Args:
            content: Text to enhance
            enhancement_type: Type of enhancement (general, meeting, action, decision)
            context: Additional context for enhancement

        Returns:
            Tuple of (enhanced_text, improvements_made)
        """
        if not content or not isinstance(content, str):
            return content or "", []

        improvements = []
        enhanced_content = content

        try:
            # Apply basic grammar and formatting fixes
            enhanced_content, grammar_improvements = self._apply_grammar_fixes(enhanced_content)
            improvements.extend(grammar_improvements)

            # Apply context-specific enhancements
            if enhancement_type == "meeting":
                enhanced_content, meeting_improvements = await self._enhance_meeting_text(
                    enhanced_content, context
                )
                improvements.extend(meeting_improvements)
            elif enhancement_type == "action":
                enhanced_content, action_improvements = await self._enhance_action_item_text(
                    enhanced_content, context
                )
                improvements.extend(action_improvements)
            elif enhancement_type == "decision":
                enhanced_content, decision_improvements = await self._enhance_decision_text(
                    enhanced_content, context
                )
                improvements.extend(decision_improvements)

            # Apply general quality improvements
            enhanced_content, quality_improvements = self._improve_text_quality(enhanced_content)
            improvements.extend(quality_improvements)

            logger.debug(f"Content enhanced: {len(improvements)} improvements made")
            return enhanced_content, improvements

        except Exception as e:
            logger.error(f"Content enhancement failed: {e}")
            return content, []

    def _apply_grammar_fixes(self, text: str) -> Tuple[str, List[str]]:
        """Apply basic grammar and formatting fixes"""
        improvements = []
        fixed_text = text

        for pattern, replacement in self.enhancement_patterns['grammar_fixes']:
            if re.search(pattern, fixed_text):
                fixed_text = re.sub(pattern, replacement, fixed_text)
                improvements.append(f"Applied grammar fix: {pattern}")

        for pattern, replacement in self.enhancement_patterns['formatting_fixes']:
            if re.search(pattern, fixed_text):
                fixed_text = re.sub(pattern, replacement, fixed_text)
                improvements.append(f"Applied formatting fix: {pattern}")

        return fixed_text, improvements

    async def _enhance_meeting_text(
        self,
        text: str,
        context: Optional[Dict[str, Any]] = None
    ) -> Tuple[str, List[str]]:
        """Enhance meeting-specific text content"""
        improvements = []
        enhanced_text = text

        # Standardize meeting terminology
        meeting_terms = {
            r'\bmtg\b': 'meeting',
            r'\bppl\b': 'people',
            r'\bfyi\b': 'for your information',
            r'\btbd\b': 'to be determined',
            r'\basap\b': 'as soon as possible'
        }

        for pattern, replacement in meeting_terms.items():
            if re.search(pattern, enhanced_text, re.IGNORECASE):
                enhanced_text = re.sub(pattern, replacement, enhanced_text, flags=re.IGNORECASE)
                improvements.append(f"Expanded abbreviation: {pattern} -> {replacement}")

        # Improve sentence structure for meeting context
        if len(enhanced_text.split()) < 5:
            enhanced_text = f"Meeting discussion: {enhanced_text}"
            improvements.append("Added meeting context prefix")

        return enhanced_text, improvements

    async def _enhance_action_item_text(
        self,
        text: str,
        context: Optional[Dict[str, Any]] = None
    ) -> Tuple[str, List[str]]:
        """Enhance action item text content"""
        improvements = []
        enhanced_text = text

        # Ensure action items start with action verbs
        action_verbs = ['review', 'complete', 'follow up', 'prepare', 'schedule', 'contact']

        if not any(enhanced_text.lower().startswith(verb) for verb in action_verbs):
            # Try to identify and move action verb to front
            for verb in action_verbs:
                if verb in enhanced_text.lower():
                    enhanced_text = f"{verb.title()} {enhanced_text.replace(verb, '').strip()}"
                    improvements.append(f"Restructured to start with action verb: {verb}")
                    break

        # Add time context if missing
        time_indicators = ['by', 'before', 'within', 'deadline', 'due']
        if not any(indicator in enhanced_text.lower() for indicator in time_indicators):
            if context and context.get('default_deadline'):
                enhanced_text += f" by {context['default_deadline']}"
                improvements.append("Added deadline context")

        return enhanced_text, improvements

    async def _enhance_decision_text(
        self,
        text: str,
        context: Optional[Dict[str, Any]] = None
    ) -> Tuple[str, List[str]]:
        """Enhance decision text content"""
        improvements = []
        enhanced_text = text

        # Ensure decisions are clearly stated
        decision_prefixes = ['decided to', 'agreed to', 'approved', 'rejected', 'postponed']

        if not any(enhanced_text.lower().startswith(prefix) for prefix in decision_prefixes):
            enhanced_text = f"Decided to {enhanced_text.lower()}"
            improvements.append("Added decision clarity prefix")

        # Improve decision structure
        if '?' in enhanced_text:
            enhanced_text = enhanced_text.replace('?', '.')
            improvements.append("Converted question format to decision statement")

        return enhanced_text, improvements

    def _improve_text_quality(self, text: str) -> Tuple[str, List[str]]:
        """Apply general text quality improvements"""
        improvements = []
        improved_text = text

        # Apply quality improvement patterns
        for pattern, replacement in self.enhancement_patterns['quality_improvements']:
            if re.search(pattern, improved_text):
                if callable(replacement):
                    improved_text = re.sub(pattern, replacement, improved_text)
                else:
                    improved_text = re.sub(pattern, replacement, improved_text)
                improvements.append(f"Applied quality improvement: {pattern}")

        # Remove excessive punctuation
        if re.search(r'[.!?]{2,}', improved_text):
            improved_text = re.sub(r'[.!?]{2,}', '.', improved_text)
            improvements.append("Cleaned excessive punctuation")

        # Capitalize sentences
        sentences = improved_text.split('. ')
        capitalized_sentences = []
        for sentence in sentences:
            if sentence and sentence[0].islower():
                sentence = sentence[0].upper() + sentence[1:]
                improvements.append("Capitalized sentence start")
            capitalized_sentences.append(sentence)
        improved_text = '. '.join(capitalized_sentences)

        return improved_text, improvements

    def get_enhancement_stats(self) -> Dict[str, Any]:
        """Get enhancement statistics"""
        return {
            'available_patterns': len(self.enhancement_patterns),
            'grammar_rules': len(self.enhancement_patterns.get('grammar_fixes', [])),
            'formatting_rules': len(self.enhancement_patterns.get('formatting_fixes', [])),
            'quality_rules': len(self.enhancement_patterns.get('quality_improvements', []))
        }