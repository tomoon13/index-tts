# Request/Response Logging in IndexTTS2 API

## Overview

The IndexTTS2 API includes comprehensive request/response logging middleware that captures all details of incoming requests and outgoing responses. This is useful for:

- **Debugging**: See exactly what clients are sending
- **Monitoring**: Track API usage patterns
- **Troubleshooting**: Diagnose issues with request parameters
- **Security**: Audit API access (sensitive headers are redacted)

## Log Format

Each request generates a structured log with the following sections:

### 1. Incoming Request (`📥`)

```
================================================================================
📥 Incoming Request [abc12345]
================================================================================
Method:      POST
Path:        /v1/tts/generate
Client:      127.0.0.1:52341
User-Agent:  python-requests/2.31.0

Headers:
  host: localhost:8000
  accept: */*
  content-type: multipart/form-data; boundary=...
  content-length: 1234567

Form Data: (multipart/form-data)
  text: 你好，世界！這是一個測試。
  prompt_audio: [FILE] speaker.mp3 (0.85 MB, audio/mpeg)
  temperature: 0.8
  top_p: 0.8
  top_k: 30
  emo_mode: speaker
  do_sample: True
  num_beams: 3
  repetition_penalty: 10.0
  max_mel_tokens: 1500
  interval_silence: 200
================================================================================
```

### 2. Outgoing Response (`📤`)

```
📤 Response [abc12345]
Status:      200
Process Time: 0.123s

Response Headers:
  content-type: application/json
  content-length: 125

Response Body (JSON):
{
  "task_id": "def67890abcdef12",
  "status": "pending",
  "message": "Task created successfully"
}
================================================================================
```

## What Gets Logged

### Request Information

| Field | Description | Example |
|-------|-------------|---------|
| Request ID | Unique 8-char identifier for tracking | `abc12345` |
| Method | HTTP method | `POST`, `GET`, `DELETE` |
| Path | URL path | `/v1/tts/generate` |
| Client | Client IP and port | `127.0.0.1:52341` |
| User-Agent | Client software | `python-requests/2.31.0` |
| Query Params | URL query parameters | `?status=pending&limit=10` |
| Headers | HTTP headers (sensitive ones redacted) | See below |
| Form Data | Multipart form fields and files | Text params + file uploads |
| JSON Body | For JSON requests | Pretty-printed JSON |

### Response Information

| Field | Description | Example |
|-------|-------------|---------|
| Status | HTTP status code | `200`, `400`, `404`, `500` |
| Process Time | Request processing duration | `0.123s`, `2.456s` |
| Response Headers | HTTP response headers | `content-type`, `content-length` |
| Response Body | Response content (for JSON) | Pretty-printed JSON |

## File Upload Logging

For file uploads, the log shows:
- **Filename**: Original uploaded filename
- **Size**: File size in MB
- **Content-Type**: MIME type of the file

Example:
```
prompt_audio: [FILE] my_voice.mp3 (1.23 MB, audio/mpeg)
emo_audio: [FILE] emotion.wav (0.45 MB, audio/wav)
```

## Security Features

### Redacted Headers

Sensitive headers are automatically redacted for security:

| Header | Logged As |
|--------|-----------|
| `Authorization` | `[REDACTED]` |
| `Cookie` | `[REDACTED]` |
| `X-API-Key` | `[REDACTED]` |

### Truncated Values

Long text values are truncated to prevent log flooding:
- Text fields longer than 100 characters are truncated with `...`
- Response bodies are limited to 500 characters for non-JSON responses

## Response Types

### JSON Responses

Full JSON responses are logged with pretty-printing:

```
Response Body (JSON):
{
  "task_id": "abc123",
  "status": "completed",
  "progress": 1.0,
  "message": "Generation completed",
  "output_file": "/path/to/output.wav"
}
```

### Audio Responses

Audio file responses show size information:

```
Response Body: [AUDIO FILE - 1234567 bytes]
```

### Error Responses

Error responses are logged with full details:

```
Response Body (JSON):
{
  "detail": "Text too long (max 500 characters)"
}
```

## Example Log Outputs

### Example 1: Successful Generation Request

```
================================================================================
📥 Incoming Request [1a2b3c4d]
================================================================================
Method:      POST
Path:        /v1/tts/generate
Client:      192.168.1.100:54321
User-Agent:  Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)

Headers:
  host: api.example.com
  accept: application/json
  content-type: multipart/form-data; boundary=----WebKitFormBoundary...

Form Data: (multipart/form-data)
  text: 今天天氣很好，適合出去走走。
  prompt_audio: [FILE] speaker_voice.mp3 (0.92 MB, audio/mpeg)
  speech_length: 0
  temperature: 0.8
  top_p: 0.8
  top_k: 30
  emo_weight: 0.65
  max_text_tokens_per_segment: 120
  do_sample: True
  length_penalty: 0.0
  num_beams: 3
  repetition_penalty: 10.0
  max_mel_tokens: 1500
  interval_silence: 200
  quick_streaming_tokens: 0
  verbose: False
  emo_mode: speaker
================================================================================

📤 Response [1a2b3c4d]
Status:      200
Process Time: 0.156s

Response Headers:
  content-type: application/json
  content-length: 98

Response Body (JSON):
{
  "task_id": "5e6f7g8h9i0j1k2l",
  "status": "pending",
  "message": "Task created successfully"
}
================================================================================
```

