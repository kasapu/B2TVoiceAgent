# B2T Voice Agent Platform

## Overview

This is a cloud-native Conversational AI platform for building intelligent voice and chat assistants. The platform provides multi-channel support (Voice/SIP, Chat/WebSocket, REST APIs), advanced NLU capabilities, flexible dialogue flows, and real-time analytics.

## B2T Portal (NEW)

The platform now features a world-class admin portal at `/` with:
- **Dashboard** - Hero section, stats, feature cards
- **miniApps** - Deploy NL applications in minutes
- **NLU** - Intent management and model training
- **Orchestrator** - Drag-and-drop flow builder
- **Voice Biometrics** - Voice authentication
- **Agent Assist** - AI-powered agent assistance
- **Integrations** - Connect external systems
- **Insights** - Analytics and metrics
- **Environments Manager** - Dev/Staging/Production
- **Access Management** - User roles and permissions
- **Testing Studio+** - Interactive conversation testing
- **Pathfinder** - Conversation path analysis
- **Support Center** - Documentation and help

### Portal Files
- `frontend/portal/index.html` - Main portal HTML
- `frontend/portal/styles.css` - Portal styling
- `frontend/portal/app.js` - Portal functionality

### Chat Widget
- Available at `/chat` route
- WebSocket-based real-time messaging
- Located in `frontend/chat-widget/`

## User Preferences

Preferred communication style: Simple, everyday language.

## System Architecture

### Core Services

1. **Orchestrator Service** (Port 8000) - Central coordination hub
   - FastAPI-based async Python service
   - Manages conversation sessions and dialogue flow execution
   - Integrates with NLU service for intent detection
   - Uses PostgreSQL for conversation logging, Redis for session state
   - Endpoints: `/v1/conversations/*`, `/v1/flows/*`, `/health`

2. **NLU Service** (Port 8001) - Natural Language Understanding
   - spaCy-based intent classification (lightweight alternative to Rasa)
   - Entity extraction for amounts, account types, etc.
   - Sentiment analysis
   - Trains from PostgreSQL training examples on startup
   - Endpoints: `/parse`, `/train`, `/intents`, `/health`

3. **STT Service** (Port 8002) - Speech-to-Text
   - OpenAI Whisper (faster-whisper) for transcription
   - Automatic GPU/CPU detection
   - Supports WAV, MP3, M4A, FLAC, OGG, WEBM
   - FFmpeg for audio conversion
   - Endpoints: `/transcribe`, `/health`

4. **TTS Service** (Port 8003) - Text-to-Speech
   - gTTS (Google Text-to-Speech) - lightweight cloud-based synthesis
   - MinIO S3-compatible storage for generated audio
   - Adjustable speech speed
   - Endpoints: `/synthesize`, `/health`

5. **Chat Connector** (Port 8004) - WebSocket chat gateway
   - Real-time bidirectional messaging
   - Connection management
   - Forwards messages to Orchestrator

6. **Voice Connector** (Port 8005) - Voice pipeline orchestrator
   - WebSocket-based voice connections
   - Coordinates Audio → STT → Orchestrator → TTS → Audio pipeline
   - Voice Activity Detection (VAD)
   - Handles 100+ concurrent calls

7. **SIP Gateway** (Port 8006) - Telephony bridge
   - FreeSWITCH integration for SIP/RTP handling
   - Bridges traditional phone calls to Voice Connector
   - Audio format conversion (G.711 μ-law ↔ PCM 16-bit)
   - Sample rate conversion (8kHz ↔ 16kHz)
   - Twilio SIP trunk support

### Frontend Applications

- **Chat Widget** (Port 3000) - React-based web chat interface
- **Admin Portal** - Management dashboard (static HTML/JS)

### Infrastructure Services

- **PostgreSQL** - Primary database for sessions, flows, intents, training data
- **Redis** - Session state caching with TTL
- **MinIO** - S3-compatible object storage for audio files
- **Adminer** (Port 8080) - Database administration UI

### Design Patterns

- **Microservices Architecture**: Each service is independently deployable
- **Async-first**: All Python services use FastAPI with async/await
- **Event-driven communication**: WebSockets for real-time updates
- **State Machine**: Dialogue flows executed as state machines
- **Singleton Pattern**: ML model managers ensure single model instance

### Database Schema

PostgreSQL with 11+ tables including:
- `sessions` - Conversation sessions
- `conversation_turns` - Individual messages
- `dialogue_flows` - Flow definitions (JSONB)
- `intents` - Intent definitions
- `training_examples` - NLU training data
- Uses JSONB columns for flexible schema elements

## External Dependencies

### Required Infrastructure
- **PostgreSQL 15+** - Primary database (asyncpg driver)
- **Redis 7+** - Session state management
- **MinIO** - Audio file storage (S3-compatible)

### Python Packages (Key Dependencies)
- FastAPI + Uvicorn - Web framework
- SQLAlchemy 2.0 (async) - Database ORM
- spaCy 3.7 - NLU/ML pipeline
- faster-whisper 1.0 - Speech-to-text
- gTTS - Text-to-speech
- websockets - Real-time communication
- httpx - Async HTTP client

### Optional Integrations
- **Twilio** - SIP trunk for mobile phone testing
- **FreeSWITCH** - SIP/RTP media handling (containerized)

### ML Models (Downloaded on first run)
- Whisper base model (~140MB) - STT
- spaCy en_core_web_sm - NLU
- Models stored in `/ml-models/` directory