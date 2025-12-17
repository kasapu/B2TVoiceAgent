# STT Service (Speech-to-Text)

OpenAI Whisper-based speech-to-text transcription service with automatic GPU detection.

## Features

- 🎤 Accurate speech transcription using OpenAI Whisper
- 🚀 Automatic GPU/CPU detection and optimization
- 📁 Multiple audio format support (WAV, MP3, M4A, FLAC, OGG, WEBM)
- ⚡ Fast inference with faster-whisper
- 🔄 Automatic audio format conversion via FFmpeg
- 📊 Detailed transcription metadata (segments, timestamps, duration)
- 🏥 Health check endpoints
- 🐳 Docker support (CPU and GPU variants)

## Quick Start

### Local Development

```bash
# Install system dependencies
sudo apt-get install ffmpeg

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install Python dependencies
pip install -r requirements.txt

# Run the service
uvicorn app.main:app --reload --port 8002
```

### Docker (CPU)

```bash
# Build
docker build -t stt-service .

# Run
docker run -p 8002:8002 \
  -v $(pwd)/ml-models/stt:/models/stt \
  stt-service
```

### Docker (GPU)

```bash
# Build GPU version
docker build -f Dockerfile.gpu -t stt-service:gpu .

# Run with GPU
docker run --gpus all -p 8002:8002 \
  -v $(pwd)/ml-models/stt:/models/stt \
  stt-service:gpu
```

## API Endpoints

### POST /transcribe

Transcribe an audio file to text.

**Request:**
```bash
curl -X POST "http://localhost:8002/transcribe" \
  -F "file=@audio.wav" \
  -F "language=en" \
  -F "task=transcribe"
```

**Response:**
```json
{
  "text": "Hello, how are you doing today?",
  "language": "en",
  "duration": 2.5,
  "segments": [
    {
      "id": 0,
      "start": 0.0,
      "end": 2.5,
      "text": "Hello, how are you doing today?"
    }
  ],
  "processing_time_ms": 850
}
```

### GET /health

Health check endpoint.

**Response:**
```json
{
  "status": "healthy",
  "service": "OCP STT Service",
  "version": "1.0.0",
  "model": "base",
  "device": "cuda",
  "device_info": {
    "device": "cuda",
    "device_name": "NVIDIA GeForce RTX 3090",
    "device_count": 1,
    "memory_total_gb": 24.0,
    "cuda_version": "12.1",
    "compute_type": "float16"
  }
}
```

## Configuration

Environment variables (`.env` file):

```bash
# Model Configuration
WHISPER_MODEL=base  # tiny, base, small, medium, large
DEVICE=auto  # auto, cpu, cuda
COMPUTE_TYPE=auto  # auto, int8, float16, float32

# Server
HOST=0.0.0.0
PORT=8002
LOG_LEVEL=INFO

# Audio Processing
SAMPLE_RATE=16000
MAX_FILE_SIZE_MB=25

# Transcription
BEAM_SIZE=5
VAD_FILTER=true
VAD_THRESHOLD=0.5

# Paths
MODEL_DIR=/models/stt
TEMP_DIR=/tmp/stt-uploads
```

## Model Sizes

| Model  | Parameters | Size  | Speed (GPU) | Accuracy |
|--------|-----------|-------|-------------|----------|
| tiny   | 39M       | 75MB  | ~1s         | 75%      |
| base   | 74M       | 145MB | ~2s         | 80%      |
| small  | 244M      | 466MB | ~5s         | 85%      |
| medium | 769M      | 1.5GB | ~10s        | 90%      |
| large  | 1550M     | 2.9GB | ~20s        | 95%      |

*Benchmark: 30-second audio on RTX 3090*

## Supported Languages

99 languages including:
- English (en)
- Spanish (es)
- French (fr)
- German (de)
- Chinese (zh)
- Japanese (ja)
- And many more...

Auto-detection is supported by omitting the `language` parameter.

## Performance Tips

1. **Use GPU**: 10-50x faster than CPU
2. **Choose appropriate model**: Start with `base` for good balance
3. **Enable VAD filter**: Improves accuracy by filtering silence
4. **Batch processing**: Process multiple files in parallel

## Troubleshooting

### GPU Not Detected

```bash
# Check CUDA availability
python -c "import torch; print(torch.cuda.is_available())"

# Install NVIDIA Docker support
sudo apt-get install nvidia-docker2
sudo systemctl restart docker
```

### FFmpeg Not Found

```bash
# Ubuntu/Debian
sudo apt-get install ffmpeg

# MacOS
brew install ffmpeg
```

### Model Download Issues

Models are automatically downloaded on first use. If download fails:

```bash
# Manually download models
mkdir -p /models/stt
wget https://huggingface.co/guillaumekln/faster-whisper-base -P /models/stt
```

## Testing

```bash
# Run tests
pytest tests/ -v

# Test transcription
curl -X POST "http://localhost:8002/transcribe" \
  -F "file=@tests/fixtures/test_audio.wav"
```

## License

Part of the OCP Platform project.
