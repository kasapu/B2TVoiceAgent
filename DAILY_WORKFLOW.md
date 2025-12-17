# Daily Development Workflow Guide

This guide helps you start/stop the OCP Platform and maintain your development workflow.

---

## 🌅 **Starting Your Day (Resuming Work)**

### Option 1: Quick Start (Recommended)
```bash
cd /home/kranti/OCPplatform

# Start all services
docker compose up -d

# Wait 10 seconds for services to start
sleep 10

# Check status
docker compose ps

# View logs (optional)
docker compose logs -f
```

**Access Points After Startup:**
- Chat Widget: http://localhost:3000
- Orchestrator API: http://localhost:8000/docs
- NLU Service API: http://localhost:8001/docs
- Database Admin: http://localhost:8080

### Option 2: Start with Fresh Logs
```bash
cd /home/kranti/OCPplatform

# Start and follow logs
docker compose up -d && docker compose logs -f
```

Press `Ctrl+C` to exit logs (services keep running)

---

## ✅ **Verify Everything is Working**

```bash
# Check all services are running
docker compose ps

# Test orchestrator health
curl http://localhost:8000/health

# Test NLU service
curl http://localhost:8001/health

# Test chat connector
curl http://localhost:8004/health

# Test creating a session
curl -X POST http://localhost:8000/v1/conversations/start \
  -H "Content-Type: application/json" \
  -d '{"channel_type": "chat"}'
```

**Expected Results:**
- All services show "Up" status
- Health checks return `{"status":"healthy"}`
- Session creation returns a session_id

---

## 🌙 **Ending Your Day (Shutting Down)**

### Option 1: Stop Services (Keeps Data) ⭐ **RECOMMENDED**
```bash
cd /home/kranti/OCPplatform

# Stop all containers but keep data
docker compose stop

# Verify everything stopped
docker compose ps
```

**What This Does:**
- ✅ Stops all running containers
- ✅ Keeps all data (database, Redis, volumes)
- ✅ Frees up system resources
- ✅ Tomorrow: Just run `docker compose up -d` to resume

### Option 2: Full Shutdown with Cleanup
```bash
# Stop and remove containers (keeps volumes/data)
docker compose down

# Verify cleanup
docker compose ps
```

**What This Does:**
- ✅ Stops and removes containers
- ✅ Keeps data volumes intact
- ⚠️  Tomorrow: Containers will be recreated (takes longer to start)

### Option 3: Nuclear Option (Deletes Everything) ⚠️ **DANGEROUS**
```bash
# ONLY USE IF YOU WANT TO START FRESH
# This deletes ALL data including database!
docker compose down -v

# Verify complete removal
docker volume ls | grep ocpplatform
```

**⚠️ WARNING:** This deletes:
- All conversation history
- All training data
- All session data
- Database schema and data

---

## 💾 **Data Persistence**

Your data is stored in Docker volumes:

```bash
# List volumes
docker volume ls | grep ocpplatform

# Expected volumes:
# - ocpplatform_postgres_data  (all database data)
# - ocpplatform_redis_data     (session cache)
```

**Important:**
- Data persists between `docker compose stop` and `docker compose up`
- Data persists between `docker compose down` and `docker compose up`
- Data is DELETED only with `docker compose down -v`

---

## 🔧 **Common Daily Tasks**

### View Logs
```bash
# All services
docker compose logs -f

# Specific service
docker compose logs -f orchestrator
docker compose logs -f nlu-service
docker compose logs -f chat-connector

# Last 50 lines
docker compose logs --tail=50 orchestrator
```

### Restart a Service
```bash
# Restart single service
docker compose restart orchestrator

# Restart with rebuild (after code changes)
docker compose up -d --build orchestrator
```

### Access Database
```bash
# Using Adminer (Web UI)
# Open: http://localhost:8080
# Server: postgres
# Username: ocpuser
# Password: ocppassword
# Database: ocplatform

# Using psql (Command Line)
docker compose exec postgres psql -U ocpuser -d ocplatform

# Example queries:
# SELECT * FROM intents;
# SELECT * FROM sessions ORDER BY started_at DESC LIMIT 5;
# \q  (to exit)
```

### Access Redis
```bash
# Connect to Redis CLI
docker compose exec redis redis-cli

# Example commands:
# KEYS session:*
# GET session:YOUR_SESSION_ID
# TTL session:YOUR_SESSION_ID
# exit
```

