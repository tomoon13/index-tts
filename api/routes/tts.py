"""
TTS Routes
==========

TTS generation endpoints.
"""

import os
import uuid
from typing import Optional

from fastapi import APIRouter, BackgroundTasks, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from api.config import settings
from api.database import get_session, async_session_maker
from api.dependencies import get_tts_model, get_task_semaphore, get_current_user
from api.models.task import TaskStatus
from api.models.user import User
from api.schemas import GenerateResponse, TaskStatusEnum
from api.services import TaskService, TTSService, UserService
from api.services.tts_service import TTSGenerationParams

router = APIRouter(prefix="/v1/tts", tags=["TTS"])


async def run_tts_generation(
    params: TTSGenerationParams,
    tts_model,
    semaphore,
    user_id: int,
):
    """Background task for TTS generation"""
    async with async_session_maker() as session:
        task_service = TaskService(session)
        user_service = UserService(session)
        tts_service = TTSService(tts_model, semaphore)

        try:
            # Update status to processing
            await task_service.update_task_status(
                params.task_id,
                TaskStatus.PROCESSING,
                message="Starting generation...",
            )
            await session.commit()

            # Progress callback
            async def update_progress(progress: float, message: str):
                await task_service.update_task_status(
                    params.task_id,
                    TaskStatus.PROCESSING,
                    progress=progress,
                    message=message,
                )
                await session.commit()

            # Sync progress callback wrapper
            def progress_callback(progress: float, message: str):
                if params.task_id:
                    # We can't easily await here, so we'll update at the end
                    pass

            # Generate
            output_path = await tts_service.generate(params, progress_callback)

            # Update completed
            await task_service.update_task_status(
                params.task_id,
                TaskStatus.COMPLETED,
                progress=1.0,
                message="Generation completed",
                output_file=output_path,
            )

            # Increment user's generation count
            await user_service.increment_generation_count(user_id)

            await session.commit()

            print(f"✓ Task {params.task_id} completed: {output_path}")

        except Exception as e:
            await task_service.update_task_status(
                params.task_id,
                TaskStatus.FAILED,
                error=str(e),
            )
            await session.commit()
            print(f"✗ Task {params.task_id} failed: {e}")

        finally:
            # Cleanup temp files
            TTSService.cleanup_temp_files(
                params.prompt_audio_path,
                params.emo_audio_path,
            )


