# OCP Platform - Project Summary

## What You Received

This repository contains a **complete blueprint and implementation plan** for building a cloud-native, microservices-based Conversational AI & Customer Experience Platform, inspired by the Omilia Cloud Platform (OCP).

## 📋 Deliverables Overview

### 1. Comprehensive Architecture Documentation

**File:** [ARCHITECTURE.md](./ARCHITECTURE.md) (42KB, 1,200+ lines)

Covers all four requested phases:

#### Phase 1: Recommended Tech Stack
- **Backend**: FastAPI (Python), PostgreSQL, Redis
- **Frontend**: React + TypeScript, Material-UI
- **AI/ML**: Whisper (STT), Coqui TTS (TTS), Rasa/HuggingFace (NLU)
- **Voice**: FreeSWITCH/Kamailio for SIP
- **Infrastructure**: Docker, Kubernetes, Kafka, Prometheus/Grafana

**Key Decision**: 100% open-source stack, optimized for solo developer initially scalable to production.

#### Phase 2: Database Schema Design
Complete PostgreSQL schemas with:
- **11 tables**: Sessions, conversation turns, dialogue flows, intents, training examples, integrations, users, agents, audit logs
- **Indexes**: Optimized for query performance
- **Triggers**: Auto-update timestamps, session duration calculation
- **Views**: Pre-built analytics views
- **Seed Data**: 7 sample intents with training examples
- **Redis schemas**: Session state management
- **MongoDB schemas**: Optional unstructured logs

#### Phase 3: API Interface Design
Full OpenAPI 3.0 specification with:
- **Core endpoint**: `/conversations/{session_id}/process` - main orchestration logic
- **Complete request/response schemas**
- **Authentication**: JWT-based security
- **Python implementation example** with detailed logic flow

Sample endpoints:
- `POST /conversations/start` - Initialize session
- `POST /conversations/{id}/process` - Process user input
- `POST /conversations/{id}/end` - End session
- `POST /nlu/parse` - Standalone NLU parsing
- `GET/POST /flows` - Manage dialogue flows

#### Phase 4: Development Roadmap
5 detailed phases from MVP to production:

| Phase | Duration | Focus | Key Deliverables |
|-------|----------|-------|------------------|
| **Phase 1** | 4 weeks | Text chatbot | Basic NLU, hardcoded flows, web UI |
| **Phase 2** | 6 weeks | Advanced NLU | Visual flow designer, transformers, entity extraction |
| **Phase 3** | 6 weeks | Voice integration | SIP stack, streaming STT/TTS |
| **Phase 4** | 6 weeks | Analytics | Kafka, ClickHouse, dashboards, retraining |
| **Phase 5** | 8 weeks | Production | Kubernetes, monitoring, security, scale testing |

**Total Timeline**: ~30 weeks (7-8 months) for full production system

---

### 2. Project Infrastructure

#### Complete Directory Structure
```
OCPplatform/
├── services/           # 7 microservices (orchestrator, nlu, stt, tts, etc.)
├── frontend/           # 2 apps (admin UI, chat widget)
├── infrastructure/     # Docker, K8s, Terraform configs
├── ml-models/         # STT, TTS, NLU models
├── scripts/           # Setup, deployment scripts
├── docs/              # API docs, guides, runbooks
└── tests/             # Unit, integration, load tests
```

#### Docker Compose Configuration
**File:** [docker-compose.yml](./docker-compose.yml)

Phase 1 services:
- PostgreSQL 15 (with initialization SQL)
- Redis 7 (with caching config)
- Adminer (database UI)
- Orchestrator (FastAPI)
- NLU Service
- Chat Connector
- Chat Widget (React)

Commented-out services for later phases:
- Kafka + Zookeeper (Phase 4)
- Prometheus + Grafana (Phase 5)

#### Database Initialization
**File:** [scripts/sql/init.sql](./scripts/sql/init.sql) (320 lines)

Includes:
- All 11 table definitions
- Foreign key constraints
- Indexes for performance
- Triggers for automation
- Seed data: 7 intents, 20+ training examples, 1 sample dialogue flow
- Default admin user (username: admin, password: admin123)
- Analytics views

