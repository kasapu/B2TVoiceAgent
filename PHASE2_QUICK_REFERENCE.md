# Phase 2: Voice Services - Quick Reference

**Quick commands and endpoints for Phase 2 voice services**

---

## 🚀 Start/Stop Commands

```bash
# Start everything
cd /home/kranti/OCPplatform
docker compose up -d

# Start only voice services
docker compose up -d minio stt-service tts-service voice-connector

# Stop all
docker compose down

# Restart voice services
docker compose restart stt-service tts-service voice-connector

# View logs
docker compose logs -f voice-connector
docker compose logs -f stt-service
docker compose logs -f tts-service

# Check status
docker compose ps
```

---

## 🌐 Service URLs

| Service | URL | Purpose |
|---------|-----|---------|
| **Orchestrator** | http://localhost:8000 | Main orchestrator API |
| **NLU** | http://localhost:8001 | Intent/entity extraction |
| **STT** | http://localhost:8002 | Speech-to-Text |
| **TTS** | http://localhost:8003 | Text-to-Speech |
| **Chat WebSocket** | ws://localhost:8004 | Chat connector |
| **Voice WebSocket** | ws://localhost:8005 | Voice connector |
| **MinIO** | http://localhost:9000 | Object storage |
| **MinIO Console** | http://localhost:9001 | MinIO admin UI |
| **Chat Widget** | http://localhost:3000 | React chat UI |
| **Adminer** | http://localhost:8080 | Database UI |

---

## ✅ Health Checks

```bash
# Check all services at once
for port in 8000 8001 8002 8003 8005; do
  echo "Port $port:"
  curl -s http://localhost:$port/health | jq -r '.status' 2>/dev/null || echo "ERROR"
done

# MinIO
curl http://localhost:9000/minio/health/live
```

---

## 🎤 STT Service (Port 8002)

### Health Check
```bash
curl http://localhost:8002/health
```

### Transcribe Audio
```bash
curl -X POST "http://localhost:8002/transcribe" \
  -F "file=@audio.wav" \
  -F "language=en" \
  -F "task=transcribe"
```

### Create Test Audio (requires sox)
```bash
echo "Hello, how are you?" | text2wave -o test.wav
```

### Convert Audio to WAV (requires ffmpeg)
```bash
ffmpeg -i input.mp3 -ar 16000 -ac 1 -f wav output.wav
```

---

## 🔊 TTS Service (Port 8003)

### Health Check
```bash
curl http://localhost:8003/health
```

### Synthesize Speech
```bash
curl -X POST "http://localhost:8003/synthesize" \
  -H "Content-Type: application/json" \
  -d '{
    "text": "Hello, welcome to the platform!",
    "voice": "default",
    "speed": 1.0
  }'
```

### List Voices
```bash
curl http://localhost:8003/voices
```

### Download and Play Audio
```bash
# Get audio URL from synthesis response
AUDIO_URL="<paste-url-here>"

# Download
curl -o output.wav "$AUDIO_URL"

# Play (requires ffplay or aplay)
ffplay output.wav
# OR
aplay output.wav
```

---

## 📞 Voice Connector (Port 8005)

### Health Check
```bash
curl http://localhost:8005/health
```

### Get Active Calls
```bash
curl http://localhost:8005/calls
```

### WebSocket Connection (Python)
```python
import asyncio
import websockets

async def test_voice():
    async with websockets.connect("ws://localhost:8005/ws/voice") as ws:
        # Receive status
        msg = await ws.recv()
        print(f"Status: {msg}")

        # Receive welcome audio
        audio = await ws.recv()
        print(f"Welcome audio: {len(audio)} bytes")

asyncio.run(test_voice())
```

### WebSocket Connection (JavaScript)
```javascript
const ws = new WebSocket('ws://localhost:8005/ws/voice');

ws.onopen = () => console.log('Connected');
ws.onmessage = (event) => {
  if (event.data instanceof Blob) {
    console.log('Received audio:', event.data.size, 'bytes');
  } else {
    console.log('Received message:', JSON.parse(event.data));
  }
};
```

---

## 🎯 Orchestrator Voice API (Port 8000)

### Create Voice Session
```bash
curl -X POST "http://localhost:8000/api/v1/session" \
  -H "Content-Type: application/json" \
  -d '{"channel": "voice"}'
```

### Send Voice Message
```bash
SESSION_ID="<your-session-id>"

curl -X POST "http://localhost:8000/api/v1/conversation" \
  -H "Content-Type: application/json" \
  -d "{
    \"session_id\": \"$SESSION_ID\",
    \"user_message\": \"Hello, I want to check my balance\",
    \"channel\": \"voice\"
  }"
```

---

## 💾 MinIO Storage

### Access MinIO Console
1. Open: http://localhost:9001
2. Login: `minioadmin` / `minioadmin`
3. Browse buckets: `tts-audio`

### Health Check
```bash
curl http://localhost:9000/minio/health/live
```

---

## 🔍 Troubleshooting

### Check Logs
```bash
# All voice services
docker compose logs -f stt-service tts-service voice-connector

# Specific service
docker compose logs --tail=100 stt-service

# Follow live logs
docker compose logs -f voice-connector
```