### Example 2: Status Check Request

```
================================================================================
📥 Incoming Request [9z8y7x6w]
================================================================================
Method:      GET
Path:        /v1/tts/status/5e6f7g8h9i0j1k2l
Client:      192.168.1.100:54322
User-Agent:  python-requests/2.31.0

Headers:
  host: api.example.com
  accept: application/json
================================================================================

📤 Response [9z8y7x6w]
Status:      200
Process Time: 0.003s

Response Headers:
  content-type: application/json
  content-length: 234

Response Body (JSON):
{
  "task_id": "5e6f7g8h9i0j1k2l",
  "status": "processing",
  "progress": 0.45,
  "message": "speech synthesis 2/3...",
  "created_at": "2025-01-24T10:30:00.123456",
  "completed_at": null,
  "output_file": null,
  "error": null,
  "queue_position": null
}
================================================================================
```

### Example 3: Error Response

```
================================================================================
📥 Incoming Request [5v4u3t2s]
================================================================================
Method:      POST
Path:        /v1/tts/generate
Client:      192.168.1.105:12345
User-Agent:  curl/7.88.1

Form Data: (multipart/form-data)
  text: 這是一個超過五百字的非常非常長的文本測試...
  prompt_audio: [FILE] test.mp3 (0.50 MB, audio/mpeg)
================================================================================

📤 Response [5v4u3t2s]
Status:      400
Process Time: 0.012s

Response Headers:
  content-type: application/json
  content-length: 67

Response Body (JSON):
{
  "detail": "Text too long (max 500 characters)"
}
================================================================================
```

### Example 4: Audio Download Request

```
================================================================================
📥 Incoming Request [3r2q1p0o]
================================================================================
Method:      GET
Path:        /v1/tts/download/5e6f7g8h9i0j1k2l
Client:      192.168.1.100:54323
User-Agent:  python-requests/2.31.0

Headers:
  host: api.example.com
  accept: */*
================================================================================

📤 Response [3r2q1p0o]
Status:      200
Process Time: 0.045s

Response Headers:
  content-type: audio/wav
  content-length: 2456789
  content-disposition: attachment; filename=5e6f7g8h9i0j1k2l.wav

Response Body: [AUDIO FILE - 2456789 bytes]
================================================================================
```

## Performance Impact

The logging middleware has minimal performance impact:

- **Small requests** (< 1KB): ~0.5-1ms overhead
- **File uploads**: ~1-3ms overhead
- **JSON responses**: ~0.5-2ms overhead (for parsing and formatting)
- **Audio responses**: Negligible (no body reading)

Total overhead is typically **< 0.1%** of total request processing time.

## Disabling Logging

If you need to disable request logging for performance reasons, you can comment out the middleware registration in `api.py`:

```python
# Add middleware to app
# app.add_middleware(RequestLoggingMiddleware)  # Comment this line
```

## Log Rotation

For production use, consider:

1. **Redirect logs to file**:
   ```bash
   python api.py > logs/api.log 2>&1
   ```

2. **Use log rotation**:
   ```bash
   python api.py | rotatelogs logs/api-%Y-%m-%d.log 86400
   ```

3. **Use systemd/supervisor** with log management

## Best Practices

1. **Monitor log size**: Logs can grow quickly with many requests
2. **Filter sensitive data**: Add more headers to `sensitive_headers` if needed
3. **Use log aggregation**: Send logs to ELK, Splunk, or similar for analysis
4. **Set up alerts**: Monitor for error patterns (4xx, 5xx responses)
5. **Archive old logs**: Keep logs for 30-90 days depending on requirements

## Troubleshooting with Logs

### Problem: "Task not found" error

Check the logs for:
- Was the task created successfully? (Look for 200 response)
- What task_id was returned?
- Is the client using the correct task_id?

### Problem: "Unsupported audio format" error

Check the logs for:
- What file extension was uploaded?
- What MIME type was sent?
- Is the file actually an audio file?

### Problem: Slow responses

Check the logs for:
- Process Time values
- Large file uploads (> 5MB)
- Many concurrent requests

### Problem: Authentication issues

Check the logs for:
- Authorization header (will show [REDACTED])
- Client IP address
- User-Agent string
