#!/usr/bin/env python3
"""
IndexTTS2 API Runner
====================

Usage:
    uv run python run_api.py

    # Or with custom settings:
    HOST=0.0.0.0 PORT=8080 uv run python run_api.py
"""

import uvicorn

from api.config import settings


def main():
    """Run the API server"""
    uvicorn.run(
        "api.main:app",
        host=settings.HOST,
        port=settings.PORT,
        log_level="info",
        reload=settings.DEBUG,
    )


if __name__ == "__main__":
    main()
