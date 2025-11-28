"""
Simple test script for IndexTTS2 API

Usage:
    python test_api.py <prompt_audio.wav> "Text to synthesize"

Example:
    python test_api.py examples/sample_prompt.wav "你好世界，這是一個測試。"
"""

import sys
import time
import requests
from pathlib import Path


def test_api(prompt_audio_path: str, text: str, api_base: str = "http://localhost:8000"):
    """Test the TTS API"""

    print("=" * 60)
    print("IndexTTS2 API Test")
    print("=" * 60)

    # Check if prompt audio exists
    if not Path(prompt_audio_path).exists():
        print(f"✗ Error: Prompt audio file not found: {prompt_audio_path}")
        return False

    # 1. Check health
    print("\n1. Checking API health...")
    try:
        response = requests.get(f"{api_base}/health", timeout=5)
        response.raise_for_status()
        health_data = response.json()
        print(f"   ✓ Status: {health_data['status']}")
        print(f"   ✓ Model loaded: {health_data['model_loaded']}")
        print(f"   ✓ Active tasks: {health_data['active_tasks']}")
        print(f"   ✓ Queue length: {health_data['queue_length']}")
    except requests.exceptions.RequestException as e:
        print(f"   ✗ Error: {e}")
        print("   Make sure the API server is running: uv run python api.py")
        return False

    # 2. Create generation task
    print("\n2. Creating generation task...")
    print(f"   Text: {text}")
    print(f"   Prompt audio: {prompt_audio_path}")

    try:
        with open(prompt_audio_path, "rb") as f:
            response = requests.post(
                f"{api_base}/v1/tts/generate",
                data={
                    "text": text,
                    "speech_length": 0,  # Auto duration
                    "temperature": 0.8,
                },
                files={
                    "prompt_audio": f
                },
                timeout=10
            )
        response.raise_for_status()
        task_data = response.json()
        task_id = task_data["task_id"]
        print(f"   ✓ Task created: {task_id}")
    except requests.exceptions.RequestException as e:
        print(f"   ✗ Error: {e}")
        return False

    # 3. Poll task status
    print("\n3. Waiting for generation to complete...")
    start_time = time.time()
    last_progress = -1

    while True:
        try:
            response = requests.get(f"{api_base}/v1/tts/status/{task_id}", timeout=5)
            response.raise_for_status()
            status_data = response.json()

            status = status_data["status"]
            progress = status_data["progress"]
            message = status_data["message"]

            # Print progress if changed
            if progress != last_progress:
                elapsed = time.time() - start_time
                print(f"   [{elapsed:.1f}s] Status: {status}, Progress: {progress:.0%}, {message}")
                last_progress = progress

            if status == "completed":
                print(f"   ✓ Generation completed in {elapsed:.1f}s")
                break
            elif status == "failed":
                print(f"   ✗ Generation failed: {status_data.get('error', 'Unknown error')}")
                return False

            time.sleep(2)  # Poll every 2 seconds

        except requests.exceptions.RequestException as e:
            print(f"   ✗ Error polling status: {e}")
            return False

    # 4. Download result
    print("\n4. Downloading result...")
    output_filename = f"output_{task_id}.wav"

    try:
        response = requests.get(f"{api_base}/v1/tts/download/{task_id}", timeout=30)
        response.raise_for_status()

        with open(output_filename, "wb") as f:
            f.write(response.content)

        file_size = len(response.content) / 1024  # KB
        print(f"   ✓ Audio saved to: {output_filename} ({file_size:.1f} KB)")
    except requests.exceptions.RequestException as e:
        print(f"   ✗ Error downloading: {e}")
        return False

    # 5. List all tasks
    print("\n5. Listing recent tasks...")
    try:
        response = requests.get(f"{api_base}/v1/tts/tasks?limit=5", timeout=5)
        response.raise_for_status()
        tasks = response.json()
        print(f"   ✓ Found {len(tasks)} recent tasks")
        for task in tasks[:3]:
            print(f"      - {task['task_id']}: {task['status']} ({task['progress']:.0%})")
    except requests.exceptions.RequestException as e:
        print(f"   ✗ Error listing tasks: {e}")

    print("\n" + "=" * 60)
    print("✓ Test completed successfully!")
    print("=" * 60)
    return True


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print(__doc__)
        sys.exit(1)

    prompt_audio = sys.argv[1]
    text = sys.argv[2]
    api_base = sys.argv[3] if len(sys.argv) > 3 else "http://localhost:8000"

    success = test_api(prompt_audio, text, api_base)
    sys.exit(0 if success else 1)
