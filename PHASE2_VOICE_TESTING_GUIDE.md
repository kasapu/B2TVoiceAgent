# Phase 2: Voice Services Testing Guide

Complete testing guide for STT, TTS, and Voice Connector services.

## Prerequisites

1. **Docker and Docker Compose** installed
2. **At least 4GB RAM** available
3. **Network ports** 8002, 8003, 8005, 9000, 9001 available
4. **Test audio files** (provided or record your own)

## Quick Start - Full Stack

```bash
# Navigate to project
cd /home/kranti/OCPplatform

# Start all services including voice
docker compose up -d

# Wait for services to be healthy (30-60 seconds)
docker compose ps

# Check all services are running
docker compose logs -f | grep "healthy"
```

Expected services:
- ✅ ocp-postgres (healthy)
- ✅ ocp-redis (healthy)
- ✅ ocp-minio (healthy)
- ✅ ocp-orchestrator (running)
- ✅ ocp-nlu (running)
- ✅ ocp-chat-connector (running)
- ✅ ocp-stt (running)
- ✅ ocp-tts (running)
- ✅ ocp-voice-connector (running)
- ✅ ocp-chat-widget (running)
- ✅ ocp-adminer (running)

---

## Test 1: STT Service (Speech-to-Text)

### Health Check

```bash
curl http://localhost:8002/health
```

**Expected Output:**
```json
{
  "status": "healthy",
  "service": "OCP STT Service",
  "version": "1.0.0",
  "model": "base",
  "device": "cpu"
}
```

### Create Test Audio File

```bash
# Create a test WAV file (requires sox)
echo "Hello, how are you today?" | \
  text2wave -o /tmp/test_audio.wav

# OR use ffmpeg to convert any audio
ffmpeg -i input.mp3 -ar 16000 -ac 1 -f wav /tmp/test_audio.wav
```

### Test Transcription

```bash
curl -X POST "http://localhost:8002/transcribe" \
  -F "file=@/tmp/test_audio.wav" \
  -F "language=en" \
  -F "task=transcribe"
```

**Expected Output:**
```json
{
  "text": "Hello, how are you today?",
  "language": "en",
  "duration": 2.5,
  "segments": [
    {
      "id": 0,
      "start": 0.0,
      "end": 2.5,
      "text": "Hello, how are you today?"
    }
  ],
  "processing_time_ms": 850
}
```

### Verify STT Logs

```bash
docker compose logs stt-service --tail=50
```

Look for:
- ✅ Model loaded successfully
- ✅ Transcription requests processed
- ✅ No errors

---

## Test 2: MinIO Storage

### Health Check

```bash
curl http://localhost:9000/minio/health/live
```

**Expected:** Empty 200 OK response

### Access MinIO Console

1. Open browser: http://localhost:9001
2. Login:
   - Username: `minioadmin`
   - Password: `minioadmin`
3. Verify buckets exist or will be created

---

## Test 3: TTS Service (Text-to-Speech)

### Health Check

```bash
curl http://localhost:8003/health
```

**Expected Output:**
```json
{
  "status": "healthy",
  "service": "OCP TTS Service",
  "version": "1.0.0",
  "model": "tts_models/en/ljspeech/tacotron2-DDC",
  "device": "cpu",
  "minio_connected": true
}
```

### Test Synthesis

```bash
curl -X POST "http://localhost:8003/synthesize" \
  -H "Content-Type: application/json" \
  -d '{
    "text": "Hello, welcome to the OCP platform voice assistant.",
    "voice": "default",
    "speed": 1.0
  }'
```

**Expected Output:**
```json
{
  "audio_url": "http://localhost:9000/tts-audio/tts/abc123.wav?...",
  "duration_ms": 3500,
  "processing_time_ms": 1200,
  "text": "Hello, welcome to the OCP platform voice assistant.",
  "voice": "default",
  "format": "wav",
  "sample_rate": 22050
}
```

### Download and Play Audio

```bash
# Extract audio URL from response
AUDIO_URL="<paste audio_url from response>"

# Download audio
curl -o /tmp/tts_output.wav "$AUDIO_URL"

# Play audio (requires ffplay or aplay)
ffplay /tmp/tts_output.wav
# OR
aplay /tmp/tts_output.wav
```

### Verify TTS Logs

```bash
docker compose logs tts-service --tail=50
```

Look for:
- ✅ TTS model loaded
- ✅ MinIO connection successful
- ✅ Audio synthesized and uploaded
- ✅ No errors

---

## Test 4: Voice Connector Service

### Health Check

```bash
curl http://localhost:8005/health
```

**Expected Output:**
```json
{
  "status": "healthy",
  "service": "OCP Voice Connector",
  "version": "1.0.0",
  "active_calls": 0,
  "uptime_seconds": 120,
  "stt_service": "http://stt-service:8002",
  "tts_service": "http://tts-service:8003",
  "orchestrator_service": "http://orchestrator:8000"
}
```

