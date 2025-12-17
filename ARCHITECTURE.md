# Conversational AI & Customer Experience Platform
## Technical Architecture & Implementation Guide

**Version:** 1.0
**Target Architecture:** Cloud-Native Microservices
**Deployment Model:** Kubernetes/Docker Containers

---

## Table of Contents

1. [Phase 1: Recommended Tech Stack](#phase-1-recommended-tech-stack)
2. [Phase 2: Database Schema Design](#phase-2-database-schema-design)
3. [Phase 3: API Interface Design](#phase-3-api-interface-design)
4. [Phase 4: Development Roadmap](#phase-4-development-roadmap)
5. [System Architecture Overview](#system-architecture-overview)

---

## Phase 1: Recommended Tech Stack

### A. Core Services Stack

#### **Orchestrator & Business Logic**
- **Language:** Python 3.11+
- **Framework:** FastAPI (async, high-performance, auto-generated OpenAPI docs)
- **State Management:** Redis (for session state, TTL-based cleanup)
- **Workflow Engine:** Temporal.io or Apache Airflow (for complex dialogue flows)
- **Message Queue:** Apache Kafka or RabbitMQ (event streaming)

**Why FastAPI?**
- Native async support for handling concurrent conversations
- Automatic OpenAPI/Swagger documentation
- WebSocket support for real-time chat
- Easy integration with ML models via REST

#### **Frontend Admin UI**
- **Framework:** React 18+ with TypeScript
- **UI Library:** Material-UI (MUI) or Ant Design
- **State Management:** Redux Toolkit or Zustand
- **Flow Designer:** React Flow (visual dialogue editor)
- **Data Visualization:** Recharts or Apache ECharts

#### **Database Layer**
- **Primary Database:** PostgreSQL 15+ (ACID compliance, JSONB support)
- **Time-Series Analytics:** TimescaleDB (extension on PostgreSQL)
- **Cache Layer:** Redis 7+ (session state, feature flags)
- **Document Store:** MongoDB (optional, for unstructured conversation logs)
- **Search Engine:** Elasticsearch (full-text search on transcripts)

---

### B. Voice & Telephony Stack

#### **SIP/VoIP Infrastructure**

**Option 1: Production-Grade (Recommended)**
```
┌─────────────────┐
│  SIP Provider   │ (Twilio, Vonage, or Direct SIP Trunk)
└────────┬────────┘
         │
┌────────▼────────┐
│   Kamailio      │ (SIP Load Balancer + Proxy)
│   (Port 5060)   │ - High availability
└────────┬────────┘ - Session routing
         │
    ┌────┴────┐
    │         │
┌───▼──┐  ┌──▼───┐
│ FS-1 │  │ FS-2 │  FreeSWITCH Media Servers
└───┬──┘  └──┬───┘  - RTP handling
    │         │      - Audio mixing
    └────┬────┘      - Recording
         │
┌────────▼────────┐
│ Voice Connector │ (Python Service)
│   WebSocket/    │ - Streams audio to STT
│   gRPC Server   │ - Receives TTS audio
└─────────────────┘
```

**Components:**
- **Kamailio 5.6+**: SIP load balancer, session routing, failover
- **FreeSWITCH 1.10+**: Media handling, RTP termination, recording
  - Modules: `mod_sofia` (SIP), `mod_shout` (MP3), `mod_opus` (codec)
- **Alternative:** Asterisk 20+ (simpler, monolithic, good for < 1000 concurrent calls)

**Voice Connector Service:**
- Python with `asyncio` + `websockets`
- **Libraries:**
  - `pydub` for audio format conversion
  - `sounddevice` or `pyaudio` for streaming
  - `grpc` for high-performance audio streaming to STT

---

### C. AI/ML Services Stack

#### **Speech-to-Text (STT/ASR)**

**Option 1: Self-Hosted (Full Control)**
- **Whisper by OpenAI** (via faster-whisper or whisper.cpp)
  - GPU-accelerated (NVIDIA CUDA)
  - Supports 99 languages
  - Deploy with FastAPI wrapper

**Option 2: Open Source Streaming ASR**
- **Vosk** (Apache 2.0 license)
  - Lightweight, runs on CPU
  - Pre-trained models available
  - Real-time streaming support

**Option 3: Cloud-Backed (Hybrid)**
- **Google Speech-to-Text API** (fallback for complex accents)
- **Azure Cognitive Services** (good multilingual support)

**Recommended Architecture:**
```python
# Streaming ASR Service (FastAPI + WebSocket)
# Receives audio chunks, emits partial transcripts
# Supports custom vocabulary injection
```

#### **Text-to-Speech (TTS)**

**Option 1: Neural TTS (High Quality)**
- **Coqui TTS** (Mozilla's open-source engine)
  - VITS models for natural voices
  - Voice cloning support
  - GPU acceleration

**Option 2: Lightweight**
- **Piper TTS** (fast, CPU-friendly)
- **Festival** (classic, lower quality)

**Deployment:**
- Containerized with GPU support (NVIDIA Docker)
- gRPC API for low-latency audio streaming

#### **Natural Language Understanding (NLU)**

**Recommended: Rasa NLU + Custom Transformer Models**

**Stack:**
```yaml
NLU Engine:
  Intent Classification:
    - Model: DistilBERT or RoBERTa (HuggingFace)
    - Framework: PyTorch + HuggingFace Transformers

  Entity Extraction:
    - spaCy 3.6+ (custom NER models)
    - CRF layer for sequence tagging

  Dialogue Policy:
    - Rasa Core (rule-based + ML hybrid)
    - Custom policy using reinforcement learning (optional)

Context Management:
  - Redis (session context, slot filling)
  - Max TTL: 30 minutes per session
```

**Alternative: Lightweight**
- **Snips NLU** (deprecated but still usable)
- **Duckling** by Facebook (for entity extraction)

#### **Optimization & Training Loop**

**Data-Driven Retraining Pipeline:**
```
┌──────────────────┐
│ Conversation Log │
│   (PostgreSQL)   │
└────────┬─────────┘
         │
┌────────▼─────────┐
│ Label Studio or  │ (Annotation Tool)
│   Prodigy.ai     │
└────────┬─────────┘
         │
┌────────▼─────────┐
│  DVC (Data       │ (Version Control for Datasets)
│  Version Control)│
└────────┬─────────┘
         │
┌────────▼─────────┐
│  MLflow or       │ (Experiment Tracking)
│  Weights & Biases│
└────────┬─────────┘
         │
┌────────▼─────────┐
│ Automated        │ (Scheduled Retraining)
│ Retraining Job   │ - Apache Airflow DAG
└──────────────────┘ - Triggers on data volume threshold
```

**Fusion Engine (Rule + ML Hybrid):**
- **Rules Layer:** Python DSL for business logic
  ```python
  if user_intent == "check_balance" and missing("account_number"):
      return ask_for_slot("account_number")
  ```
- **ML Fallback:** When confidence < 0.7, escalate or use rules

---

### D. Data & Analytics Stack

#### **Event Streaming**
- **Apache Kafka 3.5+**
  - Topics: `voice-events`, `chat-events`, `nlu-predictions`
  - Retention: 7 days
  - Consumers: Analytics pipeline, audit logs

#### **Data Warehouse (OLAP)**
- **ClickHouse** (columnar, blazing fast for analytics)
  - Use for aggregations, dashboards
  - Real-time ingestion from Kafka

#### **Business Intelligence**
- **Apache Superset** (self-hosted, Airbnb's BI tool)
  - Pre-built dashboards: Call containment, ASR accuracy, NLU F1 scores
  - SQL Lab for ad-hoc queries

#### **Monitoring & Observability**
- **Metrics:** Prometheus + Grafana
- **Logs:** ELK Stack (Elasticsearch, Logstash, Kibana) or Loki
- **Tracing:** Jaeger or Zipkin (distributed tracing)
- **Application Monitoring:** Sentry (error tracking)

---

### E. Infrastructure & DevOps

#### **Containerization**
```dockerfile
# Each microservice gets its own Dockerfile
# Base images:
# - Python services: python:3.11-slim
# - Node services: node:20-alpine
# - ML services: nvidia/cuda:12.1-runtime-ubuntu22.04
```

#### **Orchestration**
- **Kubernetes 1.28+**
  - **Ingress:** NGINX Ingress Controller
  - **Service Mesh (optional):** Istio or Linkerd
  - **Auto-scaling:** HPA (Horizontal Pod Autoscaler) based on CPU/memory
  - **GPU Node Pool:** For STT/TTS services

**Namespace Structure:**
```yaml
- ocplatform-edge       # SIP, connectors
- ocplatform-core       # Orchestrator, NLU
- ocplatform-ai         # STT, TTS, ML models
- ocplatform-data       # Databases, Kafka
- ocplatform-analytics  # BI, monitoring
```

#### **CI/CD**
- **GitHub Actions** or **GitLab CI**
  - Build Docker images
  - Run tests (pytest, jest)
  - Deploy to staging/production via Helm charts
- **GitOps:** ArgoCD or Flux for declarative deployments

#### **Secrets Management**
- **HashiCorp Vault** or **Sealed Secrets** for Kubernetes

---

## Phase 2: Database Schema Design

### Primary Database: PostgreSQL 15+

#### **Schema: Conversations & Sessions**

```sql
-- ============================================
-- SESSION MANAGEMENT
-- ============================================

CREATE TABLE sessions (
    session_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    channel_type VARCHAR(20) NOT NULL CHECK (channel_type IN ('voice', 'chat', 'api')),

    -- Caller/User Information
    caller_id VARCHAR(50),
    user_id UUID REFERENCES users(user_id),

    -- Session Metadata
    started_at TIMESTAMP NOT NULL DEFAULT NOW(),
    ended_at TIMESTAMP,
    duration_seconds INTEGER GENERATED ALWAYS AS (
        EXTRACT(EPOCH FROM (ended_at - started_at))::INTEGER
    ) STORED,

    -- State Management
    current_state VARCHAR(100) NOT NULL DEFAULT 'started',
    context JSONB DEFAULT '{}'::jsonb,  -- Dynamic slot values

    -- Routing Information
    assigned_flow_id UUID REFERENCES dialogue_flows(flow_id),
    assigned_agent_id UUID REFERENCES human_agents(agent_id),  -- If escalated

    -- Quality Metrics
    containment_achieved BOOLEAN,  -- Did we solve without human?
    nlu_avg_confidence DECIMAL(3,2),
    user_satisfaction_score INTEGER CHECK (user_satisfaction_score BETWEEN 1 AND 5),

    -- Audit
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Indexes
CREATE INDEX idx_sessions_started_at ON sessions(started_at DESC);
CREATE INDEX idx_sessions_channel ON sessions(channel_type);
CREATE INDEX idx_sessions_flow ON sessions(assigned_flow_id);
CREATE INDEX idx_sessions_context_gin ON sessions USING gin(context);

-- ============================================
-- CONVERSATION TURNS (TRANSCRIPTS)
-- ============================================

CREATE TABLE conversation_turns (
    turn_id BIGSERIAL PRIMARY KEY,
    session_id UUID NOT NULL REFERENCES sessions(session_id) ON DELETE CASCADE,
    turn_number INTEGER NOT NULL,

    -- Speaker
    speaker VARCHAR(10) NOT NULL CHECK (speaker IN ('user', 'bot', 'agent')),

    -- User Input
    user_input_text TEXT,
    user_input_audio_url VARCHAR(500),  -- S3/MinIO URL
    user_input_language VARCHAR(10) DEFAULT 'en-US',

    -- NLU Results
    detected_intent VARCHAR(100),
    intent_confidence DECIMAL(4,3),
    extracted_entities JSONB DEFAULT '[]'::jsonb,

    -- Bot Response
    bot_response_text TEXT,
    bot_response_audio_url VARCHAR(500),
    bot_action VARCHAR(100),  -- e.g., 'ask_slot', 'api_call', 'transfer'

    -- Timing
    timestamp TIMESTAMP NOT NULL DEFAULT NOW(),
    processing_time_ms INTEGER,  -- Latency tracking

    -- Annotations (for retraining)
    is_correct_intent BOOLEAN,  -- Human feedback
    corrected_intent VARCHAR(100),
    annotation_notes TEXT,

    UNIQUE(session_id, turn_number)
);

-- Indexes
CREATE INDEX idx_turns_session ON conversation_turns(session_id, turn_number);
CREATE INDEX idx_turns_intent ON conversation_turns(detected_intent);
CREATE INDEX idx_turns_timestamp ON conversation_turns(timestamp DESC);
CREATE INDEX idx_turns_entities_gin ON conversation_turns USING gin(extracted_entities);

-- ============================================
-- DIALOGUE FLOW CONFIGURATION
-- ============================================

CREATE TABLE dialogue_flows (
    flow_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    flow_name VARCHAR(200) NOT NULL UNIQUE,
    description TEXT,

    -- Flow Definition (visual editor exports this)
    flow_definition JSONB NOT NULL,
    /* Example structure:
    {
      "nodes": [
        {
          "id": "node_1",
          "type": "intent_classifier",
          "next": "node_2"
        },
        {
          "id": "node_2",
          "type": "api_call",
          "config": {
            "endpoint": "https://api.example.com/balance",
            "method": "GET"
          },
          "next": "node_3"
        },
        {
          "id": "node_3",
          "type": "response",
          "template": "Your balance is {balance}"
        }
      ],
      "edges": [...],
      "global_intents": {
        "cancel": "node_cancel",
        "help": "node_help"
      }
    }
    */

    -- Versioning
    version INTEGER NOT NULL DEFAULT 1,
    is_active BOOLEAN DEFAULT FALSE,
    parent_flow_id UUID REFERENCES dialogue_flows(flow_id),  -- Version chain

    -- Metadata
    created_by UUID REFERENCES users(user_id),
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    published_at TIMESTAMP,

    -- A/B Testing
    traffic_percentage INTEGER DEFAULT 100 CHECK (traffic_percentage BETWEEN 0 AND 100)
);

CREATE INDEX idx_flows_active ON dialogue_flows(is_active) WHERE is_active = TRUE;

-- ============================================
-- NLU TRAINING DATA
-- ============================================

CREATE TABLE intents (
    intent_id SERIAL PRIMARY KEY,
    intent_name VARCHAR(100) NOT NULL UNIQUE,
    description TEXT,
    flow_id UUID REFERENCES dialogue_flows(flow_id),
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE training_examples (
    example_id BIGSERIAL PRIMARY KEY,
    intent_id INTEGER REFERENCES intents(intent_id) ON DELETE CASCADE,
    example_text TEXT NOT NULL,
    language VARCHAR(10) DEFAULT 'en-US',

    -- Annotations
    annotated_entities JSONB DEFAULT '[]'::jsonb,
    /* [
      {"entity": "account_type", "value": "savings", "start": 12, "end": 19}
    ] */

    -- Provenance
    source VARCHAR(50) DEFAULT 'manual',  -- 'manual', 'mined', 'synthetic'
    added_at TIMESTAMP DEFAULT NOW(),

    UNIQUE(intent_id, example_text, language)
);

CREATE INDEX idx_examples_intent ON training_examples(intent_id);

-- ============================================
-- EXTERNAL API INTEGRATIONS
-- ============================================

CREATE TABLE integration_configs (
    integration_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    integration_name VARCHAR(100) NOT NULL UNIQUE,
    integration_type VARCHAR(50) NOT NULL,  -- 'rest_api', 'graphql', 'soap', 'database'

    -- Connection Details (encrypted in production)
    base_url VARCHAR(500),
    auth_type VARCHAR(20),  -- 'bearer', 'api_key', 'oauth2'
    credentials JSONB,  -- Encrypted vault reference

    -- Request Mapping
    endpoint_mappings JSONB,
    /* {
      "get_balance": {
        "method": "GET",
        "path": "/accounts/{account_id}/balance",
        "headers": {"X-API-Key": "{{api_key}}"},
        "response_mapping": {
          "balance": "$.data.currentBalance"
        }
      }
    } */

    -- SLA & Rate Limiting
    timeout_ms INTEGER DEFAULT 5000,
    rate_limit_per_minute INTEGER,

    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT NOW()
);

-- ============================================
-- USERS & AUTHENTICATION
-- ============================================

CREATE TABLE users (
    user_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    username VARCHAR(100) NOT NULL UNIQUE,
    email VARCHAR(255) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,  -- bcrypt

    role VARCHAR(50) NOT NULL DEFAULT 'viewer',  -- 'admin', 'developer', 'analyst', 'viewer'

    is_active BOOLEAN DEFAULT TRUE,
    last_login TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE human_agents (
    agent_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(user_id),
    agent_name VARCHAR(200) NOT NULL,

    -- Skills & Routing
    skill_tags VARCHAR(50)[],  -- {'billing', 'technical_support'}
    max_concurrent_sessions INTEGER DEFAULT 5,

    is_online BOOLEAN DEFAULT FALSE,
    current_session_count INTEGER DEFAULT 0,

    created_at TIMESTAMP DEFAULT NOW()
);

-- ============================================
-- AUDIT & EVENTS
-- ============================================

CREATE TABLE audit_logs (
    log_id BIGSERIAL PRIMARY KEY,
    user_id UUID REFERENCES users(user_id),
    action VARCHAR(100) NOT NULL,  -- 'flow_published', 'model_trained', 'config_updated'
    resource_type VARCHAR(50),
    resource_id VARCHAR(100),
    details JSONB,
    ip_address INET,
    timestamp TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_audit_timestamp ON audit_logs(timestamp DESC);
CREATE INDEX idx_audit_user ON audit_logs(user_id);

-- ============================================
-- TRIGGERS (Auto-update timestamps)
-- ============================================

CREATE OR REPLACE FUNCTION update_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER sessions_updated_at BEFORE UPDATE ON sessions
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();

CREATE TRIGGER flows_updated_at BEFORE UPDATE ON dialogue_flows
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();
```

---

### Redis Schema (Session State)

```python
# Key patterns for Redis
# TTL: 30 minutes (1800 seconds)

# Active session context
# Key: session:{session_id}
# Value: JSON
{
    "session_id": "uuid",
    "current_node": "node_3",
    "slots": {
        "account_number": "12345678",
        "customer_name": "John Doe"
    },
    "conversation_history": [
        {"speaker": "user", "text": "I want to check my balance"},
        {"speaker": "bot", "text": "What's your account number?"}
    ],
    "nlu_context": {
        "last_intent": "check_balance",
        "confidence": 0.92
    },
    "metadata": {
        "started_at": "2025-01-20T10:30:00Z",
        "turn_count": 3
    }
}

# Concurrent call limiter
# Key: rate_limit:sip:{caller_id}
# Value: Integer (call count)
# TTL: 60 seconds

# Agent availability
# Key: agent:{agent_id}:status
# Value: "online" | "offline" | "busy"
```

---

### MongoDB Schema (Optional - Unstructured Logs)

```javascript
// Collection: raw_conversations
{
    _id: ObjectId,
    session_id: "uuid",
    channel: "voice",
    raw_audio_chunks: [
        {
            timestamp: ISODate("2025-01-20T10:30:05Z"),
            audio_base64: "...",  // Or S3 URL
            duration_ms: 3000
        }
    ],
    stt_raw_output: {
        partial_transcripts: [...],
        final_transcript: "I want to check my balance"
    },
    nlu_raw_output: {
        model_version: "v2.3.1",
        all_intent_probabilities: {
            "check_balance": 0.92,
            "transfer_money": 0.05,
            "close_account": 0.03
        }
    }
}
```

---

## Phase 3: API Interface Design

### Orchestrator Service - OpenAPI Specification

```yaml
openapi: 3.0.3
info:
  title: Conversational AI Orchestrator API
  version: 1.0.0
  description: |
    Central orchestration service for managing conversations across voice and chat channels.
    Handles NLU processing, dialogue flow execution, and response generation.

servers:
  - url: https://api.yourplatform.com/v1
    description: Production
  - url: http://localhost:8000/v1
    description: Local development

tags:
  - name: Conversations
    description: Session and turn management
  - name: NLU
    description: Natural language understanding
  - name: Flows
    description: Dialogue flow management

paths:
  /conversations/start:
    post:
      summary: Initialize a new conversation session
      tags: [Conversations]
      requestBody:
        required: true
        content:
          application/json:
            schema:
              type: object
              required: [channel_type]
              properties:
                channel_type:
                  type: string
                  enum: [voice, chat, api]
                caller_id:
                  type: string
                  example: "+14155551234"
                user_id:
                  type: string
                  format: uuid
                initial_context:
                  type: object
                  additionalProperties: true
                  example:
                    preferred_language: "en-US"
                    customer_tier: "premium"
                flow_id:
                  type: string
                  format: uuid
                  description: Override default flow routing
      responses:
        '201':
          description: Session created successfully
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/SessionResponse'
        '400':
          $ref: '#/components/responses/BadRequest'

  /conversations/{session_id}/process:
    post:
      summary: Process user input and get next action
      description: |
        Core endpoint that:
        1. Receives user input (text or audio reference)
        2. Runs through NLU pipeline
        3. Executes dialogue flow logic
        4. Returns bot response and next action
      tags: [Conversations]
      parameters:
        - name: session_id
          in: path
          required: true
          schema:
            type: string
            format: uuid
      requestBody:
        required: true
        content:
          application/json:
            schema:
              $ref: '#/components/schemas/UserInputRequest'
      responses:
        '200':
          description: Processing successful
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/OrchestratorResponse'
        '404':
          description: Session not found or expired
        '500':
          $ref: '#/components/responses/InternalError'

  /conversations/{session_id}/end:
    post:
      summary: Terminate a conversation session
      tags: [Conversations]
      parameters:
        - name: session_id
          in: path
          required: true
          schema:
            type: string
            format: uuid
      requestBody:
        content:
          application/json:
            schema:
              type: object
              properties:
                reason:
                  type: string
                  enum: [completed, abandoned, transferred, error]
                user_feedback:
                  type: object
                  properties:
                    satisfaction_score:
                      type: integer
                      minimum: 1
                      maximum: 5
      responses:
        '200':
          description: Session ended
          content:
            application/json:
              schema:
                type: object
                properties:
                  session_id:
                    type: string
                    format: uuid
                  duration_seconds:
                    type: integer
                  turn_count:
                    type: integer
                  summary:
                    type: object

  /nlu/parse:
    post:
      summary: Parse text for intent and entities (standalone)
      tags: [NLU]
      requestBody:
        required: true
        content:
          application/json:
            schema:
              type: object
              required: [text]
              properties:
                text:
                  type: string
                  example: "I want to transfer $500 to my savings account"
                language:
                  type: string
                  default: "en-US"
                context:
                  type: object
                  description: Additional context for disambiguation
      responses:
        '200':
          description: NLU parsing complete
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/NLUResult'

  /flows:
    get:
      summary: List all dialogue flows
      tags: [Flows]
      parameters:
        - name: is_active
          in: query
          schema:
            type: boolean
      responses:
        '200':
          description: List of flows
          content:
            application/json:
              schema:
                type: array
                items:
                  $ref: '#/components/schemas/DialogueFlow'

    post:
      summary: Create a new dialogue flow
      tags: [Flows]
      requestBody:
        required: true
        content:
          application/json:
            schema:
              $ref: '#/components/schemas/DialogueFlowCreate'
      responses:
        '201':
          description: Flow created
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/DialogueFlow'

  /flows/{flow_id}/publish:
    post:
      summary: Publish a flow version
      tags: [Flows]
      parameters:
        - name: flow_id
          in: path
          required: true
          schema:
            type: string
            format: uuid
      requestBody:
        content:
          application/json:
            schema:
              type: object
              properties:
                traffic_percentage:
                  type: integer
                  minimum: 0
                  maximum: 100
                  default: 100
                  description: For A/B testing
      responses:
        '200':
          description: Flow published

components:
  schemas:
    SessionResponse:
      type: object
      properties:
        session_id:
          type: string
          format: uuid
        channel_type:
          type: string
          enum: [voice, chat, api]
        started_at:
          type: string
          format: date-time
        initial_message:
          type: string
          example: "Hello! How can I help you today?"
        initial_audio_url:
          type: string
          description: TTS audio URL for voice channel

    UserInputRequest:
      type: object
      required: [input_type]
      properties:
        input_type:
          type: string
          enum: [text, audio]
        text:
          type: string
          example: "What's my account balance?"
          description: Required if input_type=text
        audio_url:
          type: string
          description: Required if input_type=audio. URL to audio file or base64 data
        language:
          type: string
          default: "en-US"
        metadata:
          type: object
          additionalProperties: true

    OrchestratorResponse:
      type: object
      properties:
        session_id:
          type: string
          format: uuid
        turn_number:
          type: integer

        # NLU Results
        nlu:
          $ref: '#/components/schemas/NLUResult'

        # Bot Response
        response:
          type: object
          properties:
            type:
              type: string
              enum: [text, audio, adaptive_card]
            text:
              type: string
              example: "Your current balance is $1,234.56"
            audio_url:
              type: string
              description: TTS-generated audio (for voice channel)
            ssml:
              type: string
              description: SSML markup for advanced TTS

        # Next Action
        next_action:
          type: object
          properties:
            action_type:
              type: string
              enum: [continue, wait_for_input, transfer_to_agent, end_conversation, execute_api_call]
            action_config:
              type: object
              description: Action-specific configuration

        # Context Updates
        updated_context:
          type: object
          description: New slot values filled

        # Metadata
        processing_time_ms:
          type: integer
        confidence_score:
          type: number
          format: float
          minimum: 0
          maximum: 1

    NLUResult:
      type: object
      properties:
        intent:
          type: object
          properties:
            name:
              type: string
              example: "check_balance"
            confidence:
              type: number
              format: float
              example: 0.92
        entities:
          type: array
          items:
            type: object
            properties:
              entity_type:
                type: string
                example: "account_type"
              value:
                type: string
                example: "savings"
              confidence:
                type: number
                format: float
              start_char:
                type: integer
              end_char:
                type: integer
        sentiment:
          type: object
          properties:
            label:
              type: string
              enum: [positive, neutral, negative]
            score:
              type: number
              format: float

    DialogueFlow:
      type: object
      properties:
        flow_id:
          type: string
          format: uuid
        flow_name:
          type: string
        version:
          type: integer
        is_active:
          type: boolean
        flow_definition:
          type: object
          description: JSON graph of nodes and edges
        created_at:
          type: string
          format: date-time
        updated_at:
          type: string
          format: date-time

    DialogueFlowCreate:
      type: object
      required: [flow_name, flow_definition]
      properties:
        flow_name:
          type: string
        description:
          type: string
        flow_definition:
          type: object

  responses:
    BadRequest:
      description: Invalid request
      content:
        application/json:
          schema:
            type: object
            properties:
              error:
                type: string
              details:
                type: object

    InternalError:
      description: Server error
      content:
        application/json:
          schema:
            type: object
            properties:
              error:
                type: string
              trace_id:
                type: string

  securitySchemes:
    BearerAuth:
      type: http
      scheme: bearer
      bearerFormat: JWT

security:
  - BearerAuth: []
```

---

### Implementation: Orchestrator Core Logic (Python)

```python
# orchestrator/main.py

from fastapi import FastAPI, HTTPException, Depends
from fastapi.responses import JSONResponse
import redis.asyncio as redis
from sqlalchemy.ext.asyncio import AsyncSession
import uuid
from datetime import datetime
from typing import Optional, Dict, Any

app = FastAPI(title="Orchestrator API", version="1.0.0")

# Dependencies
redis_client = redis.from_url("redis://localhost:6379", decode_responses=True)

# ============================================
# CORE ORCHESTRATOR ENDPOINT
# ============================================

@app.post("/v1/conversations/{session_id}/process")
async def process_turn(
    session_id: uuid.UUID,
    request: UserInputRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Main orchestration flow:
    1. Validate session exists
    2. Transcribe audio (if voice)
    3. Run NLU
    4. Execute dialogue flow logic
    5. Call external APIs if needed
    6. Generate response
    7. Convert to speech (if voice)
    8. Update session state
    9. Log to database
    """

    # Step 1: Get session context
    session_context = await get_session_context(session_id)
    if not session_context:
        raise HTTPException(status_code=404, detail="Session not found or expired")

    # Step 2: Transcribe audio (if needed)
    if request.input_type == "audio":
        user_text = await transcribe_audio(request.audio_url)
    else:
        user_text = request.text

    # Step 3: Run NLU
    nlu_result = await run_nlu_pipeline(
        text=user_text,
        language=request.language,
        context=session_context["slots"]
    )

    # Step 4: Execute dialogue flow
    flow_result = await execute_dialogue_flow(
        flow_id=session_context["flow_id"],
        current_node=session_context["current_node"],
        intent=nlu_result["intent"]["name"],
        entities=nlu_result["entities"],
        session_context=session_context
    )

    # Step 5: External API calls (if needed)
    if flow_result["next_action"]["action_type"] == "execute_api_call":
        api_response = await call_external_api(
            integration_name=flow_result["api_integration"],
            endpoint=flow_result["api_endpoint"],
            params=flow_result["api_params"]
        )
        flow_result["context_updates"].update(api_response)

    # Step 6: Generate response text
    response_text = render_template(
        template=flow_result["response_template"],
        context={**session_context["slots"], **flow_result["context_updates"]}
    )

    # Step 7: TTS (if voice channel)
    audio_url = None
    if session_context["channel_type"] == "voice":
        audio_url = await synthesize_speech(
            text=response_text,
            language=request.language,
            voice_id=session_context.get("voice_preference", "default")
        )

    # Step 8: Update session state in Redis
    await update_session_context(
        session_id=session_id,
        current_node=flow_result["next_node"],
        context_updates=flow_result["context_updates"],
        turn_count_increment=1
    )

    # Step 9: Log conversation turn to database
    turn_number = session_context["turn_count"] + 1
    await db.execute(
        insert(conversation_turns).values(
            session_id=session_id,
            turn_number=turn_number,
            speaker="user",
            user_input_text=user_text,
            detected_intent=nlu_result["intent"]["name"],
            intent_confidence=nlu_result["intent"]["confidence"],
            extracted_entities=nlu_result["entities"],
            bot_response_text=response_text,
            bot_response_audio_url=audio_url,
            bot_action=flow_result["next_action"]["action_type"],
            processing_time_ms=flow_result["processing_time_ms"]
        )
    )
    await db.commit()

    # Step 10: Publish event to Kafka
    await publish_event(
        topic="conversation-events",
        event={
            "event_type": "turn_completed",
            "session_id": str(session_id),
            "turn_number": turn_number,
            "intent": nlu_result["intent"]["name"],
            "timestamp": datetime.utcnow().isoformat()
        }
    )

    # Return orchestrated response
    return OrchestratorResponse(
        session_id=session_id,
        turn_number=turn_number,
        nlu=nlu_result,
        response={
            "type": "audio" if audio_url else "text",
            "text": response_text,
            "audio_url": audio_url
        },
        next_action=flow_result["next_action"],
        updated_context=flow_result["context_updates"],
        processing_time_ms=flow_result["processing_time_ms"],
        confidence_score=nlu_result["intent"]["confidence"]
    )


# ============================================
# HELPER FUNCTIONS
# ============================================

async def run_nlu_pipeline(text: str, language: str, context: Dict) -> Dict:
    """
    Calls the NLU microservice via gRPC or HTTP
    """
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "http://nlu-service:8001/parse",
            json={
                "text": text,
                "language": language,
                "context": context
            },
            timeout=2.0
        )
        return response.json()


async def execute_dialogue_flow(
    flow_id: uuid.UUID,
    current_node: str,
    intent: str,
    entities: list,
    session_context: Dict
) -> Dict:
    """
    State machine executor:
    - Loads flow definition from database
    - Finds current node
    - Applies business logic / rules
    - Determines next node
    - Returns response template
    """
    # Load flow from cache or DB
    flow_def = await get_flow_definition(flow_id)

    # Get current node config
    node = flow_def["nodes"][current_node]

    # Execute node logic
    if node["type"] == "intent_router":
        next_node = node["intent_mapping"].get(intent, node["default_next"])

    elif node["type"] == "slot_filler":
        required_slot = node["slot_name"]
        slot_value = extract_entity_value(entities, required_slot)

        if slot_value:
            return {
                "next_node": node["next_on_filled"],
                "context_updates": {required_slot: slot_value},
                "response_template": node["acknowledgment_template"],
                "next_action": {"action_type": "continue"}
            }
        else:
            return {
                "next_node": current_node,  # Stay on same node
                "context_updates": {},
                "response_template": node["prompt_template"],
                "next_action": {"action_type": "wait_for_input"}
            }

    elif node["type"] == "api_caller":
        return {
            "next_node": node["next"],
            "response_template": "Processing your request...",
            "next_action": {"action_type": "execute_api_call"},
            "api_integration": node["integration_name"],
            "api_endpoint": node["endpoint"],
            "api_params": render_params(node["params"], session_context["slots"])
        }

    elif node["type"] == "response":
        return {
            "next_node": None,
            "context_updates": {},
            "response_template": node["template"],
            "next_action": {"action_type": "end_conversation"}
        }


async def transcribe_audio(audio_url: str) -> str:
    """
    Calls STT service (e.g., Whisper API)
    """
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "http://stt-service:8002/transcribe",
            json={"audio_url": audio_url},
            timeout=10.0
        )
        return response.json()["transcript"]


async def synthesize_speech(text: str, language: str, voice_id: str) -> str:
    """
    Calls TTS service, returns URL to generated audio
    """
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "http://tts-service:8003/synthesize",
            json={
                "text": text,
                "language": language,
                "voice_id": voice_id
            },
            timeout=5.0
        )
        return response.json()["audio_url"]
```

---

## Phase 4: Development Roadmap (MVP to Production)

### 5-Phase Implementation Plan

---

### **Phase 1: Foundation - Text-Based Bot (Weeks 1-4)**

**Goal:** Build a working text chatbot with basic NLU and hardcoded flows.

#### Deliverables:
1. **Backend Setup**
   - Initialize FastAPI project
   - Set up PostgreSQL with initial schema
   - Configure Redis for session management
   - Create basic Docker Compose setup

2. **Core Services**
   - `orchestrator-service` (FastAPI)
   - `nlu-service` (simple intent classifier using spaCy or HuggingFace)
   - `chat-connector` (WebSocket server)

3. **Simple NLU**
   - Train basic intent classifier (5-10 intents)
   - Example intents: `greet`, `check_balance`, `transfer_money`, `goodbye`
   - Use spaCy's TextCategorizer or fine-tune DistilBERT

4. **Hardcoded Dialogue Flow**
   - Implement a simple state machine in Python
   - Example flow: Greet → Ask for account → Check balance → Goodbye

5. **Frontend MVP**
   - React chat widget
   - Simple text input/output interface

#### Success Criteria:
- User can chat via web interface
- Bot recognizes 5+ intents with >80% accuracy
- Session state persists across messages
- Conversation logged to database

#### Tech Stack for Phase 1:
```yaml
Backend: FastAPI, PostgreSQL, Redis
NLU: spaCy 3.6 + custom TextCategorizer
Frontend: React + Material-UI
Deployment: Docker Compose (local)
```

---

### **Phase 2: Advanced NLU & Flow Editor (Weeks 5-10)**

**Goal:** Upgrade NLU to production-grade; build visual flow designer.

#### Deliverables:
1. **Enhanced NLU**
   - Integrate Rasa NLU or fine-tune RoBERTa
   - Add entity extraction (dates, amounts, account numbers)
   - Implement context-aware intent classification

2. **Visual Flow Designer**
   - React Flow-based editor
   - Drag-and-drop nodes: Intent Router, API Call, Response, Slot Filler
   - Save flows as JSON to `dialogue_flows` table

3. **External API Integration**
   - Create `integration-service` to call REST APIs
   - Example: Mock banking API for balance/transactions
   - Implement OAuth2 authentication

4. **Testing & Annotation Tool**
   - Integrate Label Studio for labeling mis-classified utterances
   - Auto-retrain NLU weekly based on new data

#### Success Criteria:
- Non-technical users can design flows via UI
- NLU accuracy >90% on test set
- Successful external API integration (e.g., fetch real data)

#### Tech Stack Addition:
```yaml
NLU: Rasa NLU + RoBERTa (HuggingFace)
Flow Editor: React Flow
Annotation: Label Studio
API Gateway: Kong or custom FastAPI middleware
```

---

### **Phase 3: Voice Integration (Weeks 11-16)**

**Goal:** Add voice capabilities (SIP, STT, TTS).

#### Deliverables:
1. **SIP Infrastructure**
   - Deploy FreeSWITCH on a VM or container
   - Configure SIP trunk (Twilio or local PBX)
   - Implement `voice-connector` service to stream audio

2. **Speech-to-Text**
   - Deploy Whisper (faster-whisper) with GPU
   - Set up WebSocket streaming for real-time ASR
   - Handle audio formats (WAV, OPUS, G.711)

3. **Text-to-Speech**
   - Deploy Coqui TTS with VITS model
   - Generate audio in real-time (< 500ms latency)
   - Support SSML for expressive speech

4. **End-to-End Voice Flow**
   - User calls via SIP → FreeSWITCH → Voice Connector → Orchestrator
   - Orchestrator processes → TTS → Audio sent back to caller

5. **Call Recording & Monitoring**
   - Store call recordings in S3/MinIO
   - Build real-time call dashboard (active calls, duration)

#### Success Criteria:
- User can call a phone number and interact via voice
- Latency < 2 seconds (user speaks → bot responds)
- 95%+ STT word accuracy

#### Tech Stack Addition:
```yaml
SIP: FreeSWITCH 1.10
STT: Whisper (faster-whisper) on NVIDIA GPU
TTS: Coqui TTS (VITS)
Audio Storage: MinIO (S3-compatible)
```

---

### **Phase 4: Analytics & Optimization (Weeks 17-22)**

**Goal:** Build data pipeline, dashboards, and retraining loop.

#### Deliverables:
1. **Event Streaming**
   - Deploy Apache Kafka
   - Stream events: `conversation_started`, `intent_detected`, `api_called`, `conversation_ended`
   - Consumers: Database sink, analytics engine

2. **Data Warehouse**
   - Set up ClickHouse for OLAP queries
   - Create materialized views for:
     - Call containment rate (% resolved without human)
     - Average handling time
     - Intent accuracy trends

3. **BI Dashboards**
   - Deploy Apache Superset
   - Pre-built dashboards:
     - Real-time call volume
     - Top failure intents
     - User satisfaction scores

4. **Automated Retraining Pipeline**
   - Apache Airflow DAG:
     - Daily: Export mis-classified intents
     - Weekly: Retrain NLU if >100 new labels
     - Monthly: Full model re-evaluation

5. **A/B Testing Framework**
   - Support multiple flow versions
   - Route % of traffic to new flows
   - Compare KPIs (containment, satisfaction)

#### Success Criteria:
- Dashboards show real-time metrics
- Automated retraining improves accuracy by 5%+
- A/B tests run with statistical significance

#### Tech Stack Addition:
```yaml
Streaming: Apache Kafka
OLAP: ClickHouse
Orchestration: Apache Airflow
BI: Apache Superset
Experimentation: Custom A/B framework
```

---

### **Phase 5: Production Hardening & Scale (Weeks 23-30)**

**Goal:** Kubernetes deployment, monitoring, security, and scale testing.

#### Deliverables:
1. **Kubernetes Deployment**
   - Migrate Docker Compose to Helm charts
   - Namespaces: `edge`, `core`, `ai`, `data`, `analytics`
   - Autoscaling: HPA for orchestrator (CPU/memory triggers)
   - GPU nodes for STT/TTS

2. **Observability**
   - Metrics: Prometheus + Grafana
     - Dashboards: Request rate, error rate, latency (RED metrics)
   - Logs: ELK Stack or Grafana Loki
   - Tracing: Jaeger for distributed tracing
   - Alerts: PagerDuty integration for critical failures

3. **Security**
   - API Gateway with rate limiting (Kong or Traefik)
   - JWT authentication for all APIs
   - Secrets management: HashiCorp Vault
   - RBAC in Kubernetes
   - Encrypt audio storage (MinIO with SSE)

4. **Load Testing**
   - Simulate 1000 concurrent calls using SIPp
   - Identify bottlenecks (likely: NLU, database writes)
   - Optimize:
     - Cache NLU models in memory
     - Batch database inserts
     - Use read replicas for PostgreSQL

5. **Documentation**
   - API docs (auto-generated from OpenAPI)
   - Architecture diagrams (Mermaid or draw.io)
   - Runbooks for common issues
   - User guides for flow designer

6. **CI/CD**
   - GitHub Actions pipeline:
     - Lint (black, flake8)
     - Test (pytest with 80% coverage)
     - Build Docker images
     - Deploy to staging
     - Automated integration tests
   - GitOps with ArgoCD

#### Success Criteria:
- System handles 1000 concurrent calls without degradation
- 99.9% uptime over 30 days
- Mean time to recovery (MTTR) < 15 minutes
- Complete disaster recovery plan

#### Tech Stack Addition:
```yaml
Orchestration: Kubernetes (GKE, EKS, or self-managed)
Monitoring: Prometheus + Grafana + Jaeger
Security: Vault, OAuth2 Proxy
Load Testing: SIPp, Locust
CI/CD: GitHub Actions, ArgoCD
```

---

## System Architecture Overview

### High-Level Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                            EDGE LAYER (Ingress)                              │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                               │
│  ┌──────────────┐      ┌──────────────┐      ┌──────────────┐              │
│  │  SIP Trunk   │      │  WebSocket   │      │  REST API    │              │
│  │  (Twilio/    │      │  Chat Widget │      │  (External   │              │
│  │  Kamailio)   │      │              │      │  Integrations│              │
│  └──────┬───────┘      └──────┬───────┘      └──────┬───────┘              │
│         │                     │                     │                        │
│         │                     │                     │                        │
│  ┌──────▼───────┐      ┌─────▼────────┐      ┌─────▼────────┐              │
│  │ FreeSWITCH   │      │    Chat      │      │   API        │              │
│  │ Media Server │      │  Connector   │      │  Gateway     │              │
│  │ (RTP/Audio)  │      │  Service     │      │  (Kong)      │              │
│  └──────┬───────┘      └─────┬────────┘      └─────┬────────┘              │
│         │                     │                     │                        │
│         └─────────────────────┼─────────────────────┘                        │
│                               │                                              │
└───────────────────────────────┼──────────────────────────────────────────────┘
                                │
                                │
┌───────────────────────────────▼──────────────────────────────────────────────┐
│                         CORE ORCHESTRATION LAYER                             │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                               │
│                    ┌────────────────────────────┐                            │
│                    │   ORCHESTRATOR SERVICE     │                            │
│                    │   (FastAPI + Temporal)     │                            │
│                    │                            │                            │
│                    │  ┌──────────────────────┐  │                            │
│                    │  │  Session Manager     │  │                            │
│                    │  │  (Redis Cache)       │  │                            │
│                    │  └──────────────────────┘  │                            │
│                    │                            │                            │
│                    │  ┌──────────────────────┐  │                            │
│                    │  │  Flow Executor       │  │                            │
│                    │  │  (State Machine)     │  │                            │
│                    │  └──────────────────────┘  │                            │
│                    │                            │                            │
│                    │  ┌──────────────────────┐  │                            │
│                    │  │  Integration Hub     │  │                            │
│                    │  │  (External APIs)     │  │                            │
│                    │  └──────────────────────┘  │                            │
│                    └────────┬───────────────────┘                            │
│                             │                                                │
│              ┌──────────────┼──────────────┐                                 │
│              │              │              │                                 │
└──────────────┼──────────────┼──────────────┼─────────────────────────────────┘
               │              │              │
               │              │              │
┌──────────────▼──────────────▼──────────────▼─────────────────────────────────┐
│                          AI/ML SERVICES LAYER                                 │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                               │
│  ┌──────────────┐      ┌──────────────┐      ┌──────────────┐              │
│  │  STT Service │      │ NLU Service  │      │ TTS Service  │              │
│  │  (Whisper)   │      │ (Rasa/BERT)  │      │ (Coqui TTS)  │              │
│  │              │      │              │      │              │              │
│  │ - Streaming  │      │ - Intent     │      │ - SSML       │              │
│  │ - Multi-lang │      │ - Entities   │      │ - Voices     │              │
│  │ - GPU        │      │ - Context    │      │ - GPU        │              │
│  └──────────────┘      └──────┬───────┘      └──────────────┘              │
│                                │                                              │
│                         ┌──────▼───────┐                                     │
│                         │  Optimization │                                     │
│                         │  Loop Service │                                     │
│                         │               │                                     │
│                         │ - Retraining  │                                     │
│                         │ - A/B Testing │                                     │
│                         │ - Model Mgmt  │                                     │
│                         └───────────────┘                                     │
│                                                                               │
└───────────────────────────────────────────────────────────────────────────────┘
                                │
                                │
┌───────────────────────────────▼───────────────────────────────────────────────┐
│                          DATA & STORAGE LAYER                                 │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                               │
│  ┌──────────────┐   ┌──────────────┐   ┌──────────────┐   ┌──────────────┐ │
│  │ PostgreSQL   │   │    Redis     │   │  ClickHouse  │   │    MinIO     │ │
│  │              │   │              │   │              │   │              │ │
│  │ - Sessions   │   │ - State      │   │ - Analytics  │   │ - Audio      │ │
│  │ - Transcripts│   │ - Cache      │   │ - OLAP       │   │ - Recordings │ │
│  │ - Flows      │   │ - Locks      │   │ - Time-series│   │ - Backups    │ │
│  └──────────────┘   └──────────────┘   └──────────────┘   └──────────────┘ │
│                                                                               │
│                         ┌────────────────────────┐                            │
│                         │    Apache Kafka        │                            │
│                         │                        │                            │
│                         │  Topics:               │                            │
│                         │  - voice-events        │                            │
│                         │  - chat-events         │                            │
│                         │  - nlu-predictions     │                            │
│                         └────────────────────────┘                            │
│                                                                               │
└───────────────────────────────────────────────────────────────────────────────┘
                                │
                                │
┌───────────────────────────────▼───────────────────────────────────────────────┐
│                      ANALYTICS & MONITORING LAYER                             │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                               │
│  ┌──────────────┐   ┌──────────────┐   ┌──────────────┐   ┌──────────────┐ │
│  │   Superset   │   │  Prometheus  │   │    Grafana   │   │    Jaeger    │ │
│  │              │   │              │   │              │   │              │ │
│  │ - Dashboards │   │ - Metrics    │   │ - Alerts     │   │ - Tracing    │ │
│  │ - Reports    │   │ - Scraping   │   │ - Viz        │   │ - Spans      │ │
│  └──────────────┘   └──────────────┘   └──────────────┘   └──────────────┘ │
│                                                                               │
│                         ┌────────────────────────┐                            │
│                         │    Admin UI (React)    │                            │
│                         │                        │                            │
│                         │  - Flow Designer       │                            │
│                         │  - User Management     │                            │
│                         │  - Real-time Monitor   │                            │
│                         └────────────────────────┘                            │
│                                                                               │
└───────────────────────────────────────────────────────────────────────────────┘
```

---

## Appendix: Additional Considerations

### Security Best Practices

1. **PII/PHI Protection**
   - Encrypt sensitive fields in database (account numbers, SSN)
   - Implement data retention policies (GDPR compliance)
   - Redact sensitive entities from logs

2. **Authentication & Authorization**
   - JWT tokens with short expiration (15 min)
   - Refresh token rotation
   - RBAC for admin UI (roles: admin, developer, analyst, viewer)

3. **Network Security**
   - TLS 1.3 for all services
   - Private subnets for databases
   - VPN access for admin tools

### Scalability Considerations

1. **Horizontal Scaling**
   - Stateless services (orchestrator, NLU, TTS, STT)
   - Kubernetes HPA based on CPU/memory
   - Load balancing via Kubernetes Service

2. **Database Optimization**
   - Partitioning: `conversation_turns` by date (monthly partitions)
   - Read replicas for analytics queries
   - Connection pooling (PgBouncer)

3. **Caching Strategy**
   - Cache NLU models in memory (lazy load)
   - Cache flow definitions in Redis (TTL: 5 min)
   - CDN for TTS audio files (CloudFront, Cloudflare)

### Cost Optimization

1. **GPU Usage**
   - Use GPU nodes only for STT/TTS
   - Auto-scale down during off-peak hours
   - Consider spot instances for batch training

2. **Storage**
   - Lifecycle policies: Move old recordings to Glacier after 90 days
   - Compress audio files (Opus codec)

3. **Open Source First**
   - Avoid vendor lock-in (use S3-compatible MinIO instead of AWS S3)
   - Self-host when traffic is high (cheaper than SaaS at scale)

---

## Next Steps

1. **Review this document** and clarify any questions
2. **Choose deployment target** (local, AWS, GCP, Azure, on-prem)
3. **Set up development environment** (Docker, Kubernetes, IDEs)
4. **Start Phase 1** (text-based bot MVP)

---

**Document Version:** 1.0
**Last Updated:** 2025-01-20
**Maintained By:** Cloud AI Platform Team
