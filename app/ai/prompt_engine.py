"""
Advanced Meeting Information Extraction Prompt Engine (C3 - AI Processing Layer)
Sophisticated prompt management and optimization for meeting minutes extraction
Implements ICE and 82 Rule principles - intuitive prompts with comprehensive coverage
"""

import logging
from typing import Dict, List, Optional, Any, Union, Tuple
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime
import json
import re

logger = logging.getLogger(__name__)


class PromptType(Enum):
    """Types of extraction prompts"""
    BASIC_INFO = "basic_info"
    ATTENDEES = "attendees"
    AGENDA = "agenda"
    ACTION_ITEMS = "action_items"
    DECISIONS = "decisions"
    KEY_OUTCOMES = "key_outcomes"
    NEXT_MEETING = "next_meeting"
    SUMMARY = "summary"


class PromptComplexity(Enum):
    """Prompt complexity levels"""
    SIMPLE = "simple"
    STANDARD = "standard"
    DETAILED = "detailed"
    EXPERT = "expert"


@dataclass
class PromptTemplate:
    """Prompt template with metadata"""
    template_id: str
    prompt_type: PromptType
    complexity: PromptComplexity
    template: str
    system_message: Optional[str] = None
    max_tokens: Optional[int] = None
    temperature: float = 0.1
    format_instructions: Optional[str] = None
    examples: List[Dict[str, str]] = field(default_factory=list)
    validation_schema: Optional[Dict] = None
    performance_metrics: Dict[str, float] = field(default_factory=dict)
    last_updated: datetime = field(default_factory=datetime.utcnow)


@dataclass
class ExtractionContext:
    """Context for extraction process"""
    text_length: int
    language: str = "english"
    meeting_type: Optional[str] = None
    complexity_level: Optional[str] = None
    quality_hints: List[str] = field(default_factory=list)
    custom_fields: Dict[str, Any] = field(default_factory=dict)


