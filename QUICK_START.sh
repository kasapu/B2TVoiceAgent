#!/bin/bash
# Quick Start Script for OCPplatform
# Run this after all fixes have been applied

echo "============================================"
echo "OCP Platform - Quick Start"
echo "============================================"
echo ""

# Navigate to project directory
cd /home/kranti/OCPplatform

echo "Step 1: Cleaning up old containers..."
docker compose down
echo "✅ Cleanup complete"
echo ""

echo "Step 2: Building all services (this takes 8-12 minutes)..."
echo "Building: orchestrator, nlu, stt, tts, voice-connector, chat-connector, chat-widget"
docker compose build
if [ $? -ne 0 ]; then
    echo "❌ Build failed! Check error messages above."
    exit 1
fi
echo "✅ Build complete"
echo ""

echo "Step 3: Starting all services..."
docker compose up -d
if [ $? -ne 0 ]; then
    echo "❌ Failed to start services! Check error messages above."
    exit 1
fi
echo "✅ Services started"
echo ""

echo "Step 4: Waiting for services to initialize (60 seconds)..."
for i in {60..1}; do
    echo -ne "Waiting: $i seconds remaining...\r"
    sleep 1
done
echo ""
echo ""

echo "Step 5: Checking service health..."
echo ""

# Function to check health
check_health() {
    local service=$1
    local url=$2
    local response=$(curl -s -o /dev/null -w "%{http_code}" $url 2>/dev/null)

    if [ "$response" = "200" ]; then
        echo "✅ $service: healthy"
        return 0
    else
        echo "❌ $service: unhealthy (HTTP $response)"
        return 1
    fi
}

# Check all services
check_health "Orchestrator  " "http://localhost:8000/health"
check_health "NLU Service   " "http://localhost:8001/health"
check_health "STT Service   " "http://localhost:8002/health"
check_health "TTS Service   " "http://localhost:8003/health"
check_health "Chat Connector" "http://localhost:8004/health"
check_health "Voice Connector" "http://localhost:8005/health"
check_health "MinIO Storage " "http://localhost:9000/minio/health/live"

echo ""
echo "============================================"
echo "Container Status:"
echo "============================================"
docker compose ps
echo ""

echo "============================================"
echo "Access URLs:"
echo "============================================"
echo "Chat Widget:      http://localhost:3000"
echo "Orchestrator API: http://localhost:8000/docs"
echo "NLU API:          http://localhost:8001/docs"
echo "STT API:          http://localhost:8002/docs"
echo "TTS API:          http://localhost:8003/docs"
echo "Voice WebSocket:  ws://localhost:8005/ws/voice"
echo "MinIO Console:    http://localhost:9001 (admin/admin)"
echo "Database Admin:   http://localhost:8080 (postgres/ocpuser/ocppassword)"
echo ""

echo "============================================"
echo "Quick Test Commands:"
echo "============================================"
echo ""
echo "# Test STT (requires audio file):"
echo 'curl -X POST "http://localhost:8002/transcribe" -F "file=@test.wav" -F "language=en"'
echo ""
echo "# Test TTS:"
echo 'curl -X POST "http://localhost:8003/synthesize" -H "Content-Type: application/json" -d "{\"text\":\"Hello world\"}"'
echo ""
echo "# Test Voice Connector:"
echo 'curl http://localhost:8005/calls'
echo ""
echo "# View logs:"
echo 'docker compose logs -f'
echo ""

echo "============================================"
echo "✅ Quick Start Complete!"
echo "============================================"
echo ""
echo "Next steps:"
echo "1. Test the chat widget at http://localhost:3000"
echo "2. Follow PHASE2_VOICE_TESTING_GUIDE.md for detailed testing"
echo "3. Check logs with: docker compose logs -f"
echo ""