@router.post("/generate", response_model=GenerateResponse)
async def generate_speech(
    background_tasks: BackgroundTasks,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
    tts_model=Depends(get_tts_model),
    semaphore=Depends(get_task_semaphore),
    # Required parameters
    text: str = Form(..., description="Text to synthesize"),
    prompt_audio: UploadFile = File(..., description="Speaker prompt audio file"),
    # Optional audio
    emo_audio: Optional[UploadFile] = File(None, description="Emotion reference audio"),
    # Basic parameters
    speech_length: int = Form(0, description="Target speech duration in ms (0 for auto)"),
    temperature: float = Form(0.8, ge=0.1, le=2.0, description="Sampling temperature"),
    top_p: float = Form(0.8, ge=0.0, le=1.0, description="Top-p sampling"),
    top_k: int = Form(30, ge=0, le=100, description="Top-k sampling"),
    emo_weight: float = Form(0.65, ge=0.0, le=1.0, description="Emotion weight"),
    max_text_tokens_per_segment: int = Form(120, ge=20, le=300, description="Max tokens per segment"),
    # Advanced parameters
    do_sample: bool = Form(True, description="Use sampling vs greedy decoding"),
    length_penalty: float = Form(0.0, ge=-2.0, le=2.0, description="Length penalty"),
    num_beams: int = Form(3, ge=1, le=10, description="Beam search beams"),
    repetition_penalty: float = Form(10.0, ge=1.0, le=20.0, description="Repetition penalty"),
    max_mel_tokens: int = Form(1500, ge=100, le=3000, description="Max mel tokens"),
    # Segmentation
    interval_silence: int = Form(200, ge=0, le=2000, description="Silence between segments (ms)"),
    quick_streaming_tokens: int = Form(0, ge=0, le=100, description="Quick streaming tokens"),
    verbose: bool = Form(False, description="Verbose logging"),
    # Emotion control
    emo_mode: str = Form("speaker", description="Emotion mode: speaker, reference, vector, text"),
    emo_text: Optional[str] = Form(None, description="Emotion description text"),
    emo_random: bool = Form(False, description="Random emotion sampling"),
    # Emotion vector (8 dimensions)
    emo_vector_joy: float = Form(0.0, ge=0.0, le=1.0),
    emo_vector_anger: float = Form(0.0, ge=0.0, le=1.0),
    emo_vector_sadness: float = Form(0.0, ge=0.0, le=1.0),
    emo_vector_fear: float = Form(0.0, ge=0.0, le=1.0),
    emo_vector_disgust: float = Form(0.0, ge=0.0, le=1.0),
    emo_vector_melancholy: float = Form(0.0, ge=0.0, le=1.0),
    emo_vector_surprise: float = Form(0.0, ge=0.0, le=1.0),
    emo_vector_calm: float = Form(0.0, ge=0.0, le=1.0),
):
    """
    Generate speech from text with emotion control.

    Creates an asynchronous generation task and returns a task ID.
    Use the status and download endpoints to retrieve results.
    """
    # Log request
    print("\n" + "=" * 60)
    print("📝 Generate Speech Request")
    print("=" * 60)
    print(f"User: {user.id} ({user.email})")
    print(f"Text: {text[:100]}{'...' if len(text) > 100 else ''}")
    print(f"Prompt Audio: {prompt_audio.filename}")
    print(f"Emotion Mode: {emo_mode}")
    print("=" * 60 + "\n")

    # Validate inputs
    if len(text) > settings.MAX_TEXT_LENGTH:
        raise HTTPException(400, f"Text too long (max {settings.MAX_TEXT_LENGTH})")

    if prompt_audio.size > settings.MAX_AUDIO_SIZE:
        raise HTTPException(400, f"Audio too large (max {settings.MAX_AUDIO_SIZE} bytes)")

    # Validate audio format
    is_valid, error_msg = TTSService.validate_audio_format(
        prompt_audio.filename, prompt_audio.content_type
    )
    if not is_valid:
        raise HTTPException(400, error_msg)

    # Validate emotion mode
    valid_modes = ["speaker", "reference", "vector", "text"]
    if emo_mode not in valid_modes:
        raise HTTPException(400, f"Invalid emo_mode. Must be one of: {valid_modes}")

    if emo_mode == "reference" and not emo_audio:
        raise HTTPException(400, "emo_mode='reference' requires emo_audio")

    if emo_mode == "text" and not emo_text:
        raise HTTPException(400, "emo_mode='text' requires emo_text")

    # Generate task ID
    task_id = uuid.uuid4().hex

    # Save uploaded files
    prompt_content = await prompt_audio.read()
    prompt_ext = os.path.splitext(prompt_audio.filename or ".wav")[1]
    prompt_path = await TTSService.save_upload_file(
        prompt_content, f"prompt_{task_id}", prompt_ext
    )

    emo_path = None
    if emo_audio:
        emo_content = await emo_audio.read()
        emo_ext = os.path.splitext(emo_audio.filename or ".wav")[1]
        emo_path = await TTSService.save_upload_file(
            emo_content, f"emo_{task_id}", emo_ext
        )

    # Process emotion parameters
    emo_vector = None
    use_emo_text = False

    if emo_mode == "vector":
        emo_vector = [
            emo_vector_joy, emo_vector_anger, emo_vector_sadness, emo_vector_fear,
            emo_vector_disgust, emo_vector_melancholy, emo_vector_surprise, emo_vector_calm,
        ]
    elif emo_mode == "text":
        use_emo_text = True
        if not emo_text:
            emo_text = text

    # Create task in database
    task_service = TaskService(session)
    await task_service.create_task(
        task_id=task_id,
        input_text=text,
        speech_length=speech_length,
        temperature=temperature,
        top_p=top_p,
        top_k=top_k,
        emo_weight=emo_weight,
        emo_mode=emo_mode,
    )

    # Prepare generation parameters
    params = TTSGenerationParams(
        task_id=task_id,
        text=text,
        prompt_audio_path=prompt_path,
        emo_audio_path=emo_path,
        speech_length=speech_length,
        temperature=temperature,
        top_p=top_p,
        top_k=top_k,
        emo_weight=emo_weight,
        max_text_tokens_per_segment=max_text_tokens_per_segment,
        do_sample=do_sample,
        length_penalty=length_penalty,
        num_beams=num_beams,
        repetition_penalty=repetition_penalty,
        max_mel_tokens=max_mel_tokens,
        interval_silence=interval_silence,
        quick_streaming_tokens=quick_streaming_tokens,
        verbose=verbose,
        emo_vector=emo_vector,
        use_emo_text=use_emo_text,
        emo_text=emo_text,
        emo_random=emo_random,
    )

    # Start background task
    background_tasks.add_task(run_tts_generation, params, tts_model, semaphore, user.id)

    print(f"✓ Task {task_id} created and queued for user {user.id}")

    return GenerateResponse(
        task_id=task_id,
        status=TaskStatusEnum.PENDING,
        message="Task created successfully",
    )