### Check Resource Usage
```bash
# See CPU/Memory usage
docker stats

# See disk usage
docker system df
```

---

## 🐛 **Troubleshooting**

### Services Won't Start
```bash
# Check logs for errors
docker compose logs

# Try clean restart
docker compose down
docker compose up -d

# Check Docker is running
docker info
```

### Port Already in Use
```bash
# Find what's using the port
sudo lsof -i :8000  # Replace with your port

# Kill the process
sudo kill -9 <PID>

# Or stop all OCP containers
docker compose down
```

### Database Connection Issues
```bash
# Restart PostgreSQL
docker compose restart postgres

# Check PostgreSQL logs
docker compose logs postgres

# Verify database is accessible
docker compose exec postgres pg_isready -U ocpuser
```

### Out of Disk Space
```bash
# Clean up unused Docker resources
docker system prune -a

# Remove old volumes (WARNING: deletes data)
docker volume prune

# Check disk usage
df -h
docker system df
```

---

## 📝 **Development Workflow**

### Making Code Changes

1. **Edit code** in your favorite editor
   ```bash
   # Example: Edit orchestrator code
   code services/orchestrator/app/api/conversations.py
   ```

2. **Rebuild and restart** the service
   ```bash
   docker compose up -d --build orchestrator
   ```

3. **Check logs** for errors
   ```bash
   docker compose logs -f orchestrator
   ```

4. **Test** the changes
   ```bash
   # Test via web UI
   open http://localhost:3000

   # Or test via API
   curl http://localhost:8000/health
   ```

### Committing Changes
```bash
cd /home/kranti/OCPplatform

# Check what changed
git status

# Add specific files
git add services/orchestrator/app/api/conversations.py

# Commit with message
git commit -m "fix: your description here"

# Push to remote (if needed)
git push
```

---

## 📊 **Quick Reference**

| Task | Command |
|------|---------|
| Start everything | `docker compose up -d` |
| Stop everything | `docker compose stop` |
| Restart service | `docker compose restart orchestrator` |
| View logs | `docker compose logs -f` |
| Check status | `docker compose ps` |
| Rebuild service | `docker compose up -d --build orchestrator` |
| Access database | Open http://localhost:8080 |
| Test chatbot | Open http://localhost:3000 |
| Clean shutdown | `docker compose down` |

---

## 🎯 **Best Practices**

### Daily Routine

**Morning:**
1. `cd /home/kranti/OCPplatform`
2. `docker compose up -d`
3. Wait 10 seconds
4. Open http://localhost:3000 to verify

**During Development:**
1. Edit code
2. `docker compose up -d --build <service-name>`
3. Check logs: `docker compose logs -f <service-name>`
4. Test changes

**Evening:**
1. Commit your changes: `git add . && git commit -m "description"`
2. Stop services: `docker compose stop`
3. Optional: `docker system prune` to free space

### Data Backup (Important!)

```bash
# Backup database
docker compose exec -T postgres pg_dump -U ocpuser ocplatform > backup.sql

# Restore database
docker compose exec -T postgres psql -U ocpuser ocplatform < backup.sql
```

---

## 🚀 **Today's Status (2025-12-05)**

**Current State:**
- ✅ All Phase 1 services implemented
- ✅ Chat widget functional
- ✅ NLU trained with 7 intents
- ✅ Database initialized with training data
- ✅ Docker Compose setup complete

**Known Issues:**
- ⚠️ Orchestrator shows "unhealthy" in health check (but works fine)
- ⚠️ Chat-connector shows "unhealthy" in health check (but works fine)

**Fixed Today:**
- ✅ Docker Compose v2 compatibility
- ✅ SpaCy model download
- ✅ SQLAlchemy text() imports
- ✅ PostgreSQL JSONB serialization

**Next Steps:**
- Continue with Phase 2 (Advanced NLU + Visual Flow Designer)
- Add more training data for better accuracy
- Fix health check issues

---

## 📞 **Need Help?**

- Check logs: `docker compose logs`
- View documentation: `cat PHASE1_TESTING_GUIDE.md`
- Test guide: `cat PHASE1_TESTING_GUIDE.md`
- Architecture: `cat ARCHITECTURE.md`

---

**Happy Coding! 🎉**