#### Quick Start Script
**File:** [scripts/setup/quickstart.sh](./scripts/setup/quickstart.sh)

Automated setup that:
1. Checks prerequisites (Docker, Docker Compose)
2. Creates `.env` with generated secrets
3. Starts PostgreSQL and Redis
4. Waits for services to be ready
5. Verifies database initialization
6. Displays access information

Usage:
```bash
./scripts/setup/quickstart.sh
```

---

### 3. Documentation

#### Main README
**File:** [README.md](./README.md)

Includes:
- Project overview
- Architecture summary
- Quick start instructions
- Project structure
- Development roadmap with status
- Tech stack details
- API documentation links
- Configuration examples

#### Getting Started Guide
**File:** [GETTING_STARTED.md](./GETTING_STARTED.md)

Step-by-step guide covering:
- Prerequisites
- Quick start (5 minutes)
- Manual setup alternative
- Development workflow
- Service access information
- Database management
- Troubleshooting
- Testing your first conversation
- Learning resources

#### Environment Configuration
**File:** [.env.example](./env.example)

Template with 50+ configuration variables:
- Database connection strings
- Service endpoints
- Security settings (JWT, API keys)
- ML model paths
- Kafka configuration
- Observability settings
- SIP/voice configuration
- Storage configuration
- Feature flags

---

### 4. Development Tools

#### .gitignore
**File:** [.gitignore](/.gitignore)

Comprehensive exclusions for:
- Python artifacts
- Node.js modules
- Virtual environments
- Database files
- Large ML models
- Audio files
- Secrets and credentials
- Build artifacts

---

## 🎯 What You Can Do Now

### Immediate (Next 30 Minutes)

1. **Run Quick Start**
   ```bash
   ./scripts/setup/quickstart.sh
   ```

2. **Explore Database**
   - Go to http://localhost:8080 (Adminer)
   - Login with credentials from README
   - Browse tables, view seed data

3. **Read Architecture**
   - Review [ARCHITECTURE.md](./ARCHITECTURE.md)
   - Understand the tech stack rationale
   - Study the API specification

### This Week

1. **Implement Orchestrator Service**
   - Create `services/orchestrator/main.py`
   - Follow the API spec from ARCHITECTURE.md
   - Connect to PostgreSQL and Redis
   - Implement `/conversations/start` endpoint

2. **Build Simple NLU Service**
   - Use spaCy's TextCategorizer
   - Train on the 7 seed intents
   - Implement `/parse` endpoint

3. **Create Chat Connector**
   - WebSocket server with FastAPI
   - Connect to Orchestrator
   - Handle real-time messaging

4. **Build React Chat Widget**
   - Simple text input/output
   - WebSocket connection
   - Message history display

### This Month (Phase 1 Completion)

- Complete all Phase 1 services
- End-to-end conversation flow working
- Basic NLU with >80% accuracy
- Session state persistence
- Conversation logging to database

---

## 📊 Architecture Highlights

### System Design Patterns

1. **Microservices Architecture**
   - Each service is independently deployable
   - Communication via REST/gRPC/WebSocket
   - Shared database (Phase 1), event-driven (Phase 4+)

2. **Event-Driven (Phase 4+)**
   - Kafka for event streaming
   - Asynchronous processing
   - Real-time analytics

3. **Stateless Services**
   - Session state in Redis
   - Horizontal scaling ready
   - Load balancing friendly

### Data Flow

```
User Input (Text/Voice)
    ↓
Voice/Chat Connector
    ↓
Orchestrator
    ├→ NLU Service (Intent + Entities)
    ├→ Integration Service (External APIs)
    └→ Flow Executor (Dialogue Logic)
    ↓
Response Generation
    ├→ TTS Service (if voice)
    └→ Chat Connector (if text)
    ↓
User Output
```

### Key Features

**Multi-Channel Support**
- Voice calls via SIP (FreeSWITCH)
- Web chat via WebSocket
- REST API for integrations

