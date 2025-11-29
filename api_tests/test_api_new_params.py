"""
Test script for IndexTTS2 API with new parameters
==================================================

This script tests the newly added parameters:
- Advanced generation control: do_sample, length_penalty, num_beams, repetition_penalty, max_mel_tokens
- Segmentation control: interval_silence, quick_streaming_tokens, verbose

Usage:
    python test_api_new_params.py
"""

import requests
import time
import os

# Configuration
API_BASE_URL = "http://localhost:8000"
TEST_AUDIO = "./test_prompt.wav"  # Replace with your test audio file
TEST_TEXT = "你好，這是一個測試。今天天氣很好。"

def test_health():
    """Test health endpoint"""
    print("\n" + "="*60)
    print("Testing /health endpoint...")
    print("="*60)

    response = requests.get(f"{API_BASE_URL}/health")
    print(f"Status: {response.status_code}")
    print(f"Response: {response.json()}")
    return response.status_code == 200

def test_generate_with_new_params():
    """Test generation with new advanced parameters"""
    print("\n" + "="*60)
    print("Testing /v1/tts/generate with new parameters...")
    print("="*60)

    if not os.path.exists(TEST_AUDIO):
        print(f"❌ Test audio file not found: {TEST_AUDIO}")
        print("Please provide a valid audio file for testing.")
        return False

    # Test with custom advanced parameters
    test_configs = [
        {
            "name": "Default parameters",
            "params": {}
        },
        {
            "name": "High quality (more beams, higher repetition penalty)",
            "params": {
                "num_beams": 5,
                "repetition_penalty": 15.0,
                "max_mel_tokens": 2000
            }
        },
        {
            "name": "Fast generation (fewer beams)",
            "params": {
                "num_beams": 1,
                "do_sample": False,
                "max_mel_tokens": 1000
            }
        },
        {
            "name": "Long pauses between segments",
            "params": {
                "interval_silence": 500
            }
        },
        {
            "name": "Verbose logging enabled",
            "params": {
                "verbose": True
            }
        }
    ]

    for config in test_configs:
        print(f"\n--- Test: {config['name']} ---")

        with open(TEST_AUDIO, 'rb') as audio_file:
            files = {
                'prompt_audio': ('test.wav', audio_file, 'audio/wav')
            }

            data = {
                'text': TEST_TEXT,
                **config['params']
            }

            print(f"Parameters: {data}")
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
                max_wait = 60  # seconds
                start_time = time.time()

                while time.time() - start_time < max_wait:
                    status_response = requests.get(
                        f"{API_BASE_URL}/v1/tts/status/{task_id}"
                    )
                    status = status_response.json()

                    print(f"  Status: {status['status']}, Progress: {status['progress']:.2%}")

                    if status['status'] == 'completed':
                        print(f"✓ Generation completed!")

                        # Test download
                        download_response = requests.get(
                            f"{API_BASE_URL}/v1/tts/download/{task_id}"
                        )

                        if download_response.status_code == 200:
                            output_file = f"test_output_{task_id}.wav"
                            with open(output_file, 'wb') as f:
                                f.write(download_response.content)
                            print(f"✓ Audio saved to: {output_file}")

                            # Cleanup
                            delete_response = requests.delete(
                                f"{API_BASE_URL}/v1/tts/tasks/{task_id}"
                            )
                            if delete_response.status_code == 200:
                                print(f"✓ Task cleaned up")
                        break

                    elif status['status'] == 'failed':
                        print(f"❌ Generation failed: {status.get('error', 'Unknown error')}")
                        break

                    time.sleep(2)
                else:
                    print(f"⚠ Timeout waiting for task completion")

            else:
                print(f"❌ Request failed: {response.status_code}")
                print(f"Response: {response.text}")
                return False

    return True

def test_parameter_validation():
    """Test parameter validation"""
    print("\n" + "="*60)
    print("Testing parameter validation...")
    print("="*60)

    invalid_tests = [
        {
            "name": "Invalid num_beams (too high)",
            "params": {"num_beams": 20},
            "expected_error": "num_beams"
        },
        {
            "name": "Invalid repetition_penalty (too high)",
            "params": {"repetition_penalty": 30.0},
            "expected_error": "repetition_penalty"
        },
        {
            "name": "Invalid max_mel_tokens (too low)",
            "params": {"max_mel_tokens": 50},
            "expected_error": "max_mel_tokens"
        },
        {
            "name": "Invalid interval_silence (negative)",
            "params": {"interval_silence": -100},
            "expected_error": "interval_silence"
        }
    ]

    if not os.path.exists(TEST_AUDIO):
        print(f"⚠ Skipping validation tests - test audio not found")
        return True

    for test in invalid_tests:
        print(f"\n--- Test: {test['name']} ---")

        with open(TEST_AUDIO, 'rb') as audio_file:
            files = {
                'prompt_audio': ('test.wav', audio_file, 'audio/wav')
            }

            data = {
                'text': TEST_TEXT,
                **test['params']
            }

            response = requests.post(
                f"{API_BASE_URL}/v1/tts/generate",
                files=files,
                data=data
            )

            if response.status_code == 422:
                print(f"✓ Validation error correctly returned")
            else:
                print(f"⚠ Expected 422, got {response.status_code}")

    return True

def main():
    """Run all tests"""
    print("\n" + "="*60)
    print("IndexTTS2 API - New Parameters Test Suite")
    print("="*60)

    # Test health
    if not test_health():
        print("\n❌ API is not healthy. Make sure the server is running.")
        return

    # Test parameter validation
    test_parameter_validation()

    # Test generation with new parameters
    if not os.path.exists(TEST_AUDIO):
        print(f"\n⚠ Please create a test audio file at: {TEST_AUDIO}")
        print("Then run this script again to test generation endpoints.")
    else:
        test_generate_with_new_params()

    print("\n" + "="*60)
    print("Test suite completed!")
    print("="*60)

if __name__ == "__main__":
    main()
