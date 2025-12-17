#!/bin/bash

# ============================================
# OCP Platform - Complete Startup Script
# Builds and starts all services
# ============================================

set -e  # Exit on error

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${BLUE}"
echo "╔════════════════════════════════════════════════════════════════╗"
echo "║                                                                ║"
echo "║     OCP Platform - Complete Startup                           ║"
echo "║     Building and Starting All Services                        ║"
echo "║                                                                ║"
echo "╚════════════════════════════════════════════════════════════════╝"
echo -e "${NC}"

# Check Docker is running
echo -e "${YELLOW}[1/8] Checking Docker...${NC}"
if ! docker info > /dev/null 2>&1; then
    echo -e "${RED}Error: Docker is not running. Please start Docker.${NC}"
    exit 1
fi
echo -e "${GREEN}✓ Docker is running${NC}"

# Check if .env exists
echo -e "\n${YELLOW}[2/8] Checking environment variables...${NC}"
if [ ! -f .env ]; then
    echo -e "${BLUE}Creating .env file from .env.example...${NC}"
    cp .env.example .env
    echo -e "${GREEN}✓ .env file created${NC}"
else
    echo -e "${GREEN}✓ .env file exists${NC}"
fi

# Create necessary directories
echo -e "\n${YELLOW}[3/8] Creating directories...${NC}"
mkdir -p logs ml-models/nlu ml-models/stt ml-models/tts audio-storage tmp
echo -e "${GREEN}✓ Directories created${NC}"

# Stop any existing containers
echo -e "\n${YELLOW}[4/8] Stopping existing containers...${NC}"
docker compose down 2>/dev/null || true
echo -e "${GREEN}✓ Old containers stopped${NC}"

# Start infrastructure services first
echo -e "\n${YELLOW}[5/8] Starting infrastructure (PostgreSQL & Redis)...${NC}"
docker compose up -d postgres redis adminer

# Wait for PostgreSQL to be ready
echo -e "${BLUE}Waiting for PostgreSQL to be ready...${NC}"
max_attempts=30
attempt=0

while ! docker compose exec -T postgres pg_isready -U ocpuser -d ocplatform > /dev/null 2>&1; do
    attempt=$((attempt + 1))
    if [ $attempt -ge $max_attempts ]; then
        echo -e "${RED}Error: PostgreSQL failed to start within 60 seconds${NC}"
        docker compose logs postgres
        exit 1
    fi
    echo -n "."
    sleep 2
done

echo -e "\n${GREEN}✓ PostgreSQL is ready${NC}"
echo -e "${GREEN}✓ Redis is ready${NC}"

# Build all services
echo -e "\n${YELLOW}[6/8] Building application services...${NC}"
echo -e "${BLUE}This may take 2-3 minutes on first run...${NC}"
docker-compose build orchestrator nlu-service chat-connector chat-widget
echo -e "${GREEN}✓ Services built successfully${NC}"

# Start all application services
echo -e "\n${YELLOW}[7/8] Starting application services...${NC}"
docker-compose up -d

echo -e "${BLUE}Waiting for services to start...${NC}"
sleep 5

# Wait for NLU model to train
echo -e "\n${YELLOW}[8/8] Waiting for NLU model training...${NC}"
echo -e "${BLUE}This may take 30-60 seconds on first startup...${NC}"

max_wait=60
waited=0
while [ $waited -lt $max_wait ]; do
    if docker-compose logs nlu-service 2>&1 | grep -q "trained successfully\|Model loaded successfully\|NLU Service started"; then
        echo -e "\n${GREEN}✓ NLU service is ready${NC}"
        break
    fi
    echo -n "."
    sleep 2
    waited=$((waited + 2))
done

if [ $waited -ge $max_wait ]; then
    echo -e "\n${YELLOW}⚠ NLU training is taking longer than expected${NC}"
    echo -e "${YELLOW}This is normal on first startup. Check logs: docker-compose logs -f nlu-service${NC}"
fi

# Display status
echo -e "\n${YELLOW}Checking service status...${NC}"
sleep 2
docker-compose ps

# Display success message
echo -e "\n${GREEN}"
echo "╔════════════════════════════════════════════════════════════════╗"
echo "║                    ALL SERVICES RUNNING!                       ║"
echo "╚════════════════════════════════════════════════════════════════╝"
echo -e "${NC}"

echo -e "${BLUE}🌐 Access Points:${NC}"
echo "  • Chat Widget:    ${GREEN}http://localhost:3000${NC}  ← Start here!"
echo "  • API Docs:       ${GREEN}http://localhost:8000/docs${NC}"
echo "  • NLU Docs:       ${GREEN}http://localhost:8001/docs${NC}"
echo "  • Database UI:    ${GREEN}http://localhost:8080${NC}"
echo ""

echo -e "${BLUE}🔧 Useful Commands:${NC}"
echo "  • View logs:      ${GREEN}docker-compose logs -f${NC}"
echo "  • Stop services:  ${GREEN}docker-compose down${NC}"
echo "  • Restart:        ${GREEN}docker-compose restart${NC}"
echo ""

echo -e "${BLUE}📊 Service Health:${NC}"
echo -n "  • Orchestrator:   "
if curl -s http://localhost:8000/health > /dev/null 2>&1; then
    echo -e "${GREEN}✓ Healthy${NC}"
else
    echo -e "${YELLOW}⏳ Starting...${NC}"
fi

echo -n "  • NLU Service:    "
if curl -s http://localhost:8001/health > /dev/null 2>&1; then
    echo -e "${GREEN}✓ Healthy${NC}"
else
    echo -e "${YELLOW}⏳ Starting...${NC}"
fi

echo -n "  • Chat Connector: "
if curl -s http://localhost:8004/health > /dev/null 2>&1; then
    echo -e "${GREEN}✓ Healthy${NC}"
else
    echo -e "${YELLOW}⏳ Starting...${NC}"
fi

echo ""
echo -e "${GREEN}🚀 Platform is ready! Open http://localhost:3000 and start chatting!${NC}"
echo ""
echo -e "${BLUE}💡 Tip: Run 'docker-compose logs -f' to watch service logs${NC}"
echo ""
