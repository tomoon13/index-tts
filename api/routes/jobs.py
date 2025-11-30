"""
TTS Jobs Routes
===============

Unified TTS job management endpoints following REST best practices.
Implements HTTP 202 Accepted pattern for long-running tasks.
"""

import os
import uuid
from datetime import datetime, timezone
from math import ceil
from typing import Optional

from fastapi import APIRouter, BackgroundTasks, Depends, File, Form, HTTPException, Query, UploadFile
from fastapi.responses import FileResponse, JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from api.config import settings
from api.database import get_session, async_session_maker
from api.dependencies import get_tts_model, get_task_semaphore, get_current_user
from api.models.task import TaskStatus
from api.models.user import User
from api.schemas import (
    JobStatusEnum,
    JobLinks,
    JobCreateResponse,
    JobInfo,
    JobListItem,
    JobListResponse,
)
from api.services import TaskService, TTSService, UserService
from api.services.tts_service import TTSGenerationParams

router = APIRouter(prefix="/v1/tts", tags=["TTS Jobs"])


def _build_job_links(job_id: str) -> JobLinks:
    """Build HATEOAS links for a job"""
    return JobLinks(
        self_link=f"/v1/tts/jobs/{job_id}",
        audio=f"/v1/tts/jobs/{job_id}/audio",
    )


def _task_status_to_job_status(status: TaskStatus) -> JobStatusEnum:
    """Convert database TaskStatus to API JobStatusEnum"""
    return JobStatusEnum(status.value)


async def _run_tts_generation(
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

            # Sync progress callback wrapper
            def progress_callback(progress: float, message: str):
                pass  # Progress updates handled separately

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

            print(f"[OK] Job {params.task_id} completed: {output_path}")

        except Exception as e:
            await task_service.update_task_status(
                params.task_id,
                TaskStatus.FAILED,
                error=str(e),
            )
            await session.commit()
            print(f"[ERROR] Job {params.task_id} failed: {e}")

        finally:
            # Cleanup temp files
            TTSService.cleanup_temp_files(
                params.prompt_audio_path,
                params.emo_audio_path,
            )


@router.post("/jobs", status_code=202)
async def create_job(
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
    Create a new TTS generation job.

    Returns 202 Accepted with job details and Location header.
    Poll GET /jobs/{job_id} to check status.
    Download audio from GET /jobs/{job_id}/audio when completed.
    """
    # Validate inputs
    if len(text) > settings.MAX_TEXT_LENGTH:
        raise HTTPException(400, f"Text too long (max {settings.MAX_TEXT_LENGTH})")

    if prompt_audio.size and prompt_audio.size > settings.MAX_AUDIO_SIZE:
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

    # Generate job ID
    job_id = uuid.uuid4().hex

    # Save uploaded files
    prompt_content = await prompt_audio.read()
    prompt_ext = os.path.splitext(prompt_audio.filename or ".wav")[1]
    prompt_path = await TTSService.save_upload_file(
        prompt_content, f"prompt_{job_id}", prompt_ext
    )

    emo_path = None
    if emo_audio:
        emo_content = await emo_audio.read()
        emo_ext = os.path.splitext(emo_audio.filename or ".wav")[1]
        emo_path = await TTSService.save_upload_file(
            emo_content, f"emo_{job_id}", emo_ext
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
    task = await task_service.create_task(
        task_id=job_id,
        user_id=user.id,
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
        task_id=job_id,
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
    background_tasks.add_task(_run_tts_generation, params, tts_model, semaphore, user.id)

    print(f"[OK] Job {job_id} created for user {user.id}")

    # Build response
    created_at = task.created_at if task.created_at else datetime.now(timezone.utc)
    response_data = JobCreateResponse(
        job_id=job_id,
        status=JobStatusEnum.PENDING,
        message="Job created successfully",
        created_at=created_at,
        links=_build_job_links(job_id),
    )

    # Return 202 Accepted with Location header
    return JSONResponse(
        status_code=202,
        content=response_data.model_dump(mode="json", by_alias=True),
        headers={
            "Location": f"/v1/tts/jobs/{job_id}",
            "Retry-After": "2",
        },
    )


@router.get("/jobs", response_model=JobListResponse)
async def list_jobs(
    user: User = Depends(get_current_user),
    status: Optional[JobStatusEnum] = None,
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    session: AsyncSession = Depends(get_session),
):
    """
    List current user's jobs with pagination.

    Optionally filter by status.
    """
    task_service = TaskService(session)

    # Convert enum if provided
    db_status = TaskStatus(status.value) if status else None

    # Calculate offset
    offset = (page - 1) * page_size

    # Get total count
    total = await task_service.count_tasks(user_id=user.id, status=db_status)

    # Get tasks for current page
    tasks = await task_service.get_tasks(
        user_id=user.id,
        status=db_status,
        limit=page_size,
        offset=offset
    )

    # Convert to response format
    job_list = []
    for task in tasks:
        queue_position = None
        if task.status == TaskStatus.PENDING:
            queue_position = await task_service.get_queue_position(task.id)

        job_list.append(JobListItem(
            job_id=task.id,
            status=_task_status_to_job_status(task.status),
            progress=task.progress,
            message=task.message,
            created_at=task.created_at,
            completed_at=task.completed_at,
            error=task.error,
            queue_position=queue_position,
            links=_build_job_links(task.id),
        ))

    # Calculate total pages
    total_pages = ceil(total / page_size) if total > 0 else 0

    return JobListResponse(
        jobs=job_list,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )


@router.get("/jobs/{job_id}", response_model=JobInfo)
async def get_job(
    job_id: str,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """
    Get job status and details.

    Returns current status, progress, and links to related resources.
    """
    task_service = TaskService(session)
    task = await task_service.get_task(job_id, user_id=user.id)

    if not task:
        raise HTTPException(404, "Job not found")

    queue_position = None
    if task.status == TaskStatus.PENDING:
        queue_position = await task_service.get_queue_position(job_id)

    return JobInfo(
        job_id=task.id,
        status=_task_status_to_job_status(task.status),
        progress=task.progress,
        message=task.message,
        created_at=task.created_at,
        completed_at=task.completed_at,
        error=task.error,
        queue_position=queue_position,
        links=_build_job_links(task.id),
    )


@router.delete("/jobs/{job_id}")
async def delete_job(
    job_id: str,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """
    Delete a job and its output file.

    Only the job owner can delete their jobs.
    """
    task_service = TaskService(session)

    # Check if task belongs to user
    task = await task_service.get_task(job_id, user_id=user.id)
    if not task:
        raise HTTPException(404, "Job not found")

    success = await task_service.delete_task(job_id)
    if not success:
        raise HTTPException(404, "Job not found")

    return {"message": "Job deleted successfully"}


@router.get("/jobs/{job_id}/audio")
async def download_audio(
    job_id: str,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """
    Download generated audio file.

    Only available when job status is 'completed'.
    """
    task_service = TaskService(session)
    task = await task_service.get_task(job_id, user_id=user.id)

    if not task:
        raise HTTPException(404, "Job not found")

    if task.status != TaskStatus.COMPLETED:
        raise HTTPException(
            425,
            f"Job not completed yet (status: {task.status.value})",
        )

    if not task.output_file:
        raise HTTPException(404, "Output file not found")

    if not os.path.exists(task.output_file):
        raise HTTPException(404, "Output file not found on disk")

    return FileResponse(
        task.output_file,
        media_type="audio/wav",
        filename=f"{job_id}.wav",
    )