### Check Active Calls

```bash
curl http://localhost:8005/calls
```

**Expected Output:**
```json
{
  "active_calls": 0,
  "max_calls": 100,
  "calls": []
}
```

### WebSocket Connection Test

Create a test script `test_voice_ws.py`:

```python
#!/usr/bin/env python3
import asyncio
import websockets
import json
import wave
import sys

async def test_voice_websocket():
    uri = "ws://localhost:8005/ws/voice"

    try:
        async with websockets.connect(uri) as websocket:
            print("✅ Connected to voice connector")

            # Wait for initial status
            message = await websocket.recv()
            if isinstance(message, str):
                status = json.loads(message)
                print(f"✅ Received status: {status}")

            # Wait for welcome audio
            welcome_audio = await websocket.recv()
            if isinstance(welcome_audio, bytes):
                print(f"✅ Received welcome audio ({len(welcome_audio)} bytes)")

                # Save welcome audio
                with open("/tmp/welcome.wav", "wb") as f:
                    f.write(welcome_audio)
                print("✅ Saved welcome audio to /tmp/welcome.wav")

            # Send test audio (if available)
            if len(sys.argv) > 1:
                audio_file = sys.argv[1]
                print(f"📤 Sending audio from {audio_file}")

                with open(audio_file, "rb") as f:
                    # Read WAV file and send in chunks
                    with wave.open(f, "rb") as wav:
                        chunk_size = 4096
                        data = wav.readframes(chunk_size)
                        while data:
                            await websocket.send(data)
                            data = wav.readframes(chunk_size)
                            await asyncio.sleep(0.1)  # Simulate real-time

                print("✅ Audio sent")

                # Wait for response
                response = await websocket.recv()
                if isinstance(response, bytes):
                    print(f"✅ Received response audio ({len(response)} bytes)")

                    # Save response audio
                    with open("/tmp/response.wav", "wb") as f:
                        f.write(response)
                    print("✅ Saved response audio to /tmp/response.wav")

            # End call
            await websocket.send(json.dumps({"type": "end_call"}))
            print("✅ Call ended")

    except Exception as e:
        print(f"❌ Error: {e}")
        return False

    return True

if __name__ == "__main__":
    result = asyncio.run(test_voice_websocket())
    sys.exit(0 if result else 1)
```

Run the test:

```bash
# Make it executable
chmod +x test_voice_ws.py

# Test connection only
python3 test_voice_ws.py

# Test with audio file
python3 test_voice_ws.py /tmp/test_audio.wav
```

### Verify Voice Connector Logs

```bash
docker compose logs voice-connector --tail=100 -f
```

Look for:
- ✅ WebSocket connection accepted
- ✅ Call manager started
- ✅ Session created
- ✅ Welcome message sent
- ✅ Audio processing pipeline working
- ✅ No errors

---

## Test 5: Full Voice Integration

### Test Orchestrator Voice Endpoints

#### Create Voice Session

```bash
curl -X POST "http://localhost:8000/api/v1/session" \
  -H "Content-Type: application/json" \
  -d '{"channel": "voice"}'
```

**Expected Output:**
```json
{
  "session_id": "abc123-def456-ghi789"
}
```

#### Send Voice Message

```bash
SESSION_ID="<paste session_id from above>"

curl -X POST "http://localhost:8000/api/v1/conversation" \
  -H "Content-Type: application/json" \
  -d "{
    \"session_id\": \"$SESSION_ID\",
    \"user_message\": \"Hello, I want to check my balance\",
    \"channel\": \"voice\"
  }"
```

**Expected Output:**
```json
{
  "response": "Hello! I can help you check your balance. Your current account balance is $1,234.56...",
  "intent": "check_balance",
  "entities": {},
  "session_id": "abc123-def456-ghi789",
  "metadata": {
    "confidence": 0.95,
    "turn_number": 1
  }
}
```

---

## Test 6: End-to-End Voice Conversation

### Complete Flow Test

This tests the full pipeline:
1. Client connects via WebSocket
2. Sends audio → STT transcribes
3. Transcription → Orchestrator processes
4. Response → TTS synthesizes
5. Audio → Client receives

```bash
# Run the full test
python3 test_voice_ws.py /tmp/test_audio.wav

# Check all logs
docker compose logs --tail=50 voice-connector stt-service tts-service orchestrator
```

### Expected Flow in Logs

**Voice Connector:**
```
WebSocket connection accepted
Call abc123 started successfully
Processing buffered audio (size: 44100 bytes)
Transcribed: 'Hello, I want to check my balance'
Got response: 'Your current balance is $1,234.56...'
Turn 1 completed
```

