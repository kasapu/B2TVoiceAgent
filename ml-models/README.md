# ML Models Directory

This directory contains the AI/ML models used by B2TVoiceAgent services.

## Why are models not in Git?

The model files are large (100MB+) and exceed GitHub's file size limits. They are automatically downloaded when the Docker containers start for the first time.

## Directory Structure

```
ml-models/
├── nlu/                    # Natural Language Understanding models
│   └── intent_classifier/  # Downloaded on first run
├── stt/                    # Speech-to-Text models (Whisper)
│   └── models--Systran--faster-whisper-base/  # Downloaded on first run
└── tts/                    # Text-to-Speech models (Coqui TTS)
    └── (downloaded on first run)
```

## Manual Download (Optional)

If you want to pre-download the models before starting Docker:

### STT Model (Whisper Base)
The STT service automatically downloads the Whisper base model from HuggingFace on first run.

**Model:** Systran/faster-whisper-base
**Size:** ~140 MB
**Location:** `ml-models/stt/`

### TTS Model (Coqui TTS)
The TTS service automatically downloads the Tacotron2-DDC model on first run.

**Model:** tts_models/en/ljspeech/tacotron2-DDC
**Size:** ~100 MB
**Location:** `ml-models/tts/`

### NLU Model (Intent Classifier)
The NLU model is trained during initial setup or can be loaded from a pre-trained model.

**Location:** `ml-models/nlu/intent_classifier/`

## First Run

When you start the services with `docker compose up -d`, the models will be automatically downloaded. This may take 5-10 minutes on first run.

### Monitor Download Progress

```bash
# Watch STT service logs
docker logs -f ocp-stt

# Watch TTS service logs
docker logs -f ocp-tts

# Watch NLU service logs
docker logs -f ocp-nlu
```

## Storage Requirements

- **STT Models:** ~150 MB
- **TTS Models:** ~100 MB
- **NLU Models:** ~50 MB
- **Total:** ~300 MB

Ensure you have sufficient disk space before starting the services.

## Troubleshooting

### Models not downloading?

1. **Check internet connection**
2. **Check Docker volume permissions:**
   ```bash
   docker compose down
   docker volume ls
   docker volume rm <volume-name> # If needed
   docker compose up -d
   ```

3. **Manually download (advanced):**
   ```bash
   # Example for STT model
   docker exec -it ocp-stt python -c "from faster_whisper import WhisperModel; WhisperModel('base')"
   ```

### Low disk space?

Use smaller models:
- STT: Change `WHISPER_MODEL=tiny` in `.env`
- TTS: Use a smaller voice model in TTS service configuration

## Production Notes

For production deployments:
- Pre-download models to speed up container startup
- Use Docker volumes to persist models across container restarts
- Consider using a model registry or CDN for faster downloads
