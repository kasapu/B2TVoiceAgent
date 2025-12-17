# Phase 1 Testing Guide - Text-Based Chatbot

This guide will help you test the Phase 1 implementation of the OCP Platform.

## What's Implemented

✅ **Orchestrator Service** (Port 8000)
- Session management
- Dialogue flow execution
- Integration with NLU service
- PostgreSQL conversation logging
- Redis session state

✅ **NLU Service** (Port 8001)
- Basic intent classification using spaCy
- Rule-based fallback
- Entity extraction (amounts, account types)
- Simple sentiment analysis

✅ **Chat Connector** (Port 8004)
- WebSocket real-time messaging
- Connection management
- Integration with Orchestrator

✅ **Chat Widget** (Port 3000)
- Modern web interface
- Real-time messaging
- Connection status indicators
- Typing indicators

## Prerequisites

Before testing, make sure you have:
- Docker and Docker Compose installed
- All services running
- Database initialized with seed data

## Quick Start

### 1. Start All Services

```bash
# Start infrastructure (PostgreSQL, Redis)
./scripts/setup/quickstart.sh

# Start all application services
docker-compose up -d

# Check service status
docker-compose ps
```

Expected output:
```
NAME                STATUS              PORTS
ocp-postgres        running             0.0.0.0:5432->5432/tcp
ocp-redis           running             0.0.0.0:6379->6379/tcp
ocp-orchestrator    running             0.0.0.0:8000->8000/tcp
ocp-nlu             running             0.0.0.0:8001->8001/tcp
ocp-chat-connector  running             0.0.0.0:8004->8004/tcp
ocp-chat-widget     running             0.0.0.0:3000->3000/tcp
```

### 2. Verify Services are Healthy

```bash
# Check Orchestrator
curl http://localhost:8000/health

# Check NLU Service
curl http://localhost:8001/health

# Check Chat Connector
curl http://localhost:8004/health
```

All should return `{"status": "healthy"}`.

## Test Scenarios

### Test 1: Web Chat Interface (End-to-End)

**Objective**: Test the complete conversation flow through the web UI.

**Steps**:

1. Open your browser and go to: **http://localhost:3000**

2. Wait for "Connected" status to appear (green banner)

3. Try the following conversation:

   ```
   User: Hello
   Bot: Hello! I'm your banking assistant. How can I help you today?

   User: I want to check my balance
   Bot: Your current account balance is $1,234.56. Is there anything else I can help you with?

   User: Thanks, bye
   Bot: Thank you for banking with us. Have a great day!
   ```

4. Check that:
   - Messages appear instantly
   - Bot responses are relevant
   - Intent detection is shown (hover/meta info)
   - Connection remains stable

**Expected Results**:
- ✅ Conversation flows naturally
- ✅ Intents detected correctly
- ✅ No errors in browser console (F12)

---

### Test 2: API Testing with curl

**Objective**: Test the Orchestrator API directly.

#### 2.1 Create a Session

```bash
curl -X POST http://localhost:8000/v1/conversations/start \
  -H "Content-Type: application/json" \
  -d '{
    "channel_type": "chat"
  }' | jq
```

**Expected Response**:
```json
{
  "session_id": "123e4567-e89b-12d3-a456-426614174000",
  "channel_type": "chat",
  "started_at": "2025-01-20T10:30:00Z",
  "initial_message": "Hello! I'm your banking assistant..."
}
```

**Save the `session_id` for next steps!**

#### 2.2 Process User Input

```bash
# Replace SESSION_ID with the actual ID from step 2.1
SESSION_ID="123e4567-e89b-12d3-a456-426614174000"

curl -X POST "http://localhost:8000/v1/conversations/$SESSION_ID/process" \
  -H "Content-Type: application/json" \
  -d '{
    "input_type": "text",
    "text": "I want to check my balance"
  }' | jq
```

**Expected Response**:
```json
{
  "session_id": "123e4567-e89b-12d3-a456-426614174000",
  "turn_number": 1,
  "nlu": {
    "intent": {
      "name": "check_balance",
      "confidence": 0.92
    },
    "entities": [],
    "sentiment": {
      "label": "neutral",
      "score": 0.5
    }
  },
  "response": {
    "type": "text",
    "text": "Your current account balance is $1,234.56..."
  },
  "next_action": {
    "action_type": "continue"
  },
  "processing_time_ms": 150
}
```

#### 2.3 End the Session

