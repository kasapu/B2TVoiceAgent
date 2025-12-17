# TTS Service (Text-to-Speech)

Coqui TTS-based text-to-speech synthesis service with automatic GPU detection and MinIO storage integration.

## Features

- 🗣️ Natural-sounding speech synthesis using Coqui TTS
- 🚀 Automatic GPU/CPU detection and optimization
- 📦 MinIO S3-compatible storage for generated audio
- ⚡ Fast inference with GPU acceleration
- 🎚️ Adjustable speech speed (0.5x - 2.0x)
- 🎭 Multi-voice support (model-dependent)
- 🔗 Presigned URLs with configurable expiry
- 🏥 Health check endpoints
- 🐳 Docker support (CPU and GPU variants)

## Quick Start

### Local Development

```bash
# Install system dependencies
sudo apt-get install ffmpeg libsndfile1

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install Python dependencies
pip install -r requirements.txt

# Start MinIO (required for audio storage)
docker run -d -p 9000:9000 -p 9001:9001 \
  -e "MINIO_ROOT_USER=minioadmin" \
  -e "MINIO_ROOT_PASSWORD=minioadmin" \
  minio/minio server /data --console-address ":9001"

# Run the service
uvicorn app.main:app --reload --port 8003
```

### Docker (CPU)

```bash
# Build
docker build -t tts-service .

# Run
docker run -p 8003:8003 \
  -v $(pwd)/ml-models/tts:/models/tts \
  -e MINIO_ENDPOINT=host.docker.internal:9000 \
  tts-service
```

### Docker (GPU)

```bash
# Build GPU version
docker build -f Dockerfile.gpu -t tts-service:gpu .

# Run with GPU
docker run --gpus all -p 8003:8003 \
  -v $(pwd)/ml-models/tts:/models/tts \
  -e MINIO_ENDPOINT=host.docker.internal:9000 \
  tts-service:gpu
```

## API Endpoints

### POST /synthesize

Synthesize speech from text.

**Request:**
```bash
curl -X POST "http://localhost:8003/synthesize" \
  -H "Content-Type: application/json" \
  -d '{
    "text": "Hello, how can I help you today?",
    "voice": "default",
    "speed": 1.0
  }'
```

**Response:**
```json
{
  "audio_url": "http://localhost:9000/tts-audio/tts/abc123.wav?token=...",
  "duration_ms": 2500,
  "processing_time_ms": 450,
  "text": "Hello, how can I help you today?",
  "voice": "default",
  "format": "wav",
  "sample_rate": 22050
}
```

### GET /health

Health check endpoint.

**Response:**
```json
{
  "status": "healthy",
  "service": "OCP TTS Service",
  "version": "1.0.0",
  "model": "tts_models/en/ljspeech/tacotron2-DDC",
  "device": "cuda",
  "device_info": {
    "device": "cuda",
    "device_name": "NVIDIA GeForce RTX 3090",
    "memory_total_gb": 24.0
  },
  "minio_connected": true,
  "available_voices": ["default"]
}
```

### GET /voices

List available voices.

**Response:**
```json
{
  "voices": ["default", "speaker_1", "speaker_2"],
  "count": 3,
  "multi_speaker": true
}
```

## Configuration

Environment variables (`.env` file):

```bash
# Model Configuration
TTS_MODEL=tts_models/en/ljspeech/tacotron2-DDC
DEVICE=auto  # auto, cpu, cuda

# Server
HOST=0.0.0.0
PORT=8003
LOG_LEVEL=INFO

# Audio
SAMPLE_RATE=22050
OUTPUT_FORMAT=wav

# Speech Parameters
DEFAULT_SPEED=1.0
MAX_TEXT_LENGTH=1000

# MinIO Storage
MINIO_ENDPOINT=localhost:9000
MINIO_ACCESS_KEY=minioadmin
MINIO_SECRET_KEY=minioadmin
MINIO_BUCKET=tts-audio
AUDIO_URL_EXPIRY_HOURS=24

# Paths
MODEL_DIR=/models/tts
TEMP_DIR=/tmp/tts-output
```

## Available TTS Models

Popular Coqui TTS models:

| Model | Language | Quality | Speed | Multi-Speaker |
|-------|----------|---------|-------|---------------|
| tts_models/en/ljspeech/tacotron2-DDC | English | High | Fast | No |
| tts_models/en/ljspeech/vits | English | Very High | Medium | No |
| tts_models/en/vctk/vits | English | High | Medium | Yes (109 speakers) |
| tts_models/multilingual/multi-dataset/your_tts | Multi | High | Medium | Yes |

Full list: https://github.com/coqui-ai/TTS

## Speech Speed Examples

- **0.5x**: Very slow (instructional, accessibility)
- **0.75x**: Slow (clear pronunciation)
- **1.0x**: Normal speed (default)
- **1.25x**: Slightly fast
- **1.5x**: Fast (quick reading)
- **2.0x**: Very fast (maximum)

## MinIO Storage

Generated audio files are automatically uploaded to MinIO with:
- Presigned URLs (24-hour expiry by default)
- S3-compatible storage
- Automatic bucket creation
- Object naming: `tts/{uuid}.wav`

## Performance Tips

1. **Use GPU**: 5-20x faster than CPU
2. **Choose appropriate model**: VITS models = higher quality, Tacotron2 = faster
3. **Enable speed adjustment carefully**: Values > 1.5x may reduce quality
4. **Batch requests**: Process multiple texts in parallel

## Troubleshooting

### GPU Not Detected

```bash
# Check CUDA availability
python -c "import torch; print(torch.cuda.is_available())"

# Install NVIDIA Docker support
sudo apt-get install nvidia-docker2
sudo systemctl restart docker
```

### MinIO Connection Error

```bash
# Check MinIO is running
curl http://localhost:9000/minio/health/live

# Start MinIO
docker run -d -p 9000:9000 -p 9001:9001 \
  -e "MINIO_ROOT_USER=minioadmin" \
  -e "MINIO_ROOT_PASSWORD=minioadmin" \
  minio/minio server /data --console-address ":9001"
```

### Model Download Issues

Models are automatically downloaded on first use. If download fails:

```bash
# Set download directory
export TTS_HOME=/models/tts

# Manually download (example)
tts --model_name tts_models/en/ljspeech/tacotron2-DDC --text "test"
```

### Audio Quality Issues

- Use higher quality models (VITS over Tacotron2)
- Keep speed between 0.75x - 1.5x
- Ensure sample rate is 22050Hz
- Check MinIO upload integrity

## Testing

```bash
# Run tests
pytest tests/ -v

# Test synthesis
curl -X POST "http://localhost:8003/synthesize" \
  -H "Content-Type: application/json" \
  -d '{"text":"Hello world"}'

# Download and play audio
wget -O test.wav "http://localhost:9000/tts-audio/..."
ffplay test.wav
```

## Integration with OCP Platform

The TTS service integrates with:
- **Orchestrator**: Generates speech responses for voice conversations
- **Voice Connector**: Streams audio to callers via WebSocket
- **MinIO**: Centralized audio file storage

## License

Part of the OCP Platform project.