class PromptEngine:
    """
    Advanced prompt engine for meeting information extraction
    Manages prompt templates, optimization, and dynamic prompt generation
    """
    
    def __init__(self):
        """Initialize prompt engine with templates"""
        self.templates: Dict[str, PromptTemplate] = {}
        self.prompt_history: List[Dict[str, Any]] = []
        self.performance_data: Dict[str, Dict[str, float]] = {}
        
        self._initialize_templates()
        logger.info("🎯 Advanced Prompt Engine initialized")
    
    def _initialize_templates(self):
        """Initialize all prompt templates"""
        # Basic meeting information extraction
        self._add_basic_info_templates()
        self._add_attendees_templates()
        self._add_agenda_templates()
        self._add_action_items_templates()
        self._add_decisions_templates()
        self._add_outcomes_templates()
        self._add_summary_templates()
    
    def _add_basic_info_templates(self):
        """Add basic information extraction templates"""
        # Simple template
        simple_basic = PromptTemplate(
            template_id="basic_info_simple",
            prompt_type=PromptType.BASIC_INFO,
            complexity=PromptComplexity.SIMPLE,
            system_message="You are a meeting minutes analyzer. Extract basic meeting information.",
            template="""Extract basic meeting information from this text and return as JSON:

Required fields:
- title: meeting title
- date: date in YYYY-MM-DD format
- time: meeting time
- location: meeting location
- organizer: meeting organizer

Text: {text}

Return only JSON:""",
            temperature=0.1,
            max_tokens=500
        )
        
        # Detailed template
        detailed_basic = PromptTemplate(
            template_id="basic_info_detailed",
            prompt_type=PromptType.BASIC_INFO,
            complexity=PromptComplexity.DETAILED,
            system_message="You are an expert meeting analyst. Extract comprehensive meeting metadata.",
            template="""Analyze this meeting transcript and extract detailed basic information.

Please identify and return as JSON:
{{
    "title": "exact meeting title or main subject",
    "date": "meeting date in YYYY-MM-DD format",
    "time": "start time (include timezone if mentioned)",
    "duration": "meeting duration (if mentioned)",
    "location": "physical location or virtual platform",
    "meeting_type": "type of meeting (e.g., standup, planning, review)",
    "organizer": "meeting organizer/chairperson",
    "project": "associated project or initiative",
    "department": "department or team involved",
    "urgency": "urgency level if indicated",
    "confidentiality": "confidentiality level if mentioned"
}}

Instructions:
- Use null for missing information
- Be precise with date and time formats
- Identify implicit information from context
- Look for formal meeting structures

Meeting Text:
{text}

JSON Response:""",
            temperature=0.05,
            max_tokens=800,
            examples=[
                {
                    "input": "Project Alpha Weekly Standup - March 15, 2024, 9:00 AM PST",
                    "output": '{"title": "Project Alpha Weekly Standup", "date": "2024-03-15", "time": "9:00 AM PST", "meeting_type": "standup"}'
                }
            ]
        )
        
        self.templates["basic_info_simple"] = simple_basic
        self.templates["basic_info_detailed"] = detailed_basic
    
    def _add_attendees_templates(self):
        """Add attendee extraction templates"""
        standard_attendees = PromptTemplate(
            template_id="attendees_standard",
            prompt_type=PromptType.ATTENDEES,
            complexity=PromptComplexity.STANDARD,
            system_message="You are an expert at identifying meeting participants from transcripts.",
            template="""Extract all meeting attendees from this text and return as JSON array.

For each attendee, identify:
- name: full name
- role: job title or role in meeting
- organization: company or department
- present: true/false (assume true unless stated otherwise)
- email: email address if mentioned

Look for:
- Direct introductions ("I'm John from Marketing")
- Speaking patterns and names
- Participant lists
- Email signatures
- Role indicators

Text: {text}

Return JSON array:
[
    {{
        "name": "John Smith",
        "role": "Project Manager", 
        "organization": "Product Team",
        "present": true,
        "email": null
    }}
]

JSON Response:""",
            temperature=0.1,
            max_tokens=1000
        )
        
        self.templates["attendees_standard"] = standard_attendees
    
    def _add_agenda_templates(self):
        """Add agenda/discussion extraction templates"""
        detailed_agenda = PromptTemplate(
            template_id="agenda_detailed",
            prompt_type=PromptType.AGENDA,
            complexity=PromptComplexity.DETAILED,
            system_message="You are an expert at structuring meeting discussions into agenda items.",
            template="""Analyze this meeting text and extract discussion topics/agenda items.

For each topic, identify:
- title: clear topic title
- description: brief description of discussion
- presenter: who led the discussion
- duration: time spent (if mentioned)
- key_points: main discussion points
- status: current status if applicable
- priority: importance level if indicated

Look for:
- Topic transitions ("Next item...", "Moving on to...", "Let's discuss...")
- Subject headers
- Discussion themes
- Time allocations
- Presenter changes

Text: {text}

Return JSON array:
[
    {{
        "title": "Budget Review Q1",
        "description": "Discussion of Q1 budget performance",
        "presenter": "Sarah Johnson",
        "duration": "15 minutes",
        "key_points": ["Revenue up 12%", "Expenses within budget", "Forecast adjustment needed"],
        "status": "ongoing",
        "priority": "high"
    }}
]

JSON Response:""",
            temperature=0.15,
            max_tokens=1500
        )
        
        self.templates["agenda_detailed"] = detailed_agenda
    
    def _add_action_items_templates(self):
        """Add action items extraction templates"""
        expert_actions = PromptTemplate(
            template_id="action_items_expert",
            prompt_type=PromptType.ACTION_ITEMS,
            complexity=PromptComplexity.EXPERT,
            system_message="You are an expert project manager extracting actionable tasks from meetings.",
            template="""Extract all action items and tasks from this meeting transcript.

For each action item, identify:
- task: clear description of what needs to be done
- assignee: person responsible
- due_date: deadline in YYYY-MM-DD format
- priority: high/medium/low
- status: new/in_progress/completed
- dependencies: related tasks or blockers
- success_criteria: how to measure completion
- category: type of task (development, research, communication, etc.)

Look for action indicators:
- "Action item:", "TODO:", "Next steps:"
- "Will do", "I'll handle", "Assigned to"
- "By [date]", "Due [date]", "Deadline"
- "Follow up", "Check with", "Schedule"
- Commitments and promises

Text: {text}

Return JSON array:
[
    {{
        "task": "Review and approve marketing budget proposal",
        "assignee": "Mike Chen",
        "due_date": "2024-03-20",
        "priority": "high",
        "status": "new",
        "dependencies": ["Budget analysis completion"],
        "success_criteria": "Approved budget document",
        "category": "approval"
    }}
]

JSON Response:""",
            temperature=0.1,
            max_tokens=2000
        )
        
        self.templates["action_items_expert"] = expert_actions
    
    def _add_decisions_templates(self):
        """Add decisions extraction templates"""
        standard_decisions = PromptTemplate(
            template_id="decisions_standard",
            prompt_type=PromptType.DECISIONS,
            complexity=PromptComplexity.STANDARD,
            system_message="You are an expert at identifying decisions made in meetings.",
            template="""Extract all decisions made during this meeting.

For each decision, identify:
- decision: what was decided
- rationale: reasoning behind the decision
- impact: expected effects or consequences
- responsible_party: who will implement
- implementation_date: when it takes effect
- alternatives_considered: other options discussed
- vote_count: if there was a vote

Look for decision indicators:
- "We decided", "It was agreed", "The decision is"
- "We will", "Going forward", "From now on"
- "Approved", "Rejected", "Postponed"
- Consensus language
- Final resolutions

Text: {text}

Return JSON array:
[
    {{
        "decision": "Implement new CRM system by Q2",
        "rationale": "Current system lacks needed features",
        "impact": "Improved customer tracking and analytics",
        "responsible_party": "IT Team",
        "implementation_date": "2024-06-01",
        "alternatives_considered": ["Upgrade existing system", "Build custom solution"]
    }}
]

JSON Response:""",
            temperature=0.1,
            max_tokens=1500
        )
        
        self.templates["decisions_standard"] = standard_decisions
    
    def _add_outcomes_templates(self):
        """Add key outcomes extraction templates"""
        detailed_outcomes = PromptTemplate(
            template_id="outcomes_detailed",
            prompt_type=PromptType.KEY_OUTCOMES,
            complexity=PromptComplexity.DETAILED,
            system_message="You are an expert at summarizing key meeting outcomes and takeaways.",
            template="""Extract the most important outcomes and takeaways from this meeting.

Identify:
- Key conclusions reached
- Important insights shared
- Strategic alignments
- Problem resolutions
- New opportunities identified
- Risks or concerns raised
- Success metrics established
- Process improvements agreed upon

Focus on:
- Results that will drive action
- Insights that change understanding
- Agreements that resolve issues
- New directions or priorities

Return as a JSON array of strings, ordered by importance:

Text: {text}

Return JSON array:
[
    "Key outcome or takeaway 1",
    "Key outcome or takeaway 2"
]

JSON Response:""",
            temperature=0.15,
            max_tokens=800
        )
        
        self.templates["outcomes_detailed"] = detailed_outcomes
    
    def _add_summary_templates(self):
        """Add meeting summary templates"""
        executive_summary = PromptTemplate(
            template_id="summary_executive",
            prompt_type=PromptType.SUMMARY,
            complexity=PromptComplexity.EXPERT,
            system_message="You are an executive assistant creating concise meeting summaries for leadership.",
            template="""Create an executive summary of this meeting.

Structure:
{{
    "executive_summary": "2-3 sentence high-level summary",
    "key_decisions": ["decision 1", "decision 2"],
    "critical_actions": ["action 1", "action 2"],
    "next_steps": "What happens next",
    "escalations": ["items needing leadership attention"],
    "risks": ["potential risks or blockers identified"],
    "recommendations": ["strategic recommendations"]
}}

Focus on:
- Information executives need to know
- Items requiring leadership attention
- Strategic implications
- Resource requirements
- Risk factors

Text: {text}

JSON Response:""",
            temperature=0.1,
            max_tokens=1000
        )
        
        self.templates["summary_executive"] = executive_summary
    
    async def get_optimal_prompt(
        self,
        prompt_type: PromptType,
        context: ExtractionContext,
        performance_target: Optional[str] = None
    ) -> PromptTemplate:
        """
        Get optimal prompt template based on context and performance requirements
        
        Args:
            prompt_type: Type of information to extract
            context: Extraction context with hints
            performance_target: Target metric (accuracy, speed, detail)
            
        Returns:
            Optimal PromptTemplate for the task
        """
        # Filter templates by type
        type_templates = [
            template for template in self.templates.values()
            if template.prompt_type == prompt_type
        ]
        
        if not type_templates:
            raise ValueError(f"No templates found for prompt type: {prompt_type}")
        
        # Select based on context complexity
        optimal_complexity = self._determine_optimal_complexity(context)
        
        # Find best matching template
        best_template = None
        best_score = -1
        
        for template in type_templates:
            score = self._score_template(template, context, optimal_complexity, performance_target)
            if score > best_score:
                best_score = score
                best_template = template
        
        logger.debug(f"🎯 Selected template: {best_template.template_id} (score: {best_score:.2f})")
        return best_template
    
    def _determine_optimal_complexity(self, context: ExtractionContext) -> PromptComplexity:
        """Determine optimal prompt complexity based on context"""
        # Simple heuristics for complexity selection
        if context.text_length < 1000:
            return PromptComplexity.SIMPLE
        elif context.text_length < 5000:
            return PromptComplexity.STANDARD
        elif context.text_length < 15000:
            return PromptComplexity.DETAILED
        else:
            return PromptComplexity.EXPERT
    
    def _score_template(
        self,
        template: PromptTemplate,
        context: ExtractionContext,
        target_complexity: PromptComplexity,
        performance_target: Optional[str]
    ) -> float:
        """Score template suitability for given context"""
        score = 0.0
        
        # Complexity match score (40% weight)
        complexity_scores = {
            PromptComplexity.SIMPLE: 1,
            PromptComplexity.STANDARD: 2,
            PromptComplexity.DETAILED: 3,
            PromptComplexity.EXPERT: 4
        }
        
        template_complexity = complexity_scores[template.complexity]
        target_complexity_score = complexity_scores[target_complexity]
        
        complexity_diff = abs(template_complexity - target_complexity_score)
        complexity_score = max(0, 4 - complexity_diff) / 4 * 40
        score += complexity_score
        
        # Performance history score (30% weight)
        if template.template_id in self.performance_data:
            perf_data = self.performance_data[template.template_id]
            
            if performance_target and performance_target in perf_data:
                performance_score = perf_data[performance_target] / 100 * 30
            else:
                # Default to accuracy if no specific target
                performance_score = perf_data.get('accuracy', 75) / 100 * 30
            
            score += performance_score
        else:
            # No history, give moderate score
            score += 20
        
        # Context compatibility score (20% weight)
        context_score = 0
        
        # Language compatibility
        if context.language.lower() == "english":
            context_score += 10
        
        # Meeting type compatibility
        if context.meeting_type and "standup" in template.template.lower():
            if "standup" in context.meeting_type.lower():
                context_score += 5
        
        # Quality hints compatibility
        if context.quality_hints:
            for hint in context.quality_hints:
                if hint.lower() in template.template.lower():
                    context_score += 2
        
        score += min(context_score, 20)
        
        # Recency score (10% weight)
        days_old = (datetime.utcnow() - template.last_updated).days
        recency_score = max(0, 10 - days_old / 30 * 10)
        score += recency_score
        
        return score
    
    async def customize_prompt(
        self,
        template: PromptTemplate,
        text: str,
        context: ExtractionContext,
        custom_instructions: Optional[str] = None
    ) -> Tuple[str, str]:
        """
        Customize prompt template for specific text and context
        
        Args:
            template: Base prompt template
            text: Text to process
            context: Extraction context
            custom_instructions: Additional instructions
            
        Returns:
            Tuple of (customized_prompt, system_message)
        """
        # Start with base template
        prompt = template.template
        system_message = template.system_message or ""
        
        # Text length optimization
        optimized_text = await self._optimize_text_for_prompt(text, template, context)
        
        # Replace template variables
        prompt = prompt.format(text=optimized_text)
        
        # Add custom instructions
        if custom_instructions:
            prompt += f"\n\nAdditional Instructions:\n{custom_instructions}"
        
        # Add context-specific enhancements
        if context.meeting_type:
            prompt += f"\n\nNote: This is a {context.meeting_type} meeting."
        
        if context.quality_hints:
            hints = ", ".join(context.quality_hints)
            prompt += f"\n\nQuality hints: {hints}"
        
        # Add examples if available and helpful
        if template.examples and template.complexity != PromptComplexity.SIMPLE:
            examples_text = self._format_examples(template.examples)
            prompt = prompt.replace("JSON Response:", f"{examples_text}\n\nJSON Response:")
        
        logger.debug(f"📝 Customized prompt for {template.template_id}")
        return prompt, system_message
    
    async def _optimize_text_for_prompt(
        self,
        text: str,
        template: PromptTemplate,
        context: ExtractionContext
    ) -> str:
        """Optimize text length and content for prompt"""
        max_chars = 8000  # Conservative limit for most LLMs
        
        if len(text) <= max_chars:
            return text
        
        # Intelligent truncation based on prompt type
        if template.prompt_type == PromptType.BASIC_INFO:
            # For basic info, prioritize beginning of text
            return text[:max_chars]
        
        elif template.prompt_type == PromptType.ACTION_ITEMS:
            # For action items, prioritize end of text where conclusions typically are
            return text[-max_chars:]
        
        elif template.prompt_type == PromptType.SUMMARY:
            # For summary, use beginning and end
            half_chars = max_chars // 2
            return text[:half_chars] + "\n...\n" + text[-half_chars:]
        
        else:
            # Default: use middle section which often contains main discussion
            start_idx = max(0, (len(text) - max_chars) // 2)
            return text[start_idx:start_idx + max_chars]
    
    def _format_examples(self, examples: List[Dict[str, str]]) -> str:
        """Format examples for inclusion in prompt"""
        if not examples:
            return ""
        
        formatted = "\nExamples:\n"
        for i, example in enumerate(examples[:2], 1):  # Limit to 2 examples
            formatted += f"\nExample {i}:\n"
            formatted += f"Input: {example['input']}\n"
            formatted += f"Output: {example['output']}\n"
        
        return formatted
    
    def record_performance(
        self,
        template_id: str,
        metrics: Dict[str, float],
        feedback: Optional[Dict[str, Any]] = None
    ):
        """Record performance metrics for template optimization"""
        if template_id not in self.performance_data:
            self.performance_data[template_id] = {}
        
        # Update metrics with exponential moving average
        alpha = 0.3
        for metric, value in metrics.items():
            if metric in self.performance_data[template_id]:
                old_value = self.performance_data[template_id][metric]
                self.performance_data[template_id][metric] = alpha * value + (1 - alpha) * old_value
            else:
                self.performance_data[template_id][metric] = value
        
        # Store in history
        self.prompt_history.append({
            'template_id': template_id,
            'metrics': metrics,
            'feedback': feedback,
            'timestamp': datetime.utcnow().isoformat()
        })
        
        # Keep only recent history
        if len(self.prompt_history) > 1000:
            self.prompt_history = self.prompt_history[-1000:]
        
        logger.debug(f"📊 Recorded performance for template: {template_id}")
    
    def get_template_performance_report(self) -> Dict[str, Any]:
        """Get comprehensive performance report for all templates"""
        report = {
            'templates': {},
            'overall_metrics': {},
            'recommendations': []
        }
        
        # Template-specific metrics
        for template_id, template in self.templates.items():
            perf_data = self.performance_data.get(template_id, {})
            
            report['templates'][template_id] = {
                'prompt_type': template.prompt_type.value,
                'complexity': template.complexity.value,
                'usage_count': sum(1 for h in self.prompt_history if h['template_id'] == template_id),
                'performance_metrics': perf_data,
                'last_updated': template.last_updated.isoformat()
            }
        
        # Overall metrics
        if self.performance_data:
            all_accuracies = []
            all_speeds = []
            
            for metrics in self.performance_data.values():
                if 'accuracy' in metrics:
                    all_accuracies.append(metrics['accuracy'])
                if 'speed' in metrics:
                    all_speeds.append(metrics['speed'])
            
            if all_accuracies:
                report['overall_metrics']['avg_accuracy'] = sum(all_accuracies) / len(all_accuracies)
            if all_speeds:
                report['overall_metrics']['avg_speed'] = sum(all_speeds) / len(all_speeds)
        
        # Generate recommendations
        report['recommendations'] = self._generate_optimization_recommendations()
        
        return report
    
    def _generate_optimization_recommendations(self) -> List[str]:
        """Generate recommendations for prompt optimization"""
        recommendations = []
        
        # Check for low-performing templates
        for template_id, metrics in self.performance_data.items():
            if metrics.get('accuracy', 100) < 70:
                recommendations.append(f"Template {template_id} has low accuracy ({metrics['accuracy']:.1f}%) - consider revision")
        
        # Check for unused templates
        used_templates = set(h['template_id'] for h in self.prompt_history[-100:])  # Recent usage
        all_templates = set(self.templates.keys())
        unused = all_templates - used_templates
        
        if unused:
            recommendations.append(f"Consider reviewing unused templates: {', '.join(unused)}")
        
        return recommendations
    
    def add_custom_template(
        self,
        template_id: str,
        prompt_type: PromptType,
        template: str,
        complexity: PromptComplexity = PromptComplexity.STANDARD,
        **kwargs
    ) -> bool:
        """Add custom prompt template"""
        if template_id in self.templates:
            logger.warning(f"Template {template_id} already exists, will be overwritten")
        
        custom_template = PromptTemplate(
            template_id=template_id,
            prompt_type=prompt_type,
            complexity=complexity,
            template=template,
            **kwargs
        )
        
        self.templates[template_id] = custom_template
        logger.info(f"➕ Added custom template: {template_id}")
        return True
    
    def get_available_templates(self, prompt_type: Optional[PromptType] = None) -> List[Dict[str, Any]]:
        """Get list of available templates"""
        templates = self.templates.values()
        
        if prompt_type:
            templates = [t for t in templates if t.prompt_type == prompt_type]
        
        return [
            {
                'template_id': t.template_id,
                'prompt_type': t.prompt_type.value,
                'complexity': t.complexity.value,
                'performance': self.performance_data.get(t.template_id, {}),
                'last_updated': t.last_updated.isoformat()
            }
            for t in templates
        ]


# Global prompt engine instance
prompt_engine = PromptEngine()