```bash
curl -X POST "http://localhost:8000/v1/conversations/$SESSION_ID/end" \
  -H "Content-Type: application/json" \
  -d '{
    "reason": "completed"
  }' | jq
```

**Expected Response**:
```json
{
  "session_id": "123e4567-e89b-12d3-a456-426614174000",
  "duration_seconds": 45,
  "turn_count": 3,
  "summary": {
    "reason": "completed",
    "turns": 3,
    "duration": 45
  }
}
```

---

### Test 3: NLU Service Testing

**Objective**: Test intent classification directly.

```bash
curl -X POST http://localhost:8001/parse \
  -H "Content-Type: application/json" \
  -d '{
    "text": "I want to transfer $500 to my savings account",
    "language": "en-US"
  }' | jq
```

**Expected Response**:
```json
{
  "intent": {
    "name": "transfer_money",
    "confidence": 0.75
  },
  "entities": [
    {
      "entity_type": "amount",
      "value": "500",
      "confidence": 0.9,
      "start_char": 17,
      "end_char": 21
    },
    {
      "entity_type": "account_type",
      "value": "savings",
      "confidence": 0.85,
      "start_char": 28,
      "end_char": 35
    }
  ],
  "sentiment": {
    "label": "neutral",
    "score": 0.5
  }
}
```

**Try different intents**:
```bash
# Greeting
curl -X POST http://localhost:8001/parse -H "Content-Type: application/json" \
  -d '{"text": "Hello there"}' | jq '.intent'

# Goodbye
curl -X POST http://localhost:8001/parse -H "Content-Type: application/json" \
  -d '{"text": "bye"}' | jq '.intent'

# Help
curl -X POST http://localhost:8001/parse -H "Content-Type: application/json" \
  -d '{"text": "I need help"}' | jq '.intent'
```

---

### Test 4: Database Verification

**Objective**: Verify that conversations are logged correctly.

```bash
# Connect to PostgreSQL
docker-compose exec postgres psql -U ocpuser -d ocplatform
```

#### Check Sessions

```sql
-- View all sessions
SELECT session_id, channel_type, started_at, current_state
FROM sessions
ORDER BY started_at DESC
LIMIT 5;
```

#### Check Conversation Turns

```sql
-- View conversation turns for a session (replace with actual session_id)
SELECT turn_number, speaker, user_input_text, detected_intent, bot_response_text
FROM conversation_turns
WHERE session_id = 'YOUR_SESSION_ID'
ORDER BY turn_number;
```

#### Check Intent Statistics

```sql
-- View intent distribution
SELECT detected_intent, COUNT(*) as count, AVG(intent_confidence) as avg_confidence
FROM conversation_turns
WHERE detected_intent IS NOT NULL
GROUP BY detected_intent
ORDER BY count DESC;
```

Exit psql:
```sql
\q
```

---

### Test 5: Redis Session State

**Objective**: Verify session state is stored in Redis.

```bash
# Connect to Redis
docker-compose exec redis redis-cli

# List all session keys
KEYS session:*

# Get session data (replace with actual session_id)
GET session:YOUR_SESSION_ID

# Check TTL (should be ~1800 seconds = 30 minutes)
TTL session:YOUR_SESSION_ID

# Exit
exit
```

---

### Test 6: Dialogue Flow Testing

**Objective**: Test all dialogue flow paths.

