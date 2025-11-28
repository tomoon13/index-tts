"""
TTS Schemas
===========

Pydantic schemas for TTS generation parameters.
"""

from typing import List, Optional

from pydantic import BaseModel, Field


class TTSGenerateRequest(BaseModel):
    """TTS generation request parameters (for documentation)"""

    text: str = Field(..., description="Text to synthesize", max_length=500)
    speech_length: int = Field(
        default=0,
        ge=0,
        description="Target speech duration in milliseconds (0 for auto)",
    )
    temperature: float = Field(
        default=0.8,
        ge=0.1,
        le=2.0,
        description="Sampling temperature",
    )
    top_p: float = Field(
        default=0.8,
        ge=0.0,
        le=1.0,
        description="Top-p sampling",
    )
    top_k: int = Field(
        default=30,
        ge=0,
        le=100,
        description="Top-k sampling",
    )
    emo_weight: float = Field(
        default=0.65,
        ge=0.0,
        le=1.0,
        description="Emotion weight/alpha",
    )
    max_text_tokens_per_segment: int = Field(
        default=120,
        ge=20,
        le=300,
        description="Max tokens per segment",
    )

    # Advanced generation parameters
    do_sample: bool = Field(
        default=True,
        description="Use sampling (True) or greedy decoding (False)",
    )
    length_penalty: float = Field(
        default=0.0,
        ge=-2.0,
        le=2.0,
        description="Length penalty for beam search",
    )
    num_beams: int = Field(
        default=3,
        ge=1,
        le=10,
        description="Number of beams for beam search",
    )
    repetition_penalty: float = Field(
        default=10.0,
        ge=1.0,
        le=20.0,
        description="Penalty for repeating tokens",
    )
    max_mel_tokens: int = Field(
        default=1500,
        ge=100,
        le=3000,
        description="Maximum mel tokens per segment",
    )

    # Segmentation parameters
    interval_silence: int = Field(
        default=200,
        ge=0,
        le=2000,
        description="Silence duration between segments in ms",
    )
    quick_streaming_tokens: int = Field(
        default=0,
        ge=0,
        le=100,
        description="Tokens for quick streaming mode",
    )
    verbose: bool = Field(
        default=False,
        description="Enable verbose logging",
    )

    # Emotion control
    emo_mode: str = Field(
        default="speaker",
        description="Emotion control mode: speaker, reference, vector, text",
    )
    emo_text: Optional[str] = Field(
        default=None,
        description="Emotion description text (for mode=text)",
    )
    emo_random: bool = Field(
        default=False,
        description="Use random emotion sampling",
    )


class EmotionVector(BaseModel):
    """8-dimensional emotion vector"""
    joy: float = Field(default=0.0, ge=0.0, le=1.0, description="喜 (Joy)")
    anger: float = Field(default=0.0, ge=0.0, le=1.0, description="怒 (Anger)")
    sadness: float = Field(default=0.0, ge=0.0, le=1.0, description="哀 (Sadness)")
    fear: float = Field(default=0.0, ge=0.0, le=1.0, description="懼 (Fear)")
    disgust: float = Field(default=0.0, ge=0.0, le=1.0, description="厭惡 (Disgust)")
    melancholy: float = Field(default=0.0, ge=0.0, le=1.0, description="低落 (Melancholy)")
    surprise: float = Field(default=0.0, ge=0.0, le=1.0, description="驚喜 (Surprise)")
    calm: float = Field(default=0.0, ge=0.0, le=1.0, description="平靜 (Calm)")

    def to_list(self) -> List[float]:
        """Convert to list format for TTS model"""
        return [
            self.joy,
            self.anger,
            self.sadness,
            self.fear,
            self.disgust,
            self.melancholy,
            self.surprise,
            self.calm,
        ]