**AI/ML Pipeline**
- Speech-to-Text: Whisper (99 languages)
- NLU: Transformers (intent + entities)
- Text-to-Speech: Neural voices (Coqui TTS)
- Continuous learning: Automated retraining

**Visual Flow Designer**
- Drag-and-drop interface
- No-code dialogue creation
- Version control for flows
- A/B testing support

**Enterprise Features**
- Real-time analytics dashboards
- Call recording and audit logs
- RBAC (role-based access control)
- Multi-tenant support (future)
- Compliance (GDPR, PCI-DSS ready)

---

## 🛠 Technology Justification

### Why FastAPI?
- Fastest Python framework (benchmarks)
- Auto-generated OpenAPI docs
- Native async support
- WebSocket support
- Easy integration with ML models

### Why PostgreSQL?
- JSONB for flexible schema
- Full ACID compliance
- Excellent performance at scale
- Rich extension ecosystem (TimescaleDB, PostGIS)

### Why Redis?
- Sub-millisecond latency
- Perfect for session state
- TTL for auto-cleanup
- Pub/sub for real-time updates

### Why Whisper?
- State-of-the-art accuracy
- 99 languages supported
- Open source (Apache 2.0)
- Can run on CPU or GPU

### Why Kubernetes?
- Industry standard orchestration
- Auto-scaling and self-healing
- Multi-cloud support
- Rich ecosystem (Istio, ArgoCD)

---

## 📈 Scalability Considerations

### Phase 1 (MVP)
- **Concurrent users**: 100-500
- **Infrastructure**: Single server or laptop
- **Cost**: $0 (all local/open-source)

### Phase 3 (Voice Enabled)
- **Concurrent calls**: 100-500
- **Infrastructure**: 3-5 VMs
- **Cost**: ~$200-500/month (cloud VMs + GPU)

### Phase 5 (Production)
- **Concurrent calls**: 10,000+
- **Infrastructure**: Kubernetes cluster (10-50 nodes)
- **Cost**: $2,000-10,000/month (depending on traffic)
- **Autoscaling**: HPA (Horizontal Pod Autoscaler)

### Performance Targets

| Metric | Target | Phase |
|--------|--------|-------|
| Latency (text) | < 500ms | 1 |
| Latency (voice) | < 2s | 3 |
| NLU Accuracy | > 90% | 2 |
| STT WER | < 10% | 3 |
| Uptime | 99.9% | 5 |
| Max concurrent calls | 10,000+ | 5 |

---

## 🔒 Security Considerations

### Phase 1
- Environment variables for secrets
- Password hashing (bcrypt)
- JWT authentication
- CORS configuration

### Phase 5 (Production)
- HashiCorp Vault for secrets
- TLS 1.3 everywhere
- Network policies (K8s)
- PII encryption at rest
- RBAC with OIDC/SAML
- Rate limiting (per user/IP)
- DDoS protection (CloudFlare)
- Security scanning (Snyk, Trivy)

---

## 💡 Customization Guide

### Add a New Intent

1. Insert into database:
   ```sql
   INSERT INTO intents (intent_name, description)
   VALUES ('book_flight', 'User wants to book a flight');
   ```

2. Add training examples:
   ```sql
   INSERT INTO training_examples (intent_id, example_text) VALUES
   ((SELECT intent_id FROM intents WHERE intent_name='book_flight'),
    'I want to book a flight to New York');
   ```

3. Retrain NLU model (Phase 2+)

### Add a New Dialogue Flow

1. Use the Admin UI flow designer (Phase 2+)
2. Or insert via API:
   ```bash
   curl -X POST http://localhost:8000/v1/flows \
     -d '{"flow_name": "Flight Booking", "flow_definition": {...}}'
   ```

### Add External API Integration

1. Create integration config:
   ```sql
   INSERT INTO integration_configs (integration_name, base_url, auth_type)
   VALUES ('FlightAPI', 'https://api.flights.com', 'bearer');
   ```