**STT Service:**
```
Transcription request received (size: 44100 bytes)
Transcription successful: 'Hello, I want to check my balance'
Processing time: 850ms
```

**TTS Service:**
```
Synthesis request: 'Your current balance is $1,234.56...'
Audio synthesized (duration: 3500ms)
Uploaded to MinIO: tts/abc123.wav
```

**Orchestrator:**
```
Voice session abc123: Processing: 'Hello, I want to check my balance'
Voice session abc123: Intent: check_balance (0.95)
Voice session abc123: Response: 'Your current balance is...'
```

---

## Troubleshooting

### Service Won't Start

```bash
# Check logs
docker compose logs <service-name>

# Common issues:
# 1. Port already in use
sudo lsof -i :8002  # Check STT port
sudo lsof -i :8003  # Check TTS port
sudo lsof -i :8005  # Check Voice Connector port

# 2. Missing models
ls -la ml-models/stt
ls -la ml-models/tts

# 3. Permission issues
sudo chown -R $USER:$USER ml-models/
```

### STT Transcription Fails

```bash
# Check audio format
ffprobe /tmp/test_audio.wav

# Should be:
# - Sample rate: 16000 Hz
# - Channels: 1 (mono)
# - Format: WAV, PCM 16-bit

# Convert if needed
ffmpeg -i input.mp3 -ar 16000 -ac 1 -f wav output.wav
```

### TTS Synthesis Fails

```bash
# Check MinIO connection
docker compose logs tts-service | grep -i minio

# Check MinIO is accessible
curl http://localhost:9000/minio/health/live

# Restart TTS service
docker compose restart tts-service
```

### Voice Connector WebSocket Fails

```bash
# Check service dependencies
docker compose ps

# All required services should be running:
# - orchestrator
# - stt-service
# - tts-service

# Check WebSocket endpoint
curl http://localhost:8005/health

# Check logs for errors
docker compose logs voice-connector --tail=100
```

### No Audio Response

```bash
# Verify full pipeline
# 1. Check STT working
curl -X POST "http://localhost:8002/transcribe" -F "file=@/tmp/test.wav"

# 2. Check orchestrator working
curl http://localhost:8000/health

# 3. Check TTS working
curl -X POST "http://localhost:8003/synthesize" \
  -H "Content-Type: application/json" \
  -d '{"text":"test"}'

# 4. Check MinIO accessible
curl http://localhost:9000/minio/health/live
```

---

## Performance Benchmarks

### Expected Latencies

| Component | Expected | Acceptable | Poor |
|-----------|----------|------------|------|
| STT Transcription (5s audio) | < 1s | < 2s | > 3s |
| TTS Synthesis (20 words) | < 1.5s | < 3s | > 5s |
| Orchestrator Processing | < 300ms | < 500ms | > 1s |
| End-to-End Turn | < 3s | < 5s | > 8s |
| WebSocket Latency | < 50ms | < 100ms | > 200ms |

### Load Testing

```bash
# Test concurrent calls (requires hey or ab)
hey -n 100 -c 10 -m POST \
  -H "Content-Type: application/json" \
  -d '{"text":"test"}' \
  http://localhost:8003/synthesize
```

---

## Success Criteria

✅ All 11 Docker containers running
✅ STT health check passes
✅ TTS health check passes
✅ Voice Connector health check passes
✅ STT can transcribe test audio
✅ TTS can synthesize test text
✅ MinIO accessible and working
✅ WebSocket connection succeeds
✅ Welcome audio received
✅ Full conversation turn completes
✅ All logs show no errors
✅ End-to-end latency < 5 seconds

---

## Next Steps After Testing

1. **Optimize Performance:**
   - Switch to GPU for STT/TTS
   - Use smaller models for faster inference
   - Tune VAD parameters

2. **Add Monitoring:**
   - Prometheus metrics
   - Grafana dashboards
   - Alert rules

3. **Production Hardening:**
   - Add authentication
   - Rate limiting
   - Error recovery
   - Graceful degradation

4. **Feature Enhancements:**
   - Multi-language support
   - Voice selection
   - Background noise filtering
   - Conversation context

---

## Useful Commands

```bash
# Start all services
docker compose up -d

# Start only voice services
docker compose up -d minio stt-service tts-service voice-connector

# Stop all services
docker compose down

# Restart voice services
docker compose restart stt-service tts-service voice-connector

# View logs
docker compose logs -f voice-connector

# Check resource usage
docker stats

# Clean up
docker compose down -v  # WARNING: Deletes volumes

# Rebuild services
docker compose up -d --build
```

---

**Phase 2 Complete! 🎉**

You now have a fully functional voice conversation system with:
- Speech-to-Text (Whisper)
- Text-to-Speech (Coqui TTS)
- Real-time WebSocket voice calls
- Complete integration with orchestrator and NLU
