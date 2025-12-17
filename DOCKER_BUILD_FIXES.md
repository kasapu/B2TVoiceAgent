# Docker Build Fixes Applied

**Date:** December 13, 2025
**Issue:** STT Service build failing with pip install error

---

## ✅ Fixes Applied

### 1. STT Service (Port 8002)
**Files Updated:**
- `services/stt-service/Dockerfile`
- `services/stt-service/requirements.txt`

**Changes:**
- Added `build-essential` and `curl` to system dependencies
- Updated `faster-whisper` to version 1.0.0 (more stable)
- Added `openai-whisper==20231117` for compatibility
- Added `numpy==1.24.3` and `numba==0.58.1` dependencies
- Added `requests==2.31.0` for health checks

### 2. TTS Service (Port 8003)
**Files Updated:**
- `services/tts-service/Dockerfile`
- `services/tts-service/requirements.txt`

**Changes:**
- Added `libsndfile1-dev`, `curl`, and `git` to system dependencies
- Updated `TTS` to version 0.22.0 (more stable)
- Added `soundfile==0.12.1` for audio processing
- Added `requests==2.31.0` for health checks
- Reordered dependencies (numpy first)

### 3. Voice Connector (Port 8005)
**Files Updated:**
- `services/voice-connector/Dockerfile`
- `services/voice-connector/requirements.txt`

**Changes:**
- Added `curl` to system dependencies
- Added `requests==2.31.0` for health checks

---

## 🚀 How to Rebuild and Start

### Step 1: Clean Up Old Containers (if any)
```bash
cd /home/kranti/OCPplatform

# Stop and remove all containers
docker compose down

# Remove old images (optional, but recommended)
docker compose down --rmi all

# Clean build cache (optional, for complete fresh build)
docker builder prune -af
```

### Step 2: Build and Start All Services
```bash
# Build all services (this will take 5-10 minutes)
docker compose build

# Start all services
docker compose up -d

# Watch the logs during startup
docker compose logs -f
```

### Step 3: Verify Services Are Running
```bash
# Check container status
docker compose ps

# Should show all 11 containers running:
# - ocp-postgres
# - ocp-redis
# - ocp-orchestrator
# - ocp-nlu
# - ocp-chat-connector
# - ocp-chat-widget
# - ocp-adminer
# - ocp-minio
# - ocp-stt
# - ocp-tts
# - ocp-voice-connector
```

### Step 4: Health Checks
```bash
# Wait 30-60 seconds for services to fully start, then test:

# Test orchestrator
curl http://localhost:8000/health

# Test NLU
curl http://localhost:8001/health

# Test STT
curl http://localhost:8002/health

# Test TTS
curl http://localhost:8003/health

# Test Voice Connector
curl http://localhost:8005/health

# Test MinIO
curl http://localhost:9000/minio/health/live
```

---

## 📊 Expected Build Time

| Service | Build Time | Notes |
|---------|------------|-------|
| postgres | 10s | Pre-built image |
| redis | 5s | Pre-built image |
| minio | 5s | Pre-built image |
| adminer | 5s | Pre-built image |
| orchestrator | 30s | Light dependencies |
| nlu-service | 60s | spaCy models |
| chat-connector | 20s | Light dependencies |
| chat-widget | 90s | npm install |
| **stt-service** | **180-300s** | Whisper + PyTorch (large) |
| **tts-service** | **180-300s** | Coqui TTS + PyTorch (large) |
| voice-connector | 30s | Light dependencies |

**Total First Build:** 10-15 minutes
**Subsequent Builds:** 2-3 minutes (with cache)

---

## 🔍 Troubleshooting

### If Build Still Fails

**Check Docker Resources:**
```bash
# Docker needs at least:
# - 4 GB RAM
# - 20 GB disk space
# - Good internet connection (downloading ~2 GB packages)

docker system df  # Check disk usage
```

**Build Services One by One:**
```bash
# Build only STT first
docker compose build stt-service

# Build only TTS
docker compose build tts-service

# Build everything else
docker compose build
```

**View Detailed Build Logs:**
```bash
# See exactly where it fails
docker compose build stt-service --progress=plain --no-cache
```

### If Container Exits Immediately

**Check Logs:**
```bash
docker compose logs stt-service
docker compose logs tts-service
docker compose logs voice-connector
```

**Common Issues:**
1. **Port already in use:** Stop any services using ports 8002, 8003, 8005, 9000
2. **Model download timeout:** Services download models on first run (be patient)
3. **Permission issues:** Make sure you have write access to `ml-models/` and `tmp/` directories

```bash
# Fix permissions
sudo chown -R $USER:$USER /home/kranti/OCPplatform/ml-models
sudo chown -R $USER:$USER /home/kranti/OCPplatform/tmp
sudo chown -R $USER:$USER /home/kranti/OCPplatform/audio-storage
```

### If Health Check Fails

**Wait Longer:**
STT and TTS services take 60-120 seconds to download and load models on first start.

```bash
# Watch logs in real-time
docker compose logs -f stt-service tts-service

# Look for:
# "Model loaded successfully"
# "Application startup complete"
```

---

## 📝 What Changed

### Dependencies Fixed

**STT Service:**
- `faster-whisper` 0.10.0 → 1.0.0 (more stable)
- Added explicit `openai-whisper` dependency
- Added missing NumPy and Numba versions

**TTS Service:**
- `TTS` 0.21.0 → 0.22.0 (more stable)
- Added soundfile library
- Better dependency ordering

**All Services:**
- Added `requests` library for health checks
- Added system build tools
- Improved Dockerfile layer caching

---

## ✅ Verification Checklist

After rebuilding, verify:

- [ ] All 11 containers show "Up" status in `docker compose ps`
- [ ] Health endpoints return `{"status":"healthy"}` for all services
- [ ] No error messages in `docker compose logs`
- [ ] MinIO console accessible at http://localhost:9001
- [ ] Chat widget accessible at http://localhost:3000
- [ ] Can transcribe test audio via STT service
- [ ] Can synthesize test speech via TTS service

---

## 🎯 Quick Test After Build

```bash
# 1. All services running
docker compose ps | grep Up

# 2. Test STT (requires test audio file)
echo "Testing STT..." > /tmp/test.txt

# 3. Test TTS
curl -X POST "http://localhost:8003/synthesize" \
  -H "Content-Type: application/json" \
  -d '{"text":"Hello, the build was successful!"}' | jq .

# 4. Test Voice Connector
curl http://localhost:8005/calls | jq .
```

---

## 💡 Tips

1. **First build takes time** - STT and TTS download large ML models
2. **Use build cache** - Don't use `--no-cache` unless necessary
3. **Monitor resources** - Watch Docker Desktop or `docker stats`
4. **Be patient** - Model downloads can take 2-5 minutes each
5. **Check logs** - Use `docker compose logs -f` to see real-time progress

---

**All fixes applied! Ready to rebuild.** 🎉