Use the web interface (http://localhost:3000) and try these conversations:

#### Flow 1: Greeting and Help
```
User: Hi
Bot: Hello! I'm your banking assistant. How can I help you today?
User: What can you do?
Bot: I can help you check your balance or transfer money...
```

#### Flow 2: Balance Check
```
User: Hello
Bot: Hello! I'm your banking assistant...
User: Check my balance
Bot: Your current account balance is $1,234.56...
```

#### Flow 3: Transfer (Slot Filling)
```
User: I want to transfer money
Bot: How much would you like to transfer?
User: $500
Bot: Transfer of $500 initiated successfully!
```

#### Flow 4: Cancel
```
User: I want to check my balance
Bot: Your current account balance is...
User: cancel
Bot: Hello! I'm your banking assistant... (back to start)
```

#### Flow 5: Out of Scope
```
User: What's the weather?
Bot: I'm sorry, I didn't understand that...
```

---

### Test 7: Load Testing (Optional)

**Objective**: Test concurrent connections.

```bash
# Install Apache Bench if not already installed
# sudo apt-get install apache2-utils

# Test Orchestrator endpoint
ab -n 100 -c 10 -p data.json -T application/json \
  http://localhost:8000/v1/conversations/start
```

Where `data.json` contains:
```json
{"channel_type": "chat"}
```

**Expected**: All requests should succeed (200/201 status codes).

---

### Test 8: Error Handling

**Objective**: Test error scenarios.

#### Test Invalid Session
```bash
curl -X POST "http://localhost:8000/v1/conversations/00000000-0000-0000-0000-000000000000/process" \
  -H "Content-Type: application/json" \
  -d '{"input_type": "text", "text": "hello"}' | jq
```

**Expected**: 404 error with message "Session not found or expired"

#### Test Empty Message
```bash
curl -X POST http://localhost:8001/parse \
  -H "Content-Type: application/json" \
  -d '{"text": ""}' | jq
```

**Expected**: Should handle gracefully

---

## Monitoring & Debugging

### View Service Logs

```bash
# View all logs
docker-compose logs -f

# View specific service logs
docker-compose logs -f orchestrator
docker-compose logs -f nlu-service
docker-compose logs -f chat-connector
```

### Check Service Health

```bash
# Orchestrator
curl http://localhost:8000/health | jq

# NLU
curl http://localhost:8001/health | jq

# Chat Connector
curl http://localhost:8004/health | jq
```

### API Documentation

Open in browser:
- **Orchestrator API**: http://localhost:8000/docs
- **NLU API**: http://localhost:8001/docs

---

## Common Issues & Solutions

### Issue: Services won't start

**Solution**:
```bash
# Check logs
docker-compose logs

# Restart services
docker-compose restart

# Clean restart
docker-compose down
docker-compose up -d
```

### Issue: Database connection error

**Solution**:
```bash
# Check PostgreSQL is running
docker-compose ps postgres

# Test connection
docker-compose exec postgres pg_isready -U ocpuser

# Restart PostgreSQL
docker-compose restart postgres
```

### Issue: NLU model not loaded

**Solution**:
```bash
# Check NLU logs
docker-compose logs nlu-service

# The first startup will train a model, this may take 1-2 minutes
# Wait for: "Model trained successfully"
```

### Issue: WebSocket won't connect

**Solution**:
```bash
# Check chat-connector is running
docker-compose ps chat-connector

# Check browser console for errors (F12)
# Ensure you're using http://localhost:3000 (not 127.0.0.1)
```

### Issue: Chat widget shows "Connecting..." forever

**Solution**:
1. Check that chat-connector is running: `docker-compose logs chat-connector`
2. Verify orchestrator is accessible: `curl http://localhost:8000/health`
3. Check browser console (F12) for WebSocket errors
4. Try hard refresh: Ctrl+Shift+R

---

## Performance Metrics

After testing, check these metrics:

### Response Times
- **Session creation**: < 100ms
- **Intent classification**: < 200ms
- **End-to-end turn**: < 500ms

### Accuracy
- **Intent accuracy**: > 80% (on seed data)
- **Entity extraction**: Basic patterns working

### Reliability
- **WebSocket stability**: Stays connected for > 5 minutes
- **Database writes**: 100% success rate
- **Redis TTL**: Session expires after 30 minutes

---

## Success Criteria

Phase 1 is successful if:

- [x] User can chat via web interface
- [x] Bot recognizes 7 intents (greet, goodbye, check_balance, transfer_money, help, cancel, out_of_scope)
- [x] Dialogue flows work correctly
- [x] Sessions persist across messages
- [x] Conversations logged to database
- [x] Intent confidence displayed
- [x] No crashes or errors during normal use
- [x] Services restart gracefully

---

## Next Steps

After successful Phase 1 testing:

1. **Phase 2**: Implement visual flow designer
2. **Phase 2**: Upgrade NLU to transformer models (RoBERTa)
3. **Phase 2**: Add external API integrations
4. **Phase 3**: Implement voice capabilities

---

## Useful Commands

```bash
# View all containers
docker-compose ps

# Restart a service
docker-compose restart orchestrator

# View logs
docker-compose logs -f nlu-service

# Execute command in container
docker-compose exec postgres psql -U ocpuser -d ocplatform

# Stop all services
docker-compose down

# Remove all data (WARNING: deletes database!)
docker-compose down -v

# Rebuild a service
docker-compose build orchestrator
docker-compose up -d orchestrator
```

---

## Report Issues

If you encounter issues not covered here:

1. Check service logs: `docker-compose logs -f`
2. Verify prerequisites are met
3. Try clean restart: `docker-compose down && docker-compose up -d`
4. Open a GitHub issue with logs

---

**Happy Testing! 🚀**
