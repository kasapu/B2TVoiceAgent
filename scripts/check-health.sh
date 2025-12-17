#!/bin/bash

# ============================================
# OCP Platform - Health Check Script
# Verifies all services are running correctly
# ============================================

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}OCP Platform - Health Check${NC}"
echo "================================"
echo ""

# Check Docker containers
echo -e "${YELLOW}Docker Containers:${NC}"
docker-compose ps --format "table {{.Name}}\t{{.Status}}\t{{.Ports}}" 2>/dev/null

echo ""
echo -e "${YELLOW}Service Health Checks:${NC}"

# Function to check health
check_health() {
    local name=$1
    local url=$2

    echo -n "  $name: "

    response=$(curl -s -o /dev/null -w "%{http_code}" "$url" 2>/dev/null)

    if [ "$response" = "200" ]; then
        echo -e "${GREEN}✓ Healthy${NC}"
        return 0
    else
        echo -e "${RED}✗ Unhealthy (HTTP $response)${NC}"
        return 1
    fi
}

# Check each service
check_health "PostgreSQL     " "http://localhost:8080" # Adminer proxy
check_health "Orchestrator   " "http://localhost:8000/health"
check_health "NLU Service    " "http://localhost:8001/health"
check_health "Chat Connector " "http://localhost:8004/health"
check_health "Chat Widget    " "http://localhost:3000"

echo ""
echo -e "${YELLOW}Database Connection:${NC}"
echo -n "  PostgreSQL: "
if docker-compose exec -T postgres pg_isready -U ocpuser -d ocplatform > /dev/null 2>&1; then
    echo -e "${GREEN}✓ Connected${NC}"
else
    echo -e "${RED}✗ Not connected${NC}"
fi

echo -n "  Redis:      "
if docker-compose exec -T redis redis-cli ping > /dev/null 2>&1; then
    echo -e "${GREEN}✓ Connected${NC}"
else
    echo -e "${RED}✗ Not connected${NC}"
fi

echo ""
echo -e "${YELLOW}NLU Model Status:${NC}"
if docker-compose logs nlu-service 2>&1 | grep -q "trained successfully\|Model loaded successfully"; then
    echo -e "  ${GREEN}✓ Model trained and loaded${NC}"
else
    echo -e "  ${YELLOW}⏳ Model still training or not loaded${NC}"
fi

echo ""
echo -e "${YELLOW}Active Sessions:${NC}"
session_count=$(docker-compose exec -T redis redis-cli KEYS "session:*" 2>/dev/null | wc -l)
echo "  $session_count active session(s)"

echo ""
echo -e "${YELLOW}Recent Conversations:${NC}"
conv_count=$(docker-compose exec -T postgres psql -U ocpuser -d ocplatform -t -c "SELECT COUNT(*) FROM sessions;" 2>/dev/null | xargs)
echo "  $conv_count total conversation(s) in database"

echo ""
echo -e "${BLUE}================================${NC}"

# Overall status
if [ $? -eq 0 ]; then
    echo -e "${GREEN}✓ Platform is healthy!${NC}"
    echo ""
    echo "Start chatting at: ${GREEN}http://localhost:3000${NC}"
else
    echo -e "${YELLOW}⚠ Some services may not be ready yet${NC}"
    echo ""
    echo "Check logs with: ${BLUE}docker-compose logs -f${NC}"
fi

echo ""
