# Conversational AI & Customer Experience Platform

A cloud-native, microservices-based platform for building intelligent voice and chat assistants, inspired by the Omilia Cloud Platform (OCP).

## Overview

This platform enables you to build production-grade conversational AI applications with:

- **Multi-channel support**: Voice (SIP/VoIP), Chat (WebSocket), REST APIs
- **Advanced NLU**: Intent recognition, entity extraction, context management
- **Flexible dialogue flows**: Visual flow designer for non-technical users
- **Real-time analytics**: Call containment, accuracy metrics, satisfaction scores
- **Scalable architecture**: Kubernetes-ready microservices

## Architecture

See [ARCHITECTURE.md](./ARCHITECTURE.md) for comprehensive technical documentation covering:

- Recommended tech stack (100% open source)
- Database schemas
- API specifications
- 5-phase development roadmap (MVP to production)

## Quick Start

### Prerequisites

- Docker 24+ and Docker Compose
- Python 3.11+
- Node.js 20+
- PostgreSQL 15+
- Redis 7+

### Phase 1: Text-Based Bot (MVP)

```bash
# Clone and setup
git clone <your-repo-url>
cd OCPplatform

# Start infrastructure services
docker-compose up -d postgres redis

# Run database migrations
cd services/orchestrator
python -m alembic upgrade head

# Start orchestrator service
uvicorn main:app --reload --port 8000

# In another terminal, start the chat UI
cd ../../frontend
npm install
npm start
```

Visit http://localhost:3000 to interact with the chatbot.

## Project Structure

```
OCPplatform/
├── services/
│   ├── orchestrator/          # Core dialogue management
│   ├── nlu-service/           # Natural language understanding
│   ├── stt-service/           # Speech-to-text (Whisper)
│   ├── tts-service/           # Text-to-speech (Coqui TTS)
│   ├── voice-connector/       # SIP/FreeSWITCH integration
│   ├── chat-connector/        # WebSocket chat server
│   └── integration-service/   # External API middleware
├── frontend/
│   ├── admin-ui/              # Flow designer & dashboards
│   └── chat-widget/           # Embeddable chat component
├── infrastructure/
│   ├── docker/                # Dockerfiles for each service
│   ├── kubernetes/            # Helm charts & K8s manifests
│   └── terraform/             # Infrastructure as Code
├── ml-models/
│   ├── nlu/                   # Intent & entity models
│   ├── stt/                   # Whisper fine-tuned models
│   └── tts/                   # Custom voice models
├── scripts/
│   ├── setup/                 # Initial setup scripts
│   ├── data/                  # Data migration & seeding
│   └── deploy/                # Deployment automation
├── docs/
│   ├── api/                   # API documentation
│   ├── guides/                # User & developer guides
│   └── runbooks/              # Operational procedures
├── tests/
│   ├── unit/
│   ├── integration/
│   └── load/                  # SIPp & Locust tests
├── docker-compose.yml         # Development environment
├── ARCHITECTURE.md            # Technical architecture
└── README.md                  # This file
```

## Development Roadmap

| Phase | Timeline | Status | Description |
|-------|----------|--------|-------------|
| **Phase 1** | Weeks 1-4 | 🚧 In Progress | Text-based chatbot with basic NLU |
| **Phase 2** | Weeks 5-10 | 📋 Planned | Advanced NLU + visual flow designer |
| **Phase 3** | Weeks 11-16 | 📋 Planned | Voice integration (SIP, STT, TTS) |
| **Phase 4** | Weeks 17-22 | 📋 Planned | Analytics, BI dashboards, retraining |
| **Phase 5** | Weeks 23-30 | 📋 Planned | Production hardening, K8s, monitoring |

