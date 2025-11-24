# Audio Format Support in IndexTTS2 API

## Supported Input Formats

The IndexTTS2 API supports a wide range of audio formats through `librosa` and FFmpeg:

### Common Formats
- **WAV** (.wav) - Uncompressed audio (recommended for best quality)
- **MP3** (.mp3) - MPEG Audio Layer 3
- **AAC** (.aac, .m4a) - Advanced Audio Coding
- **FLAC** (.flac) - Free Lossless Audio Codec
- **OGG** (.ogg) - Ogg Vorbis
- **OPUS** (.opus) - Opus codec

### Additional Supported Formats
- **WMA** (.wma) - Windows Media Audio
- **AIFF** (.aiff) - Audio Interchange File Format
- **AU** (.au) - Sun/NeXT audio format
- **RAW** (.raw) - Raw audio data

## Output Format

All generated audio is output in **WAV format**:
- Sample rate: 22,050 Hz
- Bit depth: 16-bit PCM
- Channels: Mono

## File Requirements

### Size Limits
- Maximum file size: **10 MB**
- Recommended duration: **3-15 seconds** of clean speech

### Audio Quality Recommendations
For best results, your input audio should:
- Contain clear, single-speaker speech
- Have minimal background noise
- Be 3-15 seconds in length
- Use a sample rate of 16kHz or higher

## API Usage Examples

### Example 1: Using MP3 Input

```bash
curl -X POST "http://localhost:8000/v1/tts/generate" \
  -F "text=你好，世界！" \
  -F "prompt_audio=@speaker_voice.mp3"
```

### Example 2: Using AAC/M4A Input

```bash
curl -X POST "http://localhost:8000/v1/tts/generate" \
  -F "text=Hello, this is a test." \
  -F "prompt_audio=@speaker_voice.m4a"
```

### Example 3: Using FLAC Input with Emotion Reference

```bash
curl -X POST "http://localhost:8000/v1/tts/generate" \
  -F "text=今天天氣很好" \
  -F "prompt_audio=@speaker_voice.flac" \
  -F "emo_audio=@emotion_reference.ogg" \
  -F "emo_mode=reference"
```

### Example 4: Python with Different Formats

```python
import requests

# Using MP3 for speaker and OGG for emotion
with open('speaker.mp3', 'rb') as speaker, \
     open('emotion.ogg', 'rb') as emotion:

    files = {
        'prompt_audio': ('speaker.mp3', speaker, 'audio/mpeg'),
        'emo_audio': ('emotion.ogg', emotion, 'audio/ogg')
    }

    data = {
        'text': '你好，這是測試',
        'emo_mode': 'reference'
    }

    response = requests.post(
        'http://localhost:8000/v1/tts/generate',
        files=files,
        data=data
    )

    task_id = response.json()['task_id']
    print(f"Task created: {task_id}")
```

## Converting Audio Formats

If you need to convert audio files to a supported format, you can use FFmpeg:

### Install FFmpeg

**macOS:**
```bash
brew install ffmpeg
```

**Ubuntu/Debian:**
```bash
sudo apt-get install ffmpeg
```

**Windows:**
Download from https://ffmpeg.org/download.html

### Conversion Examples

```bash
# Convert to WAV
ffmpeg -i input.mp3 output.wav

# Convert to MP3 with specific bitrate
ffmpeg -i input.wav -codec:a libmp3lame -b:a 192k output.mp3

# Convert to AAC/M4A
ffmpeg -i input.wav -codec:a aac -b:a 192k output.m4a

# Convert to FLAC (lossless)
ffmpeg -i input.wav -codec:a flac output.flac

# Convert to OGG Vorbis
ffmpeg -i input.wav -codec:a libvorbis -q:a 5 output.ogg

# Resample to 22.05kHz (matches output format)
ffmpeg -i input.mp3 -ar 22050 output.wav
```

## Format Validation

The API performs the following validations:

1. **File Extension Check**: Ensures the file has a supported extension
2. **Size Check**: Maximum 10MB per file
3. **MIME Type Check**: Logs warnings for unusual MIME types (non-blocking)

### Error Handling

If an unsupported format is uploaded, you'll receive a `400 Bad Request` error:

```json
{
  "detail": "Unsupported audio format: .txt. Supported formats: .aac, .aiff, .au, .flac, .m4a, .mp3, .ogg, .opus, .raw, .wav, .wma"
}
```

## Technical Details

### Audio Processing Pipeline

1. **Upload**: Client uploads audio in any supported format
2. **Storage**: File is saved with original extension
3. **Loading**: `librosa.load()` reads the file (uses FFmpeg backend)
4. **Processing**: Audio is resampled to 16kHz for feature extraction
5. **Generation**: TTS model generates speech
6. **Output**: Result is saved as 22.05kHz WAV

### Why Multiple Formats?

- **Flexibility**: Accept audio from various sources (mobile apps, web recordings, etc.)
- **Compatibility**: Work with existing audio libraries and tools
- **Convenience**: No need for manual conversion before uploading

### Performance Considerations

- **WAV**: Fastest to process (no decompression needed)
- **FLAC**: Fast, lossless compression
- **MP3/AAC**: Slightly slower due to decompression, but negligible difference
- **All formats**: Processed identically after loading, no quality difference

## Troubleshooting

### Problem: "Unsupported audio format" error

**Solution**: Check your file extension matches a supported format. If using a valid format, ensure the file is not corrupted.

### Problem: "Audio too large" error

**Solution**:
- Compress your audio file (MP3, AAC, or OGG instead of WAV)
- Reduce file size with FFmpeg:
  ```bash
  ffmpeg -i large_file.wav -ar 22050 -ac 1 -b:a 128k smaller_file.mp3
  ```

### Problem: Poor quality output

**Solution**:
- Use higher quality input (WAV or FLAC recommended)
- Ensure input audio has clear speech
- Avoid heavily compressed formats with low bitrates
- Check input audio is 3-15 seconds long

## FAQ

**Q: Which format gives the best quality?**
A: WAV and FLAC provide the best quality as they are uncompressed or losslessly compressed. However, high-bitrate MP3 (192kbps+) or AAC is usually indistinguishable.

**Q: Can I use video files (MP4, AVI)?**
A: No, only audio files are supported. Extract audio from video first:
```bash
ffmpeg -i video.mp4 -vn -acodec copy audio.m4a
```

**Q: Why is output always WAV?**
A: WAV is uncompressed and provides the highest quality. You can convert to other formats after download using FFmpeg.

**Q: Does format affect processing speed?**
A: Minimal impact. Decompression overhead is negligible compared to TTS generation time.

**Q: Can I use streaming formats like RTMP or HLS?**
A: No, only complete audio files are supported. You need to record/download the stream first.
