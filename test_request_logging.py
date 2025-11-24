"""
Test script for request/response logging in IndexTTS2 API
==========================================================

This script tests the enhanced logging middleware that shows:
- All incoming request details (headers, form data, files)
- All outgoing response details (headers, JSON body)

Usage:
    python test_request_logging.py
"""

import requests
import time
import os

# Configuration
API_BASE_URL = "http://localhost:8000"

def test_health_endpoint():
    """Test health endpoint with logging"""
    print("\n" + "="*60)
    print("Test 1: Health Check Endpoint")
    print("="*60)
    print("\nExpected log output:")
    print("- Request: GET /health")
    print("- Response: JSON with status, model_loaded, active_tasks, etc.")
    print("\nMaking request...")

    response = requests.get(f"{API_BASE_URL}/health")

    print(f"\n✓ Response received (Status: {response.status_code})")
    print(f"Response: {response.json()}")

    time.sleep(1)


def test_list_tasks():
    """Test list tasks endpoint"""
    print("\n" + "="*60)
    print("Test 2: List Tasks Endpoint")
    print("="*60)
    print("\nExpected log output:")
    print("- Request: GET /v1/tts/tasks")
    print("- Response: JSON array of tasks")
    print("\nMaking request...")

    response = requests.get(f"{API_BASE_URL}/v1/tts/tasks")

    print(f"\n✓ Response received (Status: {response.status_code})")
    if response.status_code == 200:
        tasks = response.json()
        print(f"Number of tasks: {len(tasks)}")

    time.sleep(1)


def test_generate_with_logging(audio_file_path=None):
    """Test generation endpoint with detailed logging"""
    print("\n" + "="*60)
    print("Test 3: Generate Speech Endpoint")
    print("="*60)
    print("\nExpected log output:")
    print("- Request: POST /v1/tts/generate")
    print("- Form data with all parameters")
    print("- File upload info (filename, size, content-type)")
    print("- Response: JSON with task_id, status, message")
    print("\nMaking request...")

    if not audio_file_path or not os.path.exists(audio_file_path):
        print("\n⚠ No audio file provided. Skipping generation test.")
        print("To test generation logging, run:")
        print(f"  python {__file__} /path/to/audio.wav")
        return

    with open(audio_file_path, 'rb') as audio_file:
        files = {
            'prompt_audio': ('test_audio.wav', audio_file, 'audio/wav')
        }

        data = {
            'text': '這是一個測試請求，用來檢查日誌功能。',
            'temperature': 0.8,
            'top_p': 0.8,
            'top_k': 30,
            'emo_weight': 0.65,
            'max_text_tokens_per_segment': 120,
            'do_sample': True,
            'length_penalty': 0.0,
            'num_beams': 3,
            'repetition_penalty': 10.0,
            'max_mel_tokens': 1500,
            'interval_silence': 200,
            'verbose': False,
            'emo_mode': 'speaker'
        }

        response = requests.post(
            f"{API_BASE_URL}/v1/tts/generate",
            files=files,
            data=data
        )

        print(f"\n✓ Response received (Status: {response.status_code})")

        if response.status_code == 200:
            result = response.json()
            task_id = result.get('task_id')
            print(f"Task ID: {task_id}")

            # Test status endpoint
            time.sleep(2)
            print("\n--- Testing Status Endpoint ---")
            status_response = requests.get(
                f"{API_BASE_URL}/v1/tts/status/{task_id}"
            )
            print(f"✓ Status response received (Status: {status_response.status_code})")

            # Cleanup
            time.sleep(1)
            print("\n--- Testing Delete Endpoint ---")
            delete_response = requests.delete(
                f"{API_BASE_URL}/v1/tts/tasks/{task_id}"
            )
            print(f"✓ Delete response received (Status: {delete_response.status_code})")

        else:
            print(f"❌ Request failed: {response.text}")

    time.sleep(1)


def test_error_response():
    """Test error response logging"""
    print("\n" + "="*60)
    print("Test 4: Error Response Logging")
    print("="*60)
    print("\nExpected log output:")
    print("- Request: GET /v1/tts/status/nonexistent")
    print("- Response: 404 error with detail message")
    print("\nMaking request...")

    response = requests.get(f"{API_BASE_URL}/v1/tts/status/nonexistent_task_id")

    print(f"\n✓ Response received (Status: {response.status_code})")
    print(f"Response: {response.json()}")

    time.sleep(1)


def main():
    """Run all logging tests"""
    print("\n" + "="*80)
    print("IndexTTS2 API - Request/Response Logging Test Suite")
    print("="*80)
    print("\nThis test suite will make several API requests to demonstrate")
    print("the enhanced logging features. Check your server logs to see:")
    print("  - Detailed request information (headers, form data, files)")
    print("  - Response details (status, headers, JSON body)")
    print("  - Request/response timing")
    print("\n" + "="*80)

    # Check if API is running
    try:
        response = requests.get(f"{API_BASE_URL}/health", timeout=5)
        if response.status_code != 200:
            print("\n❌ API is not healthy. Please start the server first.")
            return
    except Exception as e:
        print(f"\n❌ Cannot connect to API: {e}")
        print(f"Make sure the server is running at {API_BASE_URL}")
        return

    print("\n✓ API is running. Starting tests...\n")

    # Run tests
    test_health_endpoint()
    test_list_tasks()
    test_error_response()

    # Test with audio file if provided
    import sys
    if len(sys.argv) > 1:
        audio_file = sys.argv[1]
        test_generate_with_logging(audio_file)
    else:
        test_generate_with_logging()

    print("\n" + "="*80)
    print("All tests completed!")
    print("="*80)
    print("\nCheck your server logs to see the detailed request/response logs.")
    print("Each request should show:")
    print("  📥 Incoming Request - with method, path, headers, form data")
    print("  📤 Response - with status, headers, JSON body")
    print("\n")


if __name__ == "__main__":
    main()
