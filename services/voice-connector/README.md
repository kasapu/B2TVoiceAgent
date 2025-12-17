# Voice Connector Service

WebSocket-based voice connector for OCP Platform that orchestrates real-time voice conversations through STT, NLU, and TTS services.

## Features

- 🎙️ Real-time WebSocket voice connections
- 🔄 Complete voice pipeline: Audio -> STT -> Orchestrator -> TTS -> Audio
- 📊 Voice Activity Detection (VAD) for smart buffering
- ⚡ Concurrent call handling (100+ simultaneous calls)
- 🏥 Health monitoring and call tracking
- 🔌 Automatic reconnection handling
- 📈 Call metrics and statistics

## Architecture

```
Client (WebSocket)
    ↓ (Audio Chunks)
Voice Connector
    ↓
AudioBuffer (VAD + Buffering)
    ↓
STT Service (Speech-to-Text)
    ↓
Orchestrator (NLU + Dialog Management)
    ↓
TTS Service (Text-to-Speech)
    ↓
Voice Connector
    ↓ (Audio Response)
Client (WebSocket)
```

## Quick Start

### Local Development

```bash
# Install dependencies
pip install -r requirements.txt

# Run the service
uvicorn app.main:app --reload --port 8005
```

### Docker

```bash
# Build
docker build -t voice-connector .

# Run
docker run -p 8005:8005 \
  -e STT_SERVICE_URL=http://stt-service:8002 \
  -e TTS_SERVICE_URL=http://tts-service:8003 \
  -e ORCHESTRATOR_URL=http://orchestrator:8000 \
  voice-connector
```

## API Endpoints

### WebSocket: `/ws/voice`

Main WebSocket endpoint for voice calls.

**Connection:**
```javascript
const ws = new WebSocket('ws://localhost:8005/ws/voice');

ws.onopen = () => {
  console.log('Connected');
};

// Send audio chunks
ws.send(audioChunkBytes);

// Receive audio responses
ws.onmessage = (event) => {
  if (event.data instanceof Blob) {
    // Audio response
    playAudio(event.data);
  } else {
    // Control message
    const message = JSON.parse(event.data);
    console.log(message);
  }
};
```

**Message Types:**

1. **Outgoing (Client -> Server):**
   - Binary frames: Audio chunks (16-bit PCM, 16kHz)
   - `{"type": "ping"}`: Ping message
   - `{"type": "end_call"}`: End the call

2. **Incoming (Server -> Client):**
   - Binary frames: TTS audio responses
   - `{"type": "status", "call_id": "...", "state": "..."}`: Status updates
   - `{"type": "heartbeat"}`: Keep-alive heartbeat
   - `{"type": "pong"}`: Ping response

### GET `/health`

Health check endpoint.

**Response:**
```json
{
  "status": "healthy",
  "service": "OCP Voice Connector",
  "version": "1.0.0",
  "active_calls": 5,
  "uptime_seconds": 3600,
  "stt_service": "http://stt-service:8002",
  "tts_service": "http://tts-service:8003",
  "orchestrator_service": "http://orchestrator:8000"
}
```

### GET `/calls`

Get active calls information.

**Response:**
```json
{
  "active_calls": 5,
  "max_calls": 100,
  "calls": [
    {
      "call_id": "abc123",
      "session_id": "sess456",
      "state": "listening",
      "turns_count": 3
    }
  ]
}
```

## Configuration

Environment variables (`.env` file):

```bash
# Service
HOST=0.0.0.0
PORT=8005
LOG_LEVEL=INFO

# Service URLs
STT_SERVICE_URL=http://stt-service:8002
TTS_SERVICE_URL=http://tts-service:8003
ORCHESTRATOR_URL=http://orchestrator:8000

# WebSocket
WS_HEARTBEAT_INTERVAL=30
WS_TIMEOUT=300
MAX_CONNECTIONS=1000

# Audio
SAMPLE_RATE=16000
CHUNK_SIZE=4096
AUDIO_FORMAT=wav

# Buffer (VAD)
BUFFER_DURATION_MS=1000
MIN_AUDIO_LENGTH_MS=500
SILENCE_THRESHOLD=0.01
SILENCE_DURATION_MS=500

# Performance
MAX_CONCURRENT_CALLS=100
AUDIO_TIMEOUT_SECONDS=10
```

