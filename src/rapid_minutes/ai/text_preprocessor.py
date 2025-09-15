"""
Text Preprocessor Module (C1 - AI Processing Layer)
Implements text cleaning and preprocessing for meeting transcripts
Based on 82 Rule principle - core 20% functionality for 80% effectiveness
"""

import re
import logging
from typing import Dict, List, Optional
from dataclasses import dataclass
from datetime import datetime

logger = logging.getLogger(__name__)


@dataclass
class PreprocessedText:
    """Container for preprocessed text data"""
    original_text: str
    cleaned_text: str
    segments: List[str]
    metadata: Dict[str, any]
    preprocessing_stats: Dict[str, int]


class TextPreprocessor:
    """
    Advanced text preprocessor for meeting transcriptions
    Handles noise removal, normalization, and segmentation
    """
    
    def __init__(self):
        """Initialize preprocessor with default settings"""
        self.setup_patterns()
        self.setup_replacements()
    
    def setup_patterns(self):
        """Setup regex patterns for text cleaning"""
        # Common transcription noise patterns
        self.noise_patterns = {
            'filler_words': re.compile(r'\b(um|uh|ah|er|hmm|like|you know|sort of|kind of)\b', re.IGNORECASE),
            'repeated_words': re.compile(r'\b(\w+)\s+\1\b', re.IGNORECASE),
            'transcription_markers': re.compile(r'\[.*?\]|\(.*?\)', re.IGNORECASE),
            'extra_whitespace': re.compile(r'\s{2,}'),
            'speaker_labels': re.compile(r'^(Speaker\s*\d+|[A-Z][a-z]+):\s*', re.MULTILINE),
            'timestamps': re.compile(r'\d{1,2}:\d{2}(?::\d{2})?(?:\s*[AP]M)?'),
            'interruptions': re.compile(r'--+|\.{3,}|…'),
            'false_starts': re.compile(r'\b(\w+)\s+\1?\s*-+\s*(\w+)', re.IGNORECASE)
        }
        
        # Text structure patterns
        self.structure_patterns = {
            'sentence_boundary': re.compile(r'[.!?]+\s+'),
            'paragraph_boundary': re.compile(r'\n\s*\n'),
            'topic_markers': re.compile(r'\b(next|moving on|agenda|topic|item|discussion)\b', re.IGNORECASE),
            'action_markers': re.compile(r'\b(action|task|todo|follow.?up|assign)\b', re.IGNORECASE),
            'decision_markers': re.compile(r'\b(decide|decision|agree|resolved|conclusion)\b', re.IGNORECASE),
            'time_expressions': re.compile(r'\b(?:today|tomorrow|yesterday|next week|last week|\d{1,2}[/-]\d{1,2}(?:[/-]\d{2,4})?)\b', re.IGNORECASE)
        }
        
        # Content extraction patterns
        self.content_patterns = {
            'names': re.compile(r'\b[A-Z][a-z]+ [A-Z][a-z]+\b'),
            'organizations': re.compile(r'\b[A-Z][A-Za-z]*(?:\s+[A-Z][A-Za-z]*)*(?:\s+(?:Inc|Corp|LLC|Ltd)\.?)\b'),
            'email_addresses': re.compile(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'),
            'phone_numbers': re.compile(r'\b(?:\+?1[-.\s]?)?(?:\(?[0-9]{3}\)?[-.\s]?)?[0-9]{3}[-.\s]?[0-9]{4}\b'),
            'dates': re.compile(r'\b\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b|\b(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2}(?:,\s*\d{4})?\b', re.IGNORECASE)
        }
    
    def setup_replacements(self):
        """Setup text replacement rules"""
        self.replacements = {
            # Common transcription errors
            'gonna': 'going to',
            'wanna': 'want to',
            'gotta': 'got to',
            'shoulda': 'should have',
            'coulda': 'could have',
            'wouldve': 'would have',
            # Contractions
            "don't": 'do not',
            "won't": 'will not',
            "can't": 'cannot',
            "isn't": 'is not',
            "aren't": 'are not',
            "wasn't": 'was not',
            "weren't": 'were not',
            "haven't": 'have not',
            "hasn't": 'has not',
            "hadn't": 'had not',
            "shouldn't": 'should not',
            "wouldn't": 'would not',
            "couldn't": 'could not'
        }
    
    async def preprocess(self, text: str, options: Optional[Dict] = None) -> PreprocessedText:
        """
        Main preprocessing method
        
        Args:
            text: Raw meeting transcript text
            options: Optional preprocessing options
            
        Returns:
            PreprocessedText object with cleaned and structured text
        """
        logger.info(f"Starting text preprocessing - length: {len(text)} characters")
        
        options = options or {}
        original_length = len(text)
        
        # Step 1: Initial cleaning
        cleaned_text = await self._initial_cleaning(text)
        
        # Step 2: Remove noise
        cleaned_text = await self._remove_noise(cleaned_text, options)
        
        # Step 3: Normalize text
        cleaned_text = await self._normalize_text(cleaned_text)
        
        # Step 4: Segment text
        segments = await self._segment_text(cleaned_text, options)
        
        # Step 5: Extract metadata
        metadata = await self._extract_metadata(text, cleaned_text)
        
        # Step 6: Generate statistics
        stats = self._generate_stats(text, cleaned_text, segments)
        
        result = PreprocessedText(
            original_text=text,
            cleaned_text=cleaned_text,
            segments=segments,
            metadata=metadata,
            preprocessing_stats=stats
        )
        
        logger.info(f"Preprocessing completed - reduced from {original_length} to {len(cleaned_text)} characters")
        return result
    
    async def _initial_cleaning(self, text: str) -> str:
        """Initial text cleaning - remove obvious noise"""
        # Remove extra whitespace
        text = self.noise_patterns['extra_whitespace'].sub(' ', text)
        
        # Remove transcription markers
        text = self.noise_patterns['transcription_markers'].sub('', text)
        
        # Remove timestamps
        text = self.noise_patterns['timestamps'].sub('', text)
        
        # Clean up line breaks
        text = text.replace('\r\n', '\n').replace('\r', '\n')
        
        return text.strip()
    
    async def _remove_noise(self, text: str, options: Dict) -> str:
        """Remove noise based on options"""
        remove_fillers = options.get('remove_fillers', True)
        remove_repetitions = options.get('remove_repetitions', True)
        remove_speaker_labels = options.get('remove_speaker_labels', False)
        
        if remove_fillers:
            text = self.noise_patterns['filler_words'].sub('', text)
        
        if remove_repetitions:
            # Remove word repetitions
            text = self.noise_patterns['repeated_words'].sub(r'\1', text)
        
        if remove_speaker_labels:
            text = self.noise_patterns['speaker_labels'].sub('', text)
        
        # Clean up interruptions and false starts
        text = self.noise_patterns['interruptions'].sub('.', text)
        text = self.noise_patterns['false_starts'].sub(r'\2', text)
        
        return text
    
    async def _normalize_text(self, text: str) -> str:
        """Normalize text - expand contractions, fix common errors"""
        # Apply replacements
        for old, new in self.replacements.items():
            text = re.sub(r'\b' + re.escape(old) + r'\b', new, text, flags=re.IGNORECASE)
        
        # Normalize punctuation
        text = re.sub(r'[.]{2,}', '.', text)
        text = re.sub(r'[!]{2,}', '!', text)
        text = re.sub(r'[?]{2,}', '?', text)
        
        # Ensure proper sentence spacing
        text = re.sub(r'([.!?])\s*([A-Z])', r'\1 \2', text)
        
        # Clean up extra whitespace again
        text = self.noise_patterns['extra_whitespace'].sub(' ', text)
        
        return text.strip()
    
    async def _segment_text(self, text: str, options: Dict) -> List[str]:
        """Segment text into logical parts"""
        segment_by = options.get('segment_by', 'paragraph')  # paragraph, sentence, topic
        
        if segment_by == 'sentence':
            segments = self.structure_patterns['sentence_boundary'].split(text)
        elif segment_by == 'topic':
            segments = await self._segment_by_topic(text)
        else:  # paragraph
            segments = self.structure_patterns['paragraph_boundary'].split(text)
        
        # Clean and filter segments
        segments = [seg.strip() for seg in segments if seg.strip() and len(seg.strip()) > 10]
        
        return segments
    
    async def _segment_by_topic(self, text: str) -> List[str]:
        """Segment text by topic markers"""
        # Find topic markers
        markers = list(self.structure_patterns['topic_markers'].finditer(text))
        
        if not markers:
            # Fallback to paragraph segmentation
            return self.structure_patterns['paragraph_boundary'].split(text)
        
        segments = []
        start = 0
        
        for marker in markers:
            if start < marker.start():
                segment = text[start:marker.start()].strip()
                if segment:
                    segments.append(segment)
            start = marker.start()
        
        # Add final segment
        if start < len(text):
            final_segment = text[start:].strip()
            if final_segment:
                segments.append(final_segment)
        
        return segments
    
    async def _extract_metadata(self, original_text: str, cleaned_text: str) -> Dict[str, any]:
        """Extract metadata from text"""
        metadata = {
            'processing_timestamp': datetime.utcnow().isoformat(),
            'original_length': len(original_text),
            'cleaned_length': len(cleaned_text),
            'compression_ratio': len(cleaned_text) / len(original_text) if original_text else 0
        }
        
        # Extract entities
        metadata['entities'] = {
            'names': list(set(self.content_patterns['names'].findall(cleaned_text))),
            'organizations': list(set(self.content_patterns['organizations'].findall(cleaned_text))),
            'email_addresses': list(set(self.content_patterns['email_addresses'].findall(cleaned_text))),
            'phone_numbers': list(set(self.content_patterns['phone_numbers'].findall(cleaned_text))),
            'dates': list(set(self.content_patterns['dates'].findall(cleaned_text)))
        }
        
        # Count markers
        metadata['content_markers'] = {
            'topic_markers': len(self.structure_patterns['topic_markers'].findall(cleaned_text)),
            'action_markers': len(self.structure_patterns['action_markers'].findall(cleaned_text)),
            'decision_markers': len(self.structure_patterns['decision_markers'].findall(cleaned_text))
        }
        
        # Text quality metrics
        metadata['quality_metrics'] = await self._calculate_quality_metrics(cleaned_text)
        
        return metadata
    
    async def _calculate_quality_metrics(self, text: str) -> Dict[str, float]:
        """Calculate text quality metrics"""
        words = text.split()
        sentences = self.structure_patterns['sentence_boundary'].split(text)
        
        if not words:
            return {'readability': 0.0, 'coherence': 0.0}
        
        # Basic readability metrics
        avg_word_length = sum(len(word) for word in words) / len(words)
        avg_sentence_length = len(words) / len(sentences) if sentences else 0
        
        # Simple readability score (Flesch-like approximation)
        readability = max(0, min(100, 206.835 - (1.015 * avg_sentence_length) - (84.6 * (avg_word_length / avg_sentence_length)) if avg_sentence_length > 0 else 50))
        
        # Coherence approximation (based on repetition and structure)
        unique_words = set(word.lower() for word in words if word.isalpha())
        coherence = (len(unique_words) / len(words)) * 100 if words else 0
        
        return {
            'readability': round(readability, 2),
            'coherence': round(coherence, 2),
            'avg_word_length': round(avg_word_length, 2),
            'avg_sentence_length': round(avg_sentence_length, 2)
        }
    
    def _generate_stats(self, original: str, cleaned: str, segments: List[str]) -> Dict[str, int]:
        """Generate preprocessing statistics"""
        return {
            'original_chars': len(original),
            'cleaned_chars': len(cleaned),
            'chars_removed': len(original) - len(cleaned),
            'original_words': len(original.split()),
            'cleaned_words': len(cleaned.split()),
            'words_removed': len(original.split()) - len(cleaned.split()),
            'segments_created': len(segments),
            'avg_segment_length': int(sum(len(seg) for seg in segments) / len(segments)) if segments else 0
        }
    
    def validate_preprocessing_quality(self, result: PreprocessedText) -> Dict[str, bool]:
        """Validate the quality of preprocessing"""
        validations = {}
        
        # Check if text was over-cleaned (too much content removed)
        char_reduction = 1 - (result.preprocessing_stats['cleaned_chars'] / result.preprocessing_stats['original_chars'])
        validations['reasonable_reduction'] = 0.1 <= char_reduction <= 0.5
        
        # Check if segments are meaningful
        avg_segment_length = result.preprocessing_stats['avg_segment_length']
        validations['meaningful_segments'] = 50 <= avg_segment_length <= 1000
        
        # Check if essential content is preserved
        validations['content_preserved'] = len(result.cleaned_text.strip()) > 0
        
        # Check metadata extraction
        validations['metadata_extracted'] = bool(result.metadata.get('entities'))
        
        return validations