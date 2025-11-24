"""
Test script for multiple audio format support in IndexTTS2 API
===============================================================

This script tests the API's ability to handle different audio formats:
- WAV, MP3, AAC, M4A, FLAC, OGG, OPUS, etc.

Usage:
    python test_audio_formats.py
"""

import requests
import time
import os
from pathlib import Path

# Configuration
API_BASE_URL = "http://localhost:8000"
TEST_TEXT = "你好，這是多格式音頻測試。"

# Test audio files (you need to provide these)
TEST_AUDIO_FILES = {
    "wav": "./test_audio/sample.wav",
    "mp3": "./test_audio/sample.mp3",
    "aac": "./test_audio/sample.aac",
    "m4a": "./test_audio/sample.m4a",
    "flac": "./test_audio/sample.flac",
    "ogg": "./test_audio/sample.ogg",
}


def test_format_validation():
    """Test format validation with invalid formats"""
    print("\n" + "="*60)
    print("Testing Audio Format Validation")
    print("="*60)

    # Test invalid format
    invalid_formats = [
        ("sample.txt", "text/plain"),
        ("sample.pdf", "application/pdf"),
        ("sample.zip", "application/zip"),
    ]

    for filename, content_type in invalid_formats:
        print(f"\n--- Testing invalid format: {filename} ---")

        # Create a dummy file
        dummy_content = b"This is not an audio file"

        files = {
            'prompt_audio': (filename, dummy_content, content_type)
        }

        data = {
            'text': TEST_TEXT
        }

        response = requests.post(
            f"{API_BASE_URL}/v1/tts/generate",
            files=files,
            data=data
        )

        if response.status_code == 400:
            print(f"✓ Correctly rejected invalid format")
            print(f"  Error: {response.json().get('detail', 'Unknown error')}")
        else:
            print(f"⚠ Expected 400 error, got {response.status_code}")


def test_audio_format(format_name: str, file_path: str):
    """Test generation with a specific audio format"""
    print(f"\n--- Testing {format_name.upper()} format ---")

    if not os.path.exists(file_path):
        print(f"⚠ Skipping: {file_path} not found")
        return False

    with open(file_path, 'rb') as audio_file:
        files = {
            'prompt_audio': (os.path.basename(file_path), audio_file)
        }

        data = {
            'text': TEST_TEXT
        }

        print(f"Uploading {format_name.upper()} file: {os.path.basename(file_path)}")
        response = requests.post(
            f"{API_BASE_URL}/v1/tts/generate",
            files=files,
            data=data
        )

        if response.status_code == 200:
            result = response.json()
            task_id = result['task_id']
            print(f"✓ Task created: {task_id}")

            # Wait for completion
            max_wait = 60
            start_time = time.time()

            while time.time() - start_time < max_wait:
                status_response = requests.get(
                    f"{API_BASE_URL}/v1/tts/status/{task_id}"
                )
                status = status_response.json()

                if status['status'] == 'completed':
                    print(f"✓ Generation completed successfully!")

                    # Download result
                    download_response = requests.get(
                        f"{API_BASE_URL}/v1/tts/download/{task_id}"
                    )

                    if download_response.status_code == 200:
                        output_file = f"test_output_{format_name}.wav"
                        with open(output_file, 'wb') as f:
                            f.write(download_response.content)
                        print(f"✓ Audio saved to: {output_file}")

                        # Cleanup
                        requests.delete(f"{API_BASE_URL}/v1/tts/tasks/{task_id}")
                        return True

                elif status['status'] == 'failed':
                    print(f"❌ Generation failed: {status.get('error', 'Unknown error')}")
                    return False

                time.sleep(2)

            print(f"⚠ Timeout waiting for task completion")
            return False

        else:
            print(f"❌ Request failed: {response.status_code}")
            print(f"Response: {response.text}")
            return False


def test_format_conversion():
    """Test that API can handle different input formats"""
    print("\n" + "="*60)
    print("Testing Multiple Audio Format Support")
    print("="*60)

    results = {}

    for format_name, file_path in TEST_AUDIO_FILES.items():
        success = test_audio_format(format_name, file_path)
        results[format_name] = success

    # Summary
    print("\n" + "="*60)
    print("Test Summary")
    print("="*60)

    for format_name, success in results.items():
        if success:
            status = "✓ PASS"
        elif TEST_AUDIO_FILES[format_name] and not os.path.exists(TEST_AUDIO_FILES[format_name]):
            status = "⚠ SKIP (file not found)"
        else:
            status = "❌ FAIL"

        print(f"{format_name.upper():10s} - {status}")


def create_test_audio_guide():
    """Display guide for creating test audio files"""
    print("\n" + "="*60)
    print("Test Audio Files Setup Guide")
    print("="*60)
    print("\nTo test different audio formats, you need to provide sample files.")
    print("You can convert a single WAV file to other formats using ffmpeg:")
    print("\nCreate test directory:")
    print("  mkdir -p test_audio")
    print("\nConvert to different formats (replace input.wav with your file):")
    print("  ffmpeg -i input.wav test_audio/sample.wav")
    print("  ffmpeg -i input.wav -codec:a libmp3lame test_audio/sample.mp3")
    print("  ffmpeg -i input.wav -codec:a aac test_audio/sample.aac")
    print("  ffmpeg -i input.wav -codec:a aac test_audio/sample.m4a")
    print("  ffmpeg -i input.wav -codec:a flac test_audio/sample.flac")
    print("  ffmpeg -i input.wav -codec:a libvorbis test_audio/sample.ogg")
    print("\nThen run this script again to test all formats.")


def main():
    """Run all tests"""
    print("\n" + "="*60)
    print("IndexTTS2 API - Audio Format Support Test")
    print("="*60)

    # Check if API is healthy
    try:
        response = requests.get(f"{API_BASE_URL}/health")
        if response.status_code != 200:
            print("\n❌ API is not healthy. Make sure the server is running.")
            return
        print("\n✓ API is healthy")
    except Exception as e:
        print(f"\n❌ Cannot connect to API: {e}")
        print(f"Make sure the server is running at {API_BASE_URL}")
        return

    # Check if test files exist
    files_exist = any(os.path.exists(path) for path in TEST_AUDIO_FILES.values())

    if not files_exist:
        print("\n⚠ No test audio files found.")
        create_test_audio_guide()
        return

    # Run tests
    test_format_validation()
    test_format_conversion()

    print("\n" + "="*60)
    print("All tests completed!")
    print("="*60)


if __name__ == "__main__":
    main()