## Voice Activity Detection (VAD)

The AudioBuffer uses RMS-based VAD to detect speech and silence:

- **Speech Detection**: Buffers audio chunks while speech is detected
- **Silence Detection**: Triggers transcription after 500ms of silence
- **Buffer Limit**: Maximum 1000ms of audio before forced flush
- **Threshold**: RMS < 0.01 considered silence

## Call Flow

1. **Connection**: Client connects via WebSocket
2. **Welcome**: Server sends welcome message (TTS)
3. **Listening**: Server buffers incoming audio chunks
4. **VAD Trigger**: Silence detected after speech
5. **Transcription**: Audio sent to STT service
6. **Processing**: Text sent to Orchestrator for NLU
7. **Synthesis**: Response converted to speech via TTS
8. **Response**: Audio sent back to client
9. **Repeat**: Steps 3-8 for each conversation turn

## Performance

- **Latency**: ~1-2s end-to-end (STT + NLU + TTS)
- **Concurrent Calls**: 100+ simultaneous calls
- **Throughput**: Limited by STT/TTS service capacity
- **Memory**: ~50MB per active call

## Client Example (JavaScript)

```javascript
class VoiceClient {
  constructor(url) {
    this.ws = new WebSocket(url);
    this.setupHandlers();
  }

  setupHandlers() {
    this.ws.onopen = () => {
      console.log('Connected to voice service');
      this.startRecording();
    };

    this.ws.onmessage = (event) => {
      if (event.data instanceof Blob) {
        this.playAudio(event.data);
      } else {
        const msg = JSON.parse(event.data);
        console.log('Status:', msg);
      }
    };

    this.ws.onerror = (error) => {
      console.error('WebSocket error:', error);
    };

    this.ws.onclose = () => {
      console.log('Disconnected');
    };
  }

  startRecording() {
    navigator.mediaDevices.getUserMedia({ audio: true })
      .then(stream => {
        const mediaRecorder = new MediaRecorder(stream);

        mediaRecorder.ondataavailable = (event) => {
          if (event.data.size > 0) {
            this.ws.send(event.data);
          }
        };

        mediaRecorder.start(100); // 100ms chunks
      });
  }

  playAudio(audioBlob) {
    const audio = new Audio(URL.createObjectURL(audioBlob));
    audio.play();
  }

  endCall() {
    this.ws.send(JSON.stringify({ type: 'end_call' }));
    this.ws.close();
  }
}

// Usage
const client = new VoiceClient('ws://localhost:8005/ws/voice');
```

## Testing

```bash
# Run tests
pytest tests/ -v

# Test WebSocket connection
python tests/test_websocket.py
```

## Troubleshooting

### WebSocket Connection Fails

```bash
# Check service is running
curl http://localhost:8005/health

# Check logs
docker logs voice-connector
```

### No Audio Response

- Verify STT service is running and accessible
- Verify TTS service is running and accessible
- Check audio format (16-bit PCM, 16kHz, mono)
- Review logs for transcription/synthesis errors

### High Latency

- Check STT/TTS service performance
- Reduce buffer duration
- Use faster TTS/STT models
- Enable GPU acceleration on services

## Integration

The Voice Connector integrates with:

- **STT Service**: Transcribes audio to text
- **TTS Service**: Synthesizes text to speech
- **Orchestrator**: Handles NLU and dialog management
- **MinIO**: Stores temporary audio files (via TTS)

## License

Part of the OCP Platform project.