See [ARCHITECTURE.md - Phase 4](./ARCHITECTURE.md#phase-4-development-roadmap) for detailed milestones.

## Key Features

### Current (Phase 1)

- ✅ Text-based chat interface
- ✅ Basic intent classification (5-10 intents)
- ✅ Session state management (Redis)
- ✅ PostgreSQL conversation logging
- ✅ Simple dialogue flow engine

### Coming Soon (Phase 2-3)

- 🚧 Visual flow designer (React Flow)
- 🚧 Advanced NLU with transformers (RoBERTa)
- 🚧 Entity extraction
- 🚧 External API integration
- 🚧 Voice calls via SIP
- 🚧 Real-time speech-to-text
- 🚧 Neural text-to-speech

### Future (Phase 4-5)

- 📋 Real-time analytics dashboards
- 📋 Automated model retraining
- 📋 A/B testing framework
- 📋 Kubernetes deployment
- 📋 Distributed tracing
- 📋 Load testing suite

## Tech Stack

### Backend
- **Languages**: Python 3.11, Node.js 20
- **Frameworks**: FastAPI, Express
- **Databases**: PostgreSQL 15, Redis 7, ClickHouse
- **Message Queue**: Apache Kafka
- **Workflow**: Temporal.io

### AI/ML
- **NLU**: Rasa, HuggingFace Transformers (RoBERTa, DistilBERT)
- **STT**: Whisper (faster-whisper)
- **TTS**: Coqui TTS (VITS models)
- **Training**: PyTorch, spaCy 3.6

### Frontend
- **Framework**: React 18 + TypeScript
- **UI Library**: Material-UI
- **State**: Redux Toolkit
- **Flow Designer**: React Flow

### Infrastructure
- **Containers**: Docker, Kubernetes
- **Monitoring**: Prometheus, Grafana, Jaeger
- **CI/CD**: GitHub Actions, ArgoCD
- **Secrets**: HashiCorp Vault

### Voice/Telephony
- **SIP**: Kamailio (load balancer), FreeSWITCH (media server)
- **Alternative**: Asterisk 20

## API Documentation

Once the orchestrator service is running, visit:

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

Example request:

```bash
# Start a conversation
curl -X POST http://localhost:8000/v1/conversations/start \
  -H "Content-Type: application/json" \
  -d '{"channel_type": "chat"}'

# Process user input
curl -X POST http://localhost:8000/v1/conversations/{session_id}/process \
  -H "Content-Type: application/json" \
  -d '{
    "input_type": "text",
    "text": "I want to check my balance"
  }'
```

## Configuration

### Environment Variables

Create a `.env` file in the project root:

```bash
# Database
DATABASE_URL=postgresql://user:password@localhost:5432/ocplatform
REDIS_URL=redis://localhost:6379/0

# Services
NLU_SERVICE_URL=http://localhost:8001
STT_SERVICE_URL=http://localhost:8002
TTS_SERVICE_URL=http://localhost:8003

# Security
JWT_SECRET=your-secret-key-change-in-production
API_KEY=your-api-key

# ML Models
NLU_MODEL_PATH=/models/nlu/intent-classifier
STT_MODEL_PATH=/models/whisper/base
TTS_MODEL_PATH=/models/tts/vits

# Kafka
KAFKA_BOOTSTRAP_SERVERS=localhost:9092

# Observability
JAEGER_ENDPOINT=http://localhost:14268/api/traces
PROMETHEUS_PORT=9090
```

## Contributing

We welcome contributions! Please see [CONTRIBUTING.md](./CONTRIBUTING.md) for guidelines.

## Testing

```bash
# Run unit tests
pytest tests/unit -v

# Run integration tests
pytest tests/integration -v

# Run load tests
cd tests/load
./run_load_test.sh --concurrent-calls 100 --duration 300
```

## Monitoring

### Metrics

- **Prometheus**: http://localhost:9090
- **Grafana**: http://localhost:3001 (admin/admin)

### Logs

- **Kibana**: http://localhost:5601

### Tracing

- **Jaeger UI**: http://localhost:16686

## License

MIT License - see [LICENSE](./LICENSE) for details.

## Support

- **Documentation**: [docs/](./docs/)
- **Issues**: GitHub Issues
- **Discussions**: GitHub Discussions

## Acknowledgments

Inspired by the Omilia Cloud Platform architecture. Built with modern open-source tools for conversational AI.

---

**Status**: 🚧 Under Active Development (Phase 1)
**Version**: 0.1.0
**Last Updated**: 2025-01-20
