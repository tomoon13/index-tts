"""
IndexTTS2 REST API Service
==========================

A production-ready REST API for IndexTTS2 text-to-speech generation.

Features:
- Asynchronous task processing
- Configurable concurrent task limit
- Progress tracking
- Automatic file cleanup
- Swagger documentation

Usage:
    uv run python api.py

API Documentation:
    http://localhost:8000/docs
"""

import asyncio
import os
import sys
import time
import uuid
from contextlib import asynccontextmanager
from datetime import datetime
from enum import Enum
from typing import Dict, Optional, List

import uvicorn
from fastapi import FastAPI, File, UploadFile, Form, HTTPException, BackgroundTasks
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

# Add current directory to path
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(current_dir)
sys.path.append(os.path.join(current_dir, "indextts"))

from indextts.infer_v2 import IndexTTS2
import speech_length_patch  # Enable speech_length parameter


# ============================================================================
# Configuration
# ============================================================================

class Config:
    """API Configuration"""
    # Server settings
    HOST = "0.0.0.0"
    PORT = 8000

    # Model settings
    MODEL_DIR = "./checkpoints"

    # Task settings
    MAX_CONCURRENT_TASKS = 3        # Maximum number of concurrent generation tasks
    TASK_TIMEOUT = 300              # Task timeout in seconds (5 minutes)
    TASK_RETENTION = 3600           # Task result retention time in seconds (1 hour)
    CLEANUP_INTERVAL = 600          # Cleanup interval in seconds (10 minutes)

    # File settings
    OUTPUT_DIR = "./outputs/api"
    MAX_TEXT_LENGTH = 500
    MAX_AUDIO_SIZE = 10 * 1024 * 1024  # 10MB

    # TTS default settings
    USE_FP16 = False
    USE_DEEPSPEED = False
    USE_CUDA_KERNEL = False


# ============================================================================
# Data Models
# ============================================================================

class TaskStatus(str, Enum):
    """Task status enumeration"""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class TaskInfo(BaseModel):
    """Task information model"""
    task_id: str
    status: TaskStatus
    progress: float = Field(0.0, ge=0.0, le=1.0)
    message: str = ""
    created_at: datetime
    completed_at: Optional[datetime] = None
    output_file: Optional[str] = None
    error: Optional[str] = None
    queue_position: Optional[int] = None


class GenerateResponse(BaseModel):
    """Response model for generate endpoint"""
    task_id: str
    status: TaskStatus
    message: str


class HealthResponse(BaseModel):
    """Response model for health endpoint"""
    status: str
    model_loaded: bool
    active_tasks: int
    queue_length: int
    max_workers: int


# ============================================================================
# Global State
# ============================================================================

# TTS model instance (loaded on startup)
tts_model: Optional[IndexTTS2] = None

# Task storage (in-memory)
tasks: Dict[str, TaskInfo] = {}

# Semaphore for controlling concurrent tasks
task_semaphore: Optional[asyncio.Semaphore] = None

# Cleanup task
cleanup_task_handle: Optional[asyncio.Task] = None


