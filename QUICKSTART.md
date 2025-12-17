# 🚀 Quick Start - OCP Platform

## Start Everything (One Command!)

```bash
./scripts/start.sh
```

That's it! The script will:
- ✅ Check Docker is running
- ✅ Create .env file
- ✅ Start PostgreSQL & Redis
- ✅ Build all services
- ✅ Start all services
- ✅ Wait for NLU model training
- ✅ Show you all access URLs

**First startup takes 2-3 minutes** (building Docker images + training AI model)

---

## Access Your Chatbot

Once the script completes, open your browser:

👉 **http://localhost:3000**

Start chatting with your AI assistant!

---

## Try These Conversations

### Example 1: Balance Check
```
You: Hello
Bot: Hello! I'm your banking assistant. How can I help you today?
You: Check my balance
Bot: Your current account balance is $1,234.56...
```

### Example 2: Transfer Money
```
You: I want to transfer money
Bot: How much would you like to transfer?
You: $500
Bot: Transfer of $500 initiated successfully!
```

### Example 3: Get Help
```
You: What can you do?
Bot: I can help you check your balance or transfer money...
```

---

## Other Useful Links

- **API Documentation**: http://localhost:8000/docs
- **NLU API**: http://localhost:8001/docs
- **Database Admin**: http://localhost:8080
  - Login: `ocpuser` / `ocppassword` / `ocplatform`

---

## View Logs

```bash
# All services
docker-compose logs -f

# Specific service
docker-compose logs -f orchestrator
docker-compose logs -f nlu-service
```

---

## Stop Services

```bash
docker-compose down
```

---

## Troubleshooting

### Services won't start?

```bash
# Check Docker is running
docker info

# View logs for errors
docker-compose logs

# Try restarting
docker-compose down
./scripts/start.sh
```

### Chat widget shows "Connecting..."?

Wait 30 seconds for services to fully start. Check logs:

```bash
docker-compose logs chat-connector
docker-compose logs orchestrator
```

### Need help?

See the comprehensive guide: [PHASE1_TESTING_GUIDE.md](./PHASE1_TESTING_GUIDE.md)

---

## What's Included?

- ✅ **4 Microservices** (Orchestrator, NLU, Chat Connector, Chat Widget)
- ✅ **Real-time Chat** via WebSocket
- ✅ **AI Intent Detection** using spaCy
- ✅ **7 Intents**: greet, goodbye, check_balance, transfer_money, help, cancel, out_of_scope
- ✅ **Session Management** with Redis
- ✅ **Conversation Logging** to PostgreSQL
- ✅ **Auto-generated API Docs**

---

## Architecture

```
User Browser (Port 3000)
    ↓ WebSocket
Chat Connector (Port 8004)
    ↓ HTTP
Orchestrator (Port 8000)
    ↓ HTTP
NLU Service (Port 8001)
    ↓
spaCy AI Model
```

Data stored in:
- **PostgreSQL** (conversations, flows, training data)
- **Redis** (session state, 30min TTL)

---

**Happy chatting! 🤖💬**