### Restart Services
```bash
# Restart all voice services
docker compose restart stt-service tts-service voice-connector minio

# Rebuild and restart
docker compose up -d --build stt-service
```

### Check Ports
```bash
# Check if port is in use
sudo lsof -i :8002  # STT
sudo lsof -i :8003  # TTS
sudo lsof -i :8005  # Voice Connector
sudo lsof -i :9000  # MinIO
```

### Check Container Status
```bash
# Detailed status
docker compose ps

# Resource usage
docker stats ocp-stt ocp-tts ocp-voice-connector

# Container logs
docker logs ocp-stt
```

### Common Issues

**STT Not Responding:**
```bash
# Check if running
docker compose ps stt-service

# Check logs
docker compose logs stt-service

# Restart
docker compose restart stt-service
```

**TTS Synthesis Fails:**
```bash
# Check MinIO connection
docker compose logs tts-service | grep -i minio

# Restart both
docker compose restart minio tts-service
```

**Voice Connector WebSocket Fails:**
```bash
# Check dependencies
docker compose ps orchestrator stt-service tts-service

# Check logs
docker compose logs voice-connector --tail=50

# Restart
docker compose restart voice-connector
```

---

## 📊 Testing Checklist

```bash
# 1. Services running
docker compose ps | grep -E "(stt|tts|voice|minio)"

# 2. Health checks pass
curl http://localhost:8002/health | jq .status
curl http://localhost:8003/health | jq .status
curl http://localhost:8005/health | jq .status
curl http://localhost:9000/minio/health/live

# 3. STT transcription works
curl -X POST "http://localhost:8002/transcribe" \
  -F "file=@test.wav" -F "language=en" | jq .text

# 4. TTS synthesis works
curl -X POST "http://localhost:8003/synthesize" \
  -H "Content-Type: application/json" \
  -d '{"text":"test"}' | jq .audio_url

# 5. Voice connector accepts connections
curl http://localhost:8005/calls | jq .active_calls
```

---

## 🎨 Example: Complete Voice Turn

```bash
# 1. Create session
SESSION=$(curl -s -X POST "http://localhost:8000/api/v1/session" \
  -H "Content-Type: application/json" \
  -d '{"channel":"voice"}' | jq -r .session_id)

echo "Session: $SESSION"

# 2. Transcribe user audio
TRANSCRIPTION=$(curl -s -X POST "http://localhost:8002/transcribe" \
  -F "file=@user_audio.wav" -F "language=en" | jq -r .text)

echo "User said: $TRANSCRIPTION"

# 3. Get bot response
RESPONSE=$(curl -s -X POST "http://localhost:8000/api/v1/conversation" \
  -H "Content-Type: application/json" \
  -d "{
    \"session_id\": \"$SESSION\",
    \"user_message\": \"$TRANSCRIPTION\",
    \"channel\": \"voice\"
  }" | jq -r .response)

echo "Bot says: $RESPONSE"

# 4. Synthesize bot response
AUDIO_URL=$(curl -s -X POST "http://localhost:8003/synthesize" \
  -H "Content-Type: application/json" \
  -d "{\"text\":\"$RESPONSE\"}" | jq -r .audio_url)

echo "Audio URL: $AUDIO_URL"

# 5. Download and play
curl -o bot_response.wav "$AUDIO_URL"
ffplay bot_response.wav
```

---

## 📁 Important File Locations

```
/home/kranti/OCPplatform/
├── services/
│   ├── stt-service/          # STT implementation
│   ├── tts-service/          # TTS implementation
│   └── voice-connector/      # Voice WebSocket
├── docker-compose.yml        # Service configuration
├── .env                      # Environment variables
├── ml-models/
│   ├── stt/                  # STT models (auto-downloaded)
│   └── tts/                  # TTS models (auto-downloaded)
├── audio-storage/            # MinIO data
└── tmp/                      # Temporary audio files
```

---

## 🔐 Default Credentials

| Service | Username | Password |
|---------|----------|----------|
| MinIO Console | minioadmin | minioadmin |
| Adminer | postgres | ocpuser / ocppassword |

---

## 🎯 Quick Performance Benchmarks

```bash
# STT performance test
time curl -X POST "http://localhost:8002/transcribe" \
  -F "file=@test_5sec.wav" -F "language=en" > /dev/null

# TTS performance test
time curl -X POST "http://localhost:8003/synthesize" \
  -H "Content-Type: application/json" \
  -d '{"text":"This is a test message"}' > /dev/null

# Expected: 1-3 seconds each (CPU mode)
```

---

## 📚 Documentation Files

- **PHASE2_COMPLETION_SUMMARY.md** - Complete overview
- **PHASE2_VOICE_TESTING_GUIDE.md** - Detailed testing guide
- **PHASE2_QUICK_REFERENCE.md** - This file
- **services/stt-service/README.md** - STT documentation
- **services/tts-service/README.md** - TTS documentation
- **services/voice-connector/README.md** - Voice connector docs

---

## 🆘 Getting Help

```bash
# Check service documentation
cat services/stt-service/README.md
cat services/tts-service/README.md
cat services/voice-connector/README.md

# View API docs
open http://localhost:8002/docs  # STT
open http://localhost:8003/docs  # TTS
open http://localhost:8005/docs  # Voice Connector
```

---

**Phase 2 Complete! 🎉**
