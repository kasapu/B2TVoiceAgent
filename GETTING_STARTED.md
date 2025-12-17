# Getting Started with OCP Platform

This guide will walk you through setting up your development environment and building your first conversational AI application.

## Prerequisites

Before you begin, ensure you have the following installed:

### Required
- **Docker** 24.0+ ([Install Docker](https://docs.docker.com/get-docker/))
- **Docker Compose** 2.0+ ([Install Docker Compose](https://docs.docker.com/compose/install/))
- **Git** ([Install Git](https://git-scm.com/downloads))

### Optional (for local development without Docker)
- **Python** 3.11+ ([Install Python](https://www.python.org/downloads/))
- **Node.js** 20+ ([Install Node.js](https://nodejs.org/))
- **PostgreSQL** 15+ ([Install PostgreSQL](https://www.postgresql.org/download/))
- **Redis** 7+ ([Install Redis](https://redis.io/download))

## Quick Start (5 Minutes)

### Step 1: Clone the Repository

```bash
git clone <your-repo-url>
cd OCPplatform
```

### Step 2: Run the Quick Start Script

```bash
./scripts/setup/quickstart.sh
```

This script will:
- Check prerequisites
- Create `.env` file with generated secrets
- Start PostgreSQL and Redis
- Initialize the database with schema and seed data
- Display access information

### Step 3: Verify Installation

```bash
# Check running services
docker-compose ps

# Access database
docker-compose exec postgres psql -U ocpuser -d ocplatform -c "SELECT COUNT(*) FROM intents;"
```

You should see 7 intents loaded.

## Manual Setup (Alternative)

If you prefer to set up manually:

### 1. Create Environment File

```bash
cp .env.example .env
```

Edit `.env` and update the following:
- `JWT_SECRET`: Generate with `openssl rand -hex 32`
- `DATABASE_URL`: Update if using different credentials
- Other settings as needed

### 2. Start Infrastructure Services

```bash
docker-compose up -d postgres redis
```

### 3. Wait for Services to Start

```bash
# Wait for PostgreSQL
until docker-compose exec postgres pg_isready -U ocpuser; do
  echo "Waiting for PostgreSQL..."
  sleep 2
done

# Verify Redis
docker-compose exec redis redis-cli ping
```

### 4. Verify Database

```bash
docker-compose exec postgres psql -U ocpuser -d ocplatform
```

Run SQL query:
```sql
SELECT table_name FROM information_schema.tables WHERE table_schema = 'public';
```

You should see tables like `sessions`, `conversation_turns`, `dialogue_flows`, etc.

## Next Steps

### Phase 1: Build a Text-Based Chatbot

Now that your infrastructure is ready, you'll build the core services. Choose your path:

#### Option A: Follow the Tutorial (Recommended for Beginners)

See [docs/guides/phase1-tutorial.md](./docs/guides/phase1-tutorial.md) for a step-by-step guide to build:
1. Orchestrator service (FastAPI)
2. NLU service (spaCy or HuggingFace)
3. Chat connector (WebSocket)
4. React chat widget

#### Option B: Use Starter Code (Coming Soon)

Pre-built starter templates for each service will be available in the `examples/` directory.

#### Option C: Build from Architecture Spec

Review [ARCHITECTURE.md](./ARCHITECTURE.md) and implement services following the OpenAPI specification.

### Directory Structure for Phase 1

Create your first service:

```bash
cd services/orchestrator
```

Your service should have this structure:

```
orchestrator/
├── main.py              # FastAPI application
├── requirements.txt     # Python dependencies
├── Dockerfile           # Container definition
├── app/
│   ├── __init__.py
│   ├── api/            # API routes
│   │   ├── conversations.py
│   │   └── health.py
│   ├── models/         # Pydantic models
│   │   └── schemas.py
│   ├── services/       # Business logic
│   │   ├── session_manager.py
│   │   ├── flow_executor.py
│   │   └── nlu_client.py
│   └── db/            # Database operations
│       ├── connection.py
│       └── repositories.py
├── tests/
│   ├── test_api.py
│   └── test_services.py
└── alembic/           # Database migrations (optional)
```

## Development Workflow

### 1. Start Infrastructure

```bash
docker-compose up -d postgres redis
```

### 2. Develop Services Locally

For each service (orchestrator, nlu-service, etc.):

```bash
cd services/orchestrator

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Run service
uvicorn main:app --reload --port 8000
```

### 3. Run Tests

```bash
pytest tests/ -v
```

### 4. Build Docker Image

```bash
docker build -t ocp-orchestrator:latest .
```

### 5. Run with Docker Compose

```bash
# Start all services
docker-compose up -d

# View logs
docker-compose logs -f orchestrator

# Stop services
docker-compose down
```

## Accessing Services

Once services are running:

| Service | URL | Purpose |
|---------|-----|---------|
| Orchestrator API | http://localhost:8000 | Main API |
| Swagger UI | http://localhost:8000/docs | API documentation |
| NLU Service | http://localhost:8001 | Intent classification |
| Chat Connector | http://localhost:8004 | WebSocket chat |
| Chat Widget | http://localhost:3000 | Frontend UI |
| Adminer | http://localhost:8080 | Database UI |
| Prometheus | http://localhost:9090 | Metrics (Phase 5) |
| Grafana | http://localhost:3001 | Dashboards (Phase 5) |

## Database Management

### View Data

Using Adminer UI:
1. Go to http://localhost:8080
2. Login:
   - System: PostgreSQL
   - Server: postgres
   - Username: ocpuser
   - Password: ocppassword
   - Database: ocplatform

### Using psql

```bash
# Connect to database
docker-compose exec postgres psql -U ocpuser -d ocplatform

# List tables
\dt

# Query sessions
SELECT * FROM sessions ORDER BY started_at DESC LIMIT 10;

# Query conversation turns
SELECT * FROM conversation_turns WHERE session_id = 'your-session-id';

# Exit
\q
```

### Backup Database

```bash
docker-compose exec postgres pg_dump -U ocpuser ocplatform > backup.sql
```

### Restore Database

```bash
docker-compose exec -T postgres psql -U ocpuser ocplatform < backup.sql
```

## Troubleshooting

### Services Won't Start

```bash
# Check Docker logs
docker-compose logs

# Check specific service
docker-compose logs postgres

# Restart services
docker-compose restart

# Clean restart (removes volumes)
docker-compose down -v
./scripts/setup/quickstart.sh
```

### Database Connection Errors

```bash
# Check PostgreSQL is running
docker-compose ps postgres

# Check PostgreSQL logs
docker-compose logs postgres

# Test connection
docker-compose exec postgres pg_isready -U ocpuser

# Verify credentials in .env match docker-compose.yml
```

### Port Already in Use

```bash
# Find process using port 5432
lsof -i :5432  # On Linux/Mac
netstat -ano | findstr :5432  # On Windows

# Change ports in docker-compose.yml
# Example: "5433:5432" instead of "5432:5432"
```

### Permission Denied Errors

```bash
# On Linux, you may need to add your user to docker group
sudo usermod -aG docker $USER

# Log out and log back in

# Or run with sudo (not recommended)
sudo docker-compose up -d
```

## Development Tips

### Hot Reload

All services are configured with hot reload in development:
- **FastAPI**: `--reload` flag enables auto-restart
- **React**: Create React App hot module replacement

Just save your files and changes will apply automatically.

### Environment-Specific Configuration

Create multiple environment files:
- `.env` - Development (local)
- `.env.staging` - Staging environment
- `.env.production` - Production environment

Load with:
```bash
docker-compose --env-file .env.staging up -d
```

### Debugging Services

#### Python Services

Add this to your code:
```python
import pdb; pdb.set_trace()
```

Run service in attached mode:
```bash
docker-compose run --rm --service-ports orchestrator
```

#### View Real-Time Logs

```bash
# All services
docker-compose logs -f

# Specific service
docker-compose logs -f orchestrator

# Last 100 lines
docker-compose logs --tail=100 orchestrator
```

## Testing Your First Conversation

### 1. Start Orchestrator (Manual Test)

```bash
cd services/orchestrator
uvicorn main:app --reload
```

### 2. Create a Session

```bash
curl -X POST http://localhost:8000/v1/conversations/start \
  -H "Content-Type: application/json" \
  -d '{
    "channel_type": "chat"
  }'
```

Response:
```json
{
  "session_id": "123e4567-e89b-12d3-a456-426614174000",
  "channel_type": "chat",
  "started_at": "2025-01-20T10:30:00Z",
  "initial_message": "Hello! How can I help you today?"
}
```

### 3. Process User Input

```bash
curl -X POST http://localhost:8000/v1/conversations/123e4567-e89b-12d3-a456-426614174000/process \
  -H "Content-Type: application/json" \
  -d '{
    "input_type": "text",
    "text": "I want to check my balance"
  }'
```

## Learning Resources

### Documentation
- [ARCHITECTURE.md](./ARCHITECTURE.md) - Complete technical specification
- [README.md](./README.md) - Project overview
- [docs/api/](./docs/api/) - API documentation
- [docs/guides/](./docs/guides/) - How-to guides

### Code Examples
- [examples/simple-bot/](./examples/simple-bot/) - Minimal working bot
- [examples/banking-bot/](./examples/banking-bot/) - Full-featured example

### External Resources
- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [PostgreSQL Documentation](https://www.postgresql.org/docs/)
- [Docker Documentation](https://docs.docker.com/)
- [Rasa Documentation](https://rasa.com/docs/)
- [HuggingFace Transformers](https://huggingface.co/docs/transformers/)

## What's Next?

After completing Phase 1 (text-based chatbot), you can:

1. **Phase 2**: Add visual flow designer and advanced NLU
2. **Phase 3**: Integrate voice capabilities (SIP, STT, TTS)
3. **Phase 4**: Build analytics dashboards and retraining pipeline
4. **Phase 5**: Deploy to Kubernetes with full observability

See [ARCHITECTURE.md - Phase 4: Development Roadmap](./ARCHITECTURE.md#phase-4-development-roadmap) for detailed timelines.

## Getting Help

- **Issues**: Open a GitHub issue
- **Discussions**: Join GitHub Discussions
- **Documentation**: Check [docs/](./docs/)

## Contributing

We welcome contributions! See [CONTRIBUTING.md](./CONTRIBUTING.md) for guidelines.

---

**Happy building!** 🚀