# ============================================================================
# Application Lifecycle
# ============================================================================

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager"""
    # Startup
    print("=" * 60)
    print("IndexTTS2 REST API Service")
    print("=" * 60)

    # Check required files
    print("Checking required model files...")
    required_files = [
        "bpe.model",
        "gpt.pth",
        "config.yaml",
        "s2mel.pth",
        "wav2vec2bert_stats.pt"
    ]

    missing_files = []
    for file in required_files:
        file_path = os.path.join(Config.MODEL_DIR, file)
        if not os.path.exists(file_path):
            missing_files.append(file)
            print(f"  ✗ Missing: {file}")
        else:
            print(f"  ✓ Found: {file}")

    if missing_files:
        print("\n" + "=" * 60)
        print("ERROR: Missing required model files!")
        print("=" * 60)
        print("\nMissing files:")
        for file in missing_files:
            print(f"  - {file}")
        print("\nPlease download the IndexTTS2 model files to:")
        print(f"  {os.path.abspath(Config.MODEL_DIR)}/")
        print("\nDownload link:")
        print("  https://huggingface.co/IndexTeam/Index-1.9B-Character")
        print("\nOr check the project README for instructions:")
        print("  https://github.com/index-tts/index-tts")
        print("=" * 60)
        raise RuntimeError(f"Missing required files: {', '.join(missing_files)}")

    # Load TTS model
    print("\nLoading IndexTTS2 model...")
    global tts_model, task_semaphore, cleanup_task_handle

    try:
        tts_model = IndexTTS2(
            model_dir=Config.MODEL_DIR,
            cfg_path=os.path.join(Config.MODEL_DIR, "config.yaml"),
            use_fp16=Config.USE_FP16,
            use_deepspeed=Config.USE_DEEPSPEED,
            use_cuda_kernel=Config.USE_CUDA_KERNEL,
        )
        print("✓ Model loaded successfully")
    except Exception as e:
        print(f"✗ Failed to load model: {e}")
        print("\nIf you see errors about 'qwen' or missing directories,")
        print("make sure all model files are properly extracted.")
        raise

    # Initialize semaphore
    task_semaphore = asyncio.Semaphore(Config.MAX_CONCURRENT_TASKS)
    print(f"✓ Concurrent task limit: {Config.MAX_CONCURRENT_TASKS}")

    # Create output directory
    os.makedirs(Config.OUTPUT_DIR, exist_ok=True)
    print(f"✓ Output directory: {Config.OUTPUT_DIR}")

    # Start cleanup task
    cleanup_task_handle = asyncio.create_task(cleanup_old_tasks())
    print(f"✓ Cleanup task started (interval: {Config.CLEANUP_INTERVAL}s)")

    print("=" * 60)
    print(f"Server ready at http://{Config.HOST}:{Config.PORT}")
    print(f"API docs at http://{Config.HOST}:{Config.PORT}/docs")
    print("=" * 60)

    yield

    # Shutdown
    print("\nShutting down...")
    if cleanup_task_handle:
        cleanup_task_handle.cancel()
    print("✓ Cleanup task stopped")


app = FastAPI(
    title="IndexTTS2 API",
    description="REST API for IndexTTS2 text-to-speech generation",
    version="1.0.0",
    lifespan=lifespan
)


# ============================================================================
# Helper Functions
# ============================================================================

async def cleanup_old_tasks():
    """Periodically clean up old tasks and files"""
    while True:
        try:
            await asyncio.sleep(Config.CLEANUP_INTERVAL)

            current_time = time.time()
            tasks_to_delete = []

            for task_id, task_info in tasks.items():
                # Check if task is expired
                task_age = current_time - task_info.created_at.timestamp()
                if task_age > Config.TASK_RETENTION:
                    # Delete output file if exists
                    if task_info.output_file and os.path.exists(task_info.output_file):
                        try:
                            os.remove(task_info.output_file)
                            print(f"✓ Deleted expired file: {task_info.output_file}")
                        except Exception as e:
                            print(f"✗ Failed to delete file: {e}")

                    tasks_to_delete.append(task_id)

            # Remove expired tasks
            for task_id in tasks_to_delete:
                del tasks[task_id]
                print(f"✓ Removed expired task: {task_id}")

            if tasks_to_delete:
                print(f"Cleanup completed: removed {len(tasks_to_delete)} tasks")

        except asyncio.CancelledError:
            break
        except Exception as e:
            print(f"✗ Cleanup error: {e}")


def get_queue_position(task_id: str) -> Optional[int]:
    """Get the queue position of a task"""
    pending_tasks = [
        tid for tid, info in tasks.items()
        if info.status == TaskStatus.PENDING and info.created_at <= tasks[task_id].created_at
    ]
    if task_id in pending_tasks:
        return pending_tasks.index(task_id)
    return None


async def save_upload_file(upload_file: UploadFile, prefix: str = "upload") -> str:
    """Save uploaded file to disk"""
    # Generate unique filename
    file_ext = os.path.splitext(upload_file.filename)[1] if upload_file.filename else ".wav"
    filename = f"{prefix}_{uuid.uuid4().hex}{file_ext}"
    filepath = os.path.join(Config.OUTPUT_DIR, filename)

    # Save file
    content = await upload_file.read()
    with open(filepath, "wb") as f:
        f.write(content)

    return filepath


async def run_tts_generation(
    task_id: str,
    text: str,
    prompt_audio_path: str,
    emo_audio_path: Optional[str],
    speech_length: int,
    temperature: float,
    top_p: float,
    top_k: int,
    emo_weight: float,
    max_text_tokens_per_segment: int,
    # Emotion control parameters
    emo_vector: Optional[list] = None,
    use_emo_text: bool = False,
    emo_text: Optional[str] = None,
    emo_random: bool = False,
):
    """Run TTS generation task"""
    output_path = os.path.join(Config.OUTPUT_DIR, f"{task_id}.wav")

    try:
        # Update status
        tasks[task_id].status = TaskStatus.PROCESSING
        tasks[task_id].message = "Starting generation..."

        # Setup progress callback
        def progress_callback(progress: float, message: str):
            if task_id in tasks:
                tasks[task_id].progress = progress
                tasks[task_id].message = message

        # Temporarily set progress callback
        original_callback = tts_model.gr_progress
        tts_model.gr_progress = type('ProgressWrapper', (), {
            '__call__': lambda self, p, m: progress_callback(p, m)
        })()

        # Acquire semaphore (control concurrency)
        async with task_semaphore:
            # Update queue position
            tasks[task_id].queue_position = None

            # Run generation in thread pool (blocking operation)
            await asyncio.to_thread(
                lambda: next(tts_model.infer_generator(
                    spk_audio_prompt=prompt_audio_path,
                    text=text,
                    output_path=output_path,
                    emo_audio_prompt=emo_audio_path,
                    emo_alpha=emo_weight,
                    emo_vector=emo_vector,
                    use_emo_text=use_emo_text,
                    emo_text=emo_text,
                    use_random=emo_random,
                    verbose=False,
                    max_text_tokens_per_segment=max_text_tokens_per_segment,
                    stream_return=False,
                    do_sample=True,
                    top_p=top_p,
                    top_k=top_k,
                    temperature=temperature,
                    speech_length=speech_length,
                ))
            )

        # Restore original callback
        tts_model.gr_progress = original_callback

        # Update task info
        tasks[task_id].status = TaskStatus.COMPLETED
        tasks[task_id].progress = 1.0
        tasks[task_id].message = "Generation completed"
        tasks[task_id].completed_at = datetime.now()
        tasks[task_id].output_file = output_path

        print(f"✓ Task {task_id} completed: {output_path}")

    except asyncio.TimeoutError:
        tasks[task_id].status = TaskStatus.FAILED
        tasks[task_id].error = "Task timeout"
        print(f"✗ Task {task_id} timeout")

    except Exception as e:
        tasks[task_id].status = TaskStatus.FAILED
        tasks[task_id].error = str(e)
        print(f"✗ Task {task_id} failed: {e}")

    finally:
        # Cleanup temporary files
        try:
            if os.path.exists(prompt_audio_path):
                os.remove(prompt_audio_path)
            if emo_audio_path and os.path.exists(emo_audio_path):
                os.remove(emo_audio_path)
        except Exception:
            pass


# ============================================================================
# API Endpoints
# ============================================================================

@app.get("/", tags=["General"])
async def root():
    """Root endpoint"""
    return {
        "service": "IndexTTS2 API",
        "version": "1.0.0",
        "docs": "/docs"
    }


@app.get("/health", response_model=HealthResponse, tags=["General"])
async def health():
    """Health check endpoint"""
    active_tasks = sum(1 for t in tasks.values() if t.status == TaskStatus.PROCESSING)
    queue_length = sum(1 for t in tasks.values() if t.status == TaskStatus.PENDING)

    return HealthResponse(
        status="healthy" if tts_model else "unhealthy",
        model_loaded=tts_model is not None,
        active_tasks=active_tasks,
        queue_length=queue_length,
        max_workers=Config.MAX_CONCURRENT_TASKS
    )


@app.post("/v1/tts/generate", response_model=GenerateResponse, tags=["TTS"])
async def generate_speech(
    background_tasks: BackgroundTasks,
    text: str = Form(..., description="Text to synthesize"),
    prompt_audio: UploadFile = File(..., description="Speaker prompt audio file"),
    emo_audio: Optional[UploadFile] = File(None, description="Emotion reference audio file (for mode=reference)"),
    speech_length: int = Form(0, description="Target speech duration in milliseconds (0 for auto)"),
    temperature: float = Form(0.8, ge=0.1, le=2.0, description="Sampling temperature"),
    top_p: float = Form(0.8, ge=0.0, le=1.0, description="Top-p sampling"),
    top_k: int = Form(30, ge=0, le=100, description="Top-k sampling"),
    emo_weight: float = Form(0.65, ge=0.0, le=1.0, description="Emotion weight/alpha"),
    max_text_tokens_per_segment: int = Form(120, ge=20, le=300, description="Max tokens per segment"),
    # Emotion control parameters
    emo_mode: str = Form("speaker", description="Emotion control mode: 'speaker' (same as prompt), 'reference' (use emo_audio), 'vector' (use emo_vector_*), 'text' (use emo_text)"),
    emo_text: Optional[str] = Form(None, description="Emotion description text (for mode=text, e.g., '委屈巴巴')"),
    emo_random: bool = Form(False, description="Use random emotion sampling"),
    # Emotion vector (8 dimensions: joy, anger, sadness, fear, disgust, melancholy, surprise, calm)
    emo_vector_joy: float = Form(0.0, ge=0.0, le=1.0, description="喜 (Joy) - 0.0 to 1.0"),
    emo_vector_anger: float = Form(0.0, ge=0.0, le=1.0, description="怒 (Anger) - 0.0 to 1.0"),
    emo_vector_sadness: float = Form(0.0, ge=0.0, le=1.0, description="哀 (Sadness) - 0.0 to 1.0"),
    emo_vector_fear: float = Form(0.0, ge=0.0, le=1.0, description="懼 (Fear) - 0.0 to 1.0"),
    emo_vector_disgust: float = Form(0.0, ge=0.0, le=1.0, description="厭惡 (Disgust) - 0.0 to 1.0"),
    emo_vector_melancholy: float = Form(0.0, ge=0.0, le=1.0, description="低落 (Melancholy) - 0.0 to 1.0"),
    emo_vector_surprise: float = Form(0.0, ge=0.0, le=1.0, description="驚喜 (Surprise) - 0.0 to 1.0"),
    emo_vector_calm: float = Form(0.0, ge=0.0, le=1.0, description="平靜 (Calm) - 0.0 to 1.0"),
):
    """
    Generate speech from text with emotion control

    Creates an asynchronous generation task and returns a task ID.
    Use the status and download endpoints to retrieve results.

    Emotion Control Modes:
    - 'speaker': Use the same emotion as the speaker prompt audio (default)
    - 'reference': Use a separate emotion reference audio file (requires emo_audio)
    - 'vector': Use custom 8-dimensional emotion vector (喜怒哀懼厭惡低落驚喜平靜)
    - 'text': Generate emotion from text description (requires emo_text, experimental)
    """
    # Validate inputs
    if len(text) > Config.MAX_TEXT_LENGTH:
        raise HTTPException(400, f"Text too long (max {Config.MAX_TEXT_LENGTH} characters)")

    if prompt_audio.size > Config.MAX_AUDIO_SIZE:
        raise HTTPException(400, f"Prompt audio too large (max {Config.MAX_AUDIO_SIZE} bytes)")

    if emo_audio and emo_audio.size > Config.MAX_AUDIO_SIZE:
        raise HTTPException(400, f"Emotion audio too large (max {Config.MAX_AUDIO_SIZE} bytes)")

    # Validate emotion mode
    valid_emo_modes = ["speaker", "reference", "vector", "text"]
    if emo_mode not in valid_emo_modes:
        raise HTTPException(400, f"Invalid emo_mode. Must be one of: {valid_emo_modes}")

    # Validate mode-specific requirements
    if emo_mode == "reference" and not emo_audio:
        raise HTTPException(400, "emo_mode='reference' requires emo_audio file")

    if emo_mode == "text" and not emo_text:
        raise HTTPException(400, "emo_mode='text' requires emo_text parameter")

    # Process emotion parameters based on mode
    emo_vector = None
    use_emo_text = False
    emo_audio_path = None

    if emo_mode == "speaker":
        # Use speaker's emotion (default)
        emo_audio_path = None  # Will be set to prompt audio in generation

    elif emo_mode == "reference":
        # Use separate emotion reference audio
        if not emo_audio:
            raise HTTPException(400, "Emotion reference audio required for mode='reference'")

    elif emo_mode == "vector":
        # Use custom emotion vector (8 dimensions)
        emo_vector = [
            emo_vector_joy,
            emo_vector_anger,
            emo_vector_sadness,
            emo_vector_fear,
            emo_vector_disgust,
            emo_vector_melancholy,
            emo_vector_surprise,
            emo_vector_calm,
        ]
        # Normalize vector (will be done by TTS model)

    elif emo_mode == "text":
        # Use text-based emotion generation
        use_emo_text = True
        if not emo_text:
            emo_text = text  # Use main text as fallback

    # Generate task ID
    task_id = uuid.uuid4().hex

    # Save uploaded files
    try:
        prompt_audio_path = await save_upload_file(prompt_audio, f"prompt_{task_id}")
        if emo_audio:
            emo_audio_path = await save_upload_file(emo_audio, f"emo_{task_id}")
    except Exception as e:
        raise HTTPException(500, f"Failed to save uploaded files: {e}")

    # Create task info
    task_info = TaskInfo(
        task_id=task_id,
        status=TaskStatus.PENDING,
        progress=0.0,
        message="Task queued",
        created_at=datetime.now(),
        queue_position=get_queue_position(task_id)
    )
    tasks[task_id] = task_info

    # Start generation in background
    background_tasks.add_task(
        run_tts_generation,
        task_id=task_id,
        text=text,
        prompt_audio_path=prompt_audio_path,
        emo_audio_path=emo_audio_path,
        speech_length=speech_length,
        temperature=temperature,
        top_p=top_p,
        top_k=top_k,
        emo_weight=emo_weight,
        max_text_tokens_per_segment=max_text_tokens_per_segment,
        # Emotion control parameters
        emo_vector=emo_vector,
        use_emo_text=use_emo_text,
        emo_text=emo_text,
        emo_random=emo_random,
    )

    print(f"✓ Task {task_id} created and queued")

    return GenerateResponse(
        task_id=task_id,
        status=TaskStatus.PENDING,
        message="Task created successfully"
    )


@app.get("/v1/tts/status/{task_id}", response_model=TaskInfo, tags=["TTS"])
async def get_task_status(task_id: str):
    """
    Get task status

    Returns the current status, progress, and other information about a task.
    """
    if task_id not in tasks:
        raise HTTPException(404, "Task not found")

    task_info = tasks[task_id]

    # Update queue position for pending tasks
    if task_info.status == TaskStatus.PENDING:
        task_info.queue_position = get_queue_position(task_id)

    return task_info


@app.get("/v1/tts/download/{task_id}", tags=["TTS"])
async def download_result(task_id: str):
    """
    Download generated audio

    Returns the generated audio file if the task is completed.
    """
    if task_id not in tasks:
        raise HTTPException(404, "Task not found")

    task_info = tasks[task_id]

    if task_info.status != TaskStatus.COMPLETED:
        raise HTTPException(425, f"Task not completed yet (status: {task_info.status})")

    if not task_info.output_file or not os.path.exists(task_info.output_file):
        raise HTTPException(404, "Output file not found")

    return FileResponse(
        task_info.output_file,
        media_type="audio/wav",
        filename=f"{task_id}.wav"
    )


@app.get("/v1/tts/tasks", response_model=List[TaskInfo], tags=["TTS"])
async def list_tasks(
    status: Optional[TaskStatus] = None,
    limit: int = 100
):
    """
    List all tasks

    Returns a list of all tasks, optionally filtered by status.
    """
    task_list = list(tasks.values())

    # Filter by status if specified
    if status:
        task_list = [t for t in task_list if t.status == status]

    # Sort by creation time (newest first)
    task_list.sort(key=lambda t: t.created_at, reverse=True)

    # Limit results
    return task_list[:limit]


@app.delete("/v1/tts/tasks/{task_id}", tags=["TTS"])
async def delete_task(task_id: str):
    """
    Delete a task

    Removes a task and its output file from the system.
    """
    if task_id not in tasks:
        raise HTTPException(404, "Task not found")

    task_info = tasks[task_id]

    # Delete output file if exists
    if task_info.output_file and os.path.exists(task_info.output_file):
        try:
            os.remove(task_info.output_file)
        except Exception as e:
            print(f"✗ Failed to delete file: {e}")

    # Remove task
    del tasks[task_id]

    return {"message": "Task deleted successfully"}


# ============================================================================
# Main Entry Point
# ============================================================================

if __name__ == "__main__":
    uvicorn.run(
        app,
        host=Config.HOST,
        port=Config.PORT,
        log_level="info"
    )
