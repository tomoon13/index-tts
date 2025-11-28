"""
API Configuration
=================

Centralized configuration management using Pydantic Settings.
"""

import os
from functools import lru_cache
from typing import Set

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings with environment variable support"""

    # Server settings
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    DEBUG: bool = False

    # Database settings
    DATABASE_URL: str = "sqlite+aiosqlite:///./data/indextts.db"

    # Model settings
    MODEL_DIR: str = "./checkpoints"

    # Task settings
    MAX_CONCURRENT_TASKS: int = 3
    TASK_TIMEOUT: int = 300  # seconds
    TASK_RETENTION: int = 3600  # seconds
    CLEANUP_INTERVAL: int = 600  # seconds

    # File settings
    OUTPUT_DIR: str = "./outputs/api"
    MAX_TEXT_LENGTH: int = 500
    MAX_AUDIO_SIZE: int = 10 * 1024 * 1024  # 10MB

    # Supported audio formats
    SUPPORTED_AUDIO_FORMATS: Set[str] = {
        ".wav", ".mp3", ".aac", ".m4a", ".flac", ".ogg",
        ".opus", ".wma", ".aiff", ".au", ".raw"
    }
    SUPPORTED_AUDIO_MIMETYPES: Set[str] = {
        "audio/wav", "audio/wave", "audio/x-wav",
        "audio/mpeg", "audio/mp3",
        "audio/aac", "audio/x-aac",
        "audio/mp4", "audio/x-m4a",
        "audio/flac", "audio/x-flac",
        "audio/ogg", "audio/vorbis",
        "audio/opus",
        "audio/x-ms-wma",
        "audio/aiff", "audio/x-aiff",
        "audio/basic",
        "application/octet-stream"
    }

    # TTS model settings
    USE_FP16: bool = False
    USE_DEEPSPEED: bool = False
    USE_CUDA_KERNEL: bool = False

    # JWT Authentication settings
    JWT_SECRET_KEY: str = "change-this-to-a-secure-random-string"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7  # 7 days

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance"""
    return Settings()


settings = get_settings()