2. Use in dialogue flow:
   ```json
   {
     "type": "api_caller",
     "integration_name": "FlightAPI",
     "endpoint": "search",
     "params": {"from": "{origin_city}", "to": "{destination_city}"}
   }
   ```

---

## 🚀 Deployment Options

### Option 1: Local Development (Phase 1)
```bash
./scripts/setup/quickstart.sh
docker-compose up -d
```

### Option 2: Single Server (Phase 1-3)
```bash
# On Ubuntu 22.04 server
git clone <repo>
./scripts/deploy/deploy-single-server.sh
```

### Option 3: Kubernetes (Phase 5)
```bash
# Using Helm
helm install ocp-platform ./infrastructure/kubernetes/helm \
  --namespace ocp-platform \
  --create-namespace
```

### Option 4: Cloud Providers

**AWS**
- EKS (Kubernetes)
- RDS PostgreSQL
- ElastiCache Redis
- S3 for audio storage
- Terraform configs in `infrastructure/terraform/aws/`

**GCP**
- GKE (Kubernetes)
- Cloud SQL
- Memorystore Redis
- Cloud Storage
- Terraform configs in `infrastructure/terraform/gcp/`

**Azure**
- AKS (Kubernetes)
- Azure Database for PostgreSQL
- Azure Cache for Redis
- Blob Storage
- Terraform configs in `infrastructure/terraform/azure/`

---

## 📚 Learning Path

### Week 1: Understand the Architecture
- Read ARCHITECTURE.md cover to cover
- Study the database schema
- Review the API specification
- Run the quick start script

### Week 2-4: Build Phase 1
- Implement Orchestrator service
- Build NLU service
- Create chat connector
- Build React chat widget
- Test end-to-end conversation

### Week 5-10: Enhance (Phase 2)
- Integrate advanced NLU (transformers)
- Build visual flow designer
- Add entity extraction
- Connect external APIs

### Week 11-16: Add Voice (Phase 3)
- Set up FreeSWITCH
- Integrate Whisper STT
- Integrate Coqui TTS
- Test voice calls

### Week 17-22: Analytics (Phase 4)
- Set up Kafka
- Build ClickHouse pipeline
- Create Superset dashboards
- Implement retraining pipeline

### Week 23-30: Production (Phase 5)
- Migrate to Kubernetes
- Set up monitoring (Prometheus/Grafana)
- Security hardening
- Load testing
- Documentation
- Launch! 🎉

---

## 🤝 Support & Resources

### Documentation in This Repo
- [ARCHITECTURE.md](./ARCHITECTURE.md) - Complete technical spec
- [README.md](./README.md) - Project overview
- [GETTING_STARTED.md](./GETTING_STARTED.md) - Setup guide
- [docker-compose.yml](./docker-compose.yml) - Service definitions

### External Resources
- **FastAPI**: https://fastapi.tiangolo.com/
- **PostgreSQL**: https://www.postgresql.org/docs/
- **Redis**: https://redis.io/documentation
- **Whisper**: https://github.com/openai/whisper
- **Coqui TTS**: https://github.com/coqui-ai/TTS
- **Rasa**: https://rasa.com/docs/
- **FreeSWITCH**: https://freeswitch.org/confluence/
- **Kubernetes**: https://kubernetes.io/docs/

### Community
- GitHub Issues (for bugs)
- GitHub Discussions (for questions)
- Stack Overflow (tag: `ocp-platform`)

---

## 📝 License

MIT License - see [LICENSE](./LICENSE) for details.

---

## 🎉 Conclusion

You now have:

✅ Complete architecture specification (40+ pages)
✅ Production-ready database schema (11 tables, indexes, triggers)
✅ OpenAPI specification with implementation examples
✅ 5-phase development roadmap (30 weeks)
✅ Docker Compose development environment
✅ Quick start script for instant setup
✅ Comprehensive documentation
✅ Project structure and best practices

**Everything you need to build a production-grade conversational AI platform from scratch.**

---

**Ready to start building?**

```bash
./scripts/setup/quickstart.sh
```

**Good luck! 🚀**
