"""
TTS Service
===========

Business logic for TTS generation.
"""

import asyncio
import os
import uuid
from dataclasses import dataclass
from typing import Callable, Optional, List

from api.config import settings


@dataclass
class TTSGenerationParams:
    """Parameters for TTS generation"""
    task_id: str
    text: str
    prompt_audio_path: str
    emo_audio_path: Optional[str] = None
    speech_length: int = 0
    temperature: float = 0.8
    top_p: float = 0.8
    top_k: int = 30
    emo_weight: float = 0.65
    max_text_tokens_per_segment: int = 120
    # Advanced parameters
    do_sample: bool = True
    length_penalty: float = 0.0
    num_beams: int = 3
    repetition_penalty: float = 10.0
    max_mel_tokens: int = 1500
    # Segmentation
    interval_silence: int = 200
    quick_streaming_tokens: int = 0
    verbose: bool = False
    # Emotion
    emo_vector: Optional[List[float]] = None
    use_emo_text: bool = False
    emo_text: Optional[str] = None
    emo_random: bool = False


class TTSService:
    """Service for TTS generation operations"""

    def __init__(self, model, semaphore: asyncio.Semaphore):
        self.model = model
        self.semaphore = semaphore

    async def generate(
        self,
        params: TTSGenerationParams,
        progress_callback: Optional[Callable[[float, str], None]] = None,
    ) -> str:
        """
        Generate speech from text.

        Returns:
            Path to the generated audio file.
        """
        output_path = os.path.join(settings.OUTPUT_DIR, f"{params.task_id}.wav")

        # Setup progress wrapper
        if progress_callback:
            original_callback = self.model.gr_progress
            self.model.gr_progress = type(
                "ProgressWrapper",
                (),
                {
                    "__call__": lambda self, p=None, m=None, **kwargs: progress_callback(p, m)
                },
            )()

        try:
            # Acquire semaphore for concurrency control
            async with self.semaphore:
                # Run generation in thread pool
                await asyncio.to_thread(
                    lambda: next(
                        self.model.infer_generator(
                            spk_audio_prompt=params.prompt_audio_path,
                            text=params.text,
                            output_path=output_path,
                            emo_audio_prompt=params.emo_audio_path,
                            emo_alpha=params.emo_weight,
                            emo_vector=params.emo_vector,
                            use_emo_text=params.use_emo_text,
                            emo_text=params.emo_text,
                            use_random=params.emo_random,
                            verbose=params.verbose,
                            max_text_tokens_per_segment=params.max_text_tokens_per_segment,
                            interval_silence=params.interval_silence,
                            quick_streaming_tokens=params.quick_streaming_tokens,
                            stream_return=False,
                            do_sample=params.do_sample,
                            top_p=params.top_p,
                            top_k=params.top_k,
                            temperature=params.temperature,
                            length_penalty=params.length_penalty,
                            num_beams=params.num_beams,
                            repetition_penalty=params.repetition_penalty,
                            max_mel_tokens=params.max_mel_tokens,
                            speech_length=params.speech_length,
                        )
                    )
                )

            return output_path

        finally:
            # Restore original callback
            if progress_callback:
                self.model.gr_progress = original_callback

    @staticmethod
    async def save_upload_file(content: bytes, prefix: str, extension: str = ".wav") -> str:
        """Save uploaded file content to disk"""
        filename = f"{prefix}_{uuid.uuid4().hex}{extension}"
        filepath = os.path.join(settings.OUTPUT_DIR, filename)

        # Write file asynchronously
        await asyncio.to_thread(
            lambda: open(filepath, "wb").write(content)
        )

        return filepath

    @staticmethod
    def validate_audio_format(filename: str, content_type: str) -> tuple[bool, str]:
        """Validate audio file format"""
        if filename:
            file_ext = os.path.splitext(filename)[1].lower()
            if file_ext and file_ext not in settings.SUPPORTED_AUDIO_FORMATS:
                return False, f"Unsupported format: {file_ext}"

        if content_type and content_type not in settings.SUPPORTED_AUDIO_MIMETYPES:
            print(f"Warning: Unusual MIME type {content_type}")

        return True, ""

    @staticmethod
    def cleanup_temp_files(*paths: str) -> None:
        """Clean up temporary files"""
        for path in paths:
            if path and os.path.exists(path):
                try:
                    os.remove(path)
                except Exception:
                    pass
