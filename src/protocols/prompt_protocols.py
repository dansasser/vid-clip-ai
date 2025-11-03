"""
Prompt Protocol Definitions

Pydantic models that define the structure and validation rules for:
- Prompt inputs (what data each prompt needs)
- Prompt outputs (what data the LLM must return)
- Prompt metadata (versioning, description, etc.)

These protocols ensure type safety and data integrity throughout the prompt system.
"""

from pydantic import BaseModel, Field, field_validator
from typing import List, Dict, Any, Type
import json


# ============================================================================
# OUTPUT SCHEMAS - Define what each agent's LLM should return
# ============================================================================

class TextSegment(BaseModel):
    """A single text segment identified as a potential clip."""
    start_time: float = Field(..., description="Start time of the segment in seconds", ge=0)
    end_time: float = Field(..., description="End time of the segment in seconds", ge=0)
    score: float = Field(..., ge=0.0, le=1.0, description="Relevance score from 0.0 to 1.0")
    reason: str = Field(..., min_length=10, description="Brief explanation for the score")

    @field_validator('end_time')
    @classmethod
    def validate_times(cls, end_time: float, info) -> float:
        """Ensure end_time > start_time."""
        if 'start_time' in info.data and end_time <= info.data['start_time']:
            raise ValueError('end_time must be greater than start_time')
        return end_time


class TextScoringOutput(BaseModel):
    """Output schema for text scoring agent (Gemma)."""
    segments: List[TextSegment] = Field(..., description="List of identified clip segments")

    @field_validator('segments')
    @classmethod
    def validate_segments(cls, segments: List[TextSegment]) -> List[TextSegment]:
        """Ensure at least one segment is returned."""
        if len(segments) == 0:
            raise ValueError('At least one segment must be identified')
        return segments


class VisionScoringOutput(BaseModel):
    """Output schema for vision scoring agent (Qwen2.5-VL local)."""
    vision_score: float = Field(..., ge=0.0, le=1.0, description="Visual salience score")
    key_visual_elements: List[str] = Field(
        ...,
        min_length=1,
        description="Visual elements that contributed to the score"
    )
    emotional_intensity: str = Field(
        ...,
        description="Detected emotional intensity (low/medium/high)"
    )
    reason: str = Field(..., min_length=10, description="Explanation for the score")


class QualityAssuranceOutput(BaseModel):
    """Output schema for quality assurance agent (Qwen3-VL cloud)."""
    confidence_score: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="High-confidence evaluation score"
    )
    recommendation: str = Field(
        ...,
        description="Recommendation: 'accept', 'reject', or 'uncertain'"
    )
    key_factors: List[str] = Field(
        ...,
        min_length=1,
        description="Factors that influenced the decision"
    )
    reason: str = Field(..., min_length=10, description="Detailed explanation")

    @field_validator('recommendation')
    @classmethod
    def validate_recommendation(cls, recommendation: str) -> str:
        """Ensure recommendation is one of the valid values."""
        valid = ['accept', 'reject', 'uncertain']
        if recommendation.lower() not in valid:
            raise ValueError(f"recommendation must be one of {valid}")
        return recommendation.lower()


# ============================================================================
# PROMPT PROTOCOL - Base model for all prompts
# ============================================================================

class Prompt(BaseModel):
    """A validated and structured representation of a prompt."""
    name: str = Field(..., description="Unique identifier for this prompt type")
    version: int = Field(..., ge=1, description="Version number (1, 2, 3...)")
    description: str = Field(..., description="Human-readable description of purpose")
    template: str = Field(..., min_length=50, description="The prompt template text")
    input_variables: List[str] = Field(..., description="Required input variable names")
    output_protocol: Type[BaseModel] = Field(..., description="Pydantic model for output validation")

    class Config:
        arbitrary_types_allowed = True  # Allow Type[BaseModel]

    def format(self, **kwargs) -> str:
        """
        Format the prompt template with validated inputs.

        Args:
            **kwargs: Input variables to substitute into template

        Returns:
            Formatted prompt string

        Raises:
            ValueError: If required input variables are missing
        """
        # Validate all required variables are provided
        missing = [var for var in self.input_variables if var not in kwargs]
        if missing:
            raise ValueError(
                f"Missing required input variables: {missing}. "
                f"Required: {self.input_variables}"
            )

        # Format template
        try:
            return self.template.format(**kwargs)
        except KeyError as e:
            raise ValueError(f"Template formatting error: {e}") from e

    def parse_output(self, output_text: str) -> Dict[str, Any]:
        """
        Parse and validate the LLM's output against the protocol.

        Args:
            output_text: Raw text output from LLM

        Returns:
            Validated and parsed output as dictionary

        Raises:
            ValueError: If output cannot be parsed or validated
        """
        # Clean up common LLM output issues
        cleaned = self._clean_llm_output(output_text)

        # Parse JSON
        try:
            data = json.loads(cleaned)
        except json.JSONDecodeError as e:
            raise ValueError(f"Failed to parse LLM output as JSON: {e}") from e

        # Validate against protocol
        try:
            validated = self.output_protocol.model_validate(data)
            return validated.model_dump()
        except Exception as e:
            raise ValueError(f"LLM output failed validation: {e}") from e

    @staticmethod
    def _clean_llm_output(text: str) -> str:
        """
        Clean common issues in LLM JSON output.

        Args:
            text: Raw LLM output text

        Returns:
            Cleaned JSON string
        """
        # Remove markdown code blocks
        if '```json' in text:
            text = text.split('```json')[1].split('```')[0]
        elif '```' in text:
            text = text.split('```')[1].split('```')[0]

        # Strip whitespace
        text = text.strip()

        return text


# ============================================================================
# PROTOCOL REGISTRY - Maps prompt names to their output protocols
# ============================================================================

PROTOCOL_MAP: Dict[str, Type[BaseModel]] = {
    "text_scoring": TextScoringOutput,
    "vision_scoring": VisionScoringOutput,
    "quality_assurance": QualityAssuranceOutput,
}
