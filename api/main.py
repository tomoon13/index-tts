"""
TTS REST API Service
====================

Main FastAPI application entry point.
"""

import asyncio
import os
import sys
import time
import uuid
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import Response
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware

# Add project root to path
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
sys.path.insert(0, project_root)
sys.path.insert(0, os.path.join(project_root, "indextts"))

from api.config import settings
from api.console import ConsoleUI, set_console_ui, log_http
from api.database import init_db, close_db, async_session_maker
from api.dependencies import set_tts_model, set_task_semaphore
from api.routes import health_router, jobs_router, auth_router, users_router
from api.services import TaskService


# ============================================================================
# Cleanup Task
# ============================================================================

async def cleanup_old_tasks():
    """Periodically clean up old tasks"""
    # Skip if cleanup is disabled
    if settings.TASK_RETENTION < 0:
        return

    while True:
        try:
            await asyncio.sleep(settings.CLEANUP_INTERVAL)

            async with async_session_maker() as session:
                task_service = TaskService(session)
                deleted = await task_service.cleanup_old_tasks(settings.TASK_RETENTION)
                await session.commit()

                if deleted > 0:
                    print(f"✓ Cleanup: removed {deleted} expired tasks")

        except asyncio.CancelledError:
            break
        except Exception as e:
            print(f"✗ Cleanup error: {e}")


# ============================================================================
# Application Lifespan
# ============================================================================

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager"""
    print("=" * 60)
    print("TTS REST API Service")
    print("=" * 60)

    # Check required model files
    print("Checking required model files...")
    required_files = [
        "bpe.model",
        "gpt.pth",
        "config.yaml",
        "s2mel.pth",
        "wav2vec2bert_stats.pt",
    ]

    missing_files = []
    for file in required_files:
        file_path = os.path.join(settings.MODEL_DIR, file)
        if not os.path.exists(file_path):
            missing_files.append(file)
            print(f"  ✗ Missing: {file}")
        else:
            print(f"  ✓ Found: {file}")

    if missing_files:
        print("\n" + "=" * 60)
        print("ERROR: Missing required model files!")
        print("=" * 60)
        raise RuntimeError(f"Missing required files: {', '.join(missing_files)}")

    # Initialize database
    print("\nInitializing database...")
    await init_db()

    # Run migrations
    from api.database import run_migrations
    async with async_session_maker() as session:
        await run_migrations(session)

    # Seed database with default data
    from api.database import seed_database
    async with async_session_maker() as session:
        await seed_database(session)

    # Check JWT secret
    if settings.JWT_SECRET_KEY == "change-this-to-a-secure-random-string":
        print("⚠ Warning: Using default JWT_SECRET_KEY. Set a secure key in production!")

    # Load TTS model
    print("\nLoading TTS model...")
    try:
        from indextts.infer_v2 import IndexTTS2
        import speech_length_patch  # Enable speech_length parameter

        tts_model = IndexTTS2(
            model_dir=settings.MODEL_DIR,
            cfg_path=os.path.join(settings.MODEL_DIR, "config.yaml"),
            use_fp16=settings.USE_FP16,
            use_deepspeed=settings.USE_DEEPSPEED,
            use_cuda_kernel=settings.USE_CUDA_KERNEL,
        )
        set_tts_model(tts_model)
        print("✓ Model loaded successfully")
    except Exception as e:
        print(f"✗ Failed to load model: {e}")
        raise

    # Initialize semaphore
    semaphore = asyncio.Semaphore(settings.MAX_CONCURRENT_TASKS)
    set_task_semaphore(semaphore)
    print(f"✓ Concurrent task limit: {settings.MAX_CONCURRENT_TASKS}")

    # Create output directory
    os.makedirs(settings.OUTPUT_DIR, exist_ok=True)
    print(f"✓ Output directory: {settings.OUTPUT_DIR}")

    # Start cleanup task
    cleanup_task = asyncio.create_task(cleanup_old_tasks())
    if settings.TASK_RETENTION < 0:
        print("✓ Task cleanup disabled (TASK_RETENTION=-1)")
    else:
        print(f"✓ Cleanup task started (interval: {settings.CLEANUP_INTERVAL}s, retention: {settings.TASK_RETENTION}s)")

    print("=" * 60)
    print(f"Server ready at http://{settings.HOST}:{settings.PORT}")
    print(f"API docs at http://{settings.HOST}:{settings.PORT}/docs")
    print("=" * 60)

    # Start console UI
    console_ui = ConsoleUI()
    set_console_ui(console_ui)
    await console_ui.start()

    yield

    # Shutdown
    await console_ui.stop()
    print("\nShutting down...")
    cleanup_task.cancel()
    try:
        await cleanup_task
    except asyncio.CancelledError:
        pass
    await close_db()
    print("✓ Shutdown complete")


# ============================================================================
# Request Logging Middleware
# ============================================================================

class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Middleware to log all incoming requests to Rich console"""

    async def dispatch(self, request: Request, call_next):
        request_id = uuid.uuid4().hex[:8]

        # Process request
        start_time = time.time()
        response = await call_next(request)
        duration_ms = (time.time() - start_time) * 1000

        # Capture response body for JSON responses
        response_body = ""
        content_type = response.headers.get("content-type", "")
        if content_type.startswith("application/json"):
            # Read and reconstruct response
            body_bytes = b""
            async for chunk in response.body_iterator:
                body_bytes += chunk
            response_body = body_bytes.decode("utf-8", errors="replace")

            # Log to Rich console
            log_http(
                method=request.method,
                path=request.url.path,
                status=response.status_code,
                duration_ms=duration_ms,
                request_id=request_id,
                response_body=response_body,
            )

            # Return new response with captured body
            return Response(
                content=body_bytes,
                status_code=response.status_code,
                headers=dict(response.headers),
                media_type=response.media_type,
            )

        # Log without body for non-JSON responses
        log_http(
            method=request.method,
            path=request.url.path,
            status=response.status_code,
            duration_ms=duration_ms,
            request_id=request_id,
        )

        return response


# ============================================================================
# Create Application
# ============================================================================

app = FastAPI(
    title="TTS API",
    description="REST API for text-to-speech generation",
    version="1.0.0",
    lifespan=lifespan,
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=settings.CORS_ALLOW_CREDENTIALS,
    allow_methods=settings.CORS_ALLOW_METHODS,
    allow_headers=settings.CORS_ALLOW_HEADERS,
)

# Add middleware
app.add_middleware(RequestLoggingMiddleware)

# Include routers
app.include_router(health_router)
app.include_router(auth_router)
app.include_router(users_router)
app.include_router(jobs_router)
