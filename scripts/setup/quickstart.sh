#!/bin/bash

# ============================================
# OCP Platform - Quick Start Script
# Phase 1: Development Environment Setup
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
echo "║     OCP Platform - Conversational AI Platform                 ║"
echo "║     Phase 1: Quick Start Setup                                ║"
echo "║                                                                ║"
echo "╚════════════════════════════════════════════════════════════════╝"
echo -e "${NC}"

# Check prerequisites
echo -e "${YELLOW}[1/6] Checking prerequisites...${NC}"

command -v docker >/dev/null 2>&1 || { echo -e "${RED}Error: Docker is not installed. Please install Docker first.${NC}"; exit 1; }
command -v docker-compose >/dev/null 2>&1 || { echo -e "${RED}Error: Docker Compose is not installed. Please install Docker Compose first.${NC}"; exit 1; }

echo -e "${GREEN}✓ Docker and Docker Compose are installed${NC}"

# Check Docker daemon
if ! docker info > /dev/null 2>&1; then
    echo -e "${RED}Error: Docker daemon is not running. Please start Docker.${NC}"
    exit 1
fi
echo -e "${GREEN}✓ Docker daemon is running${NC}"

# Create .env file if not exists
echo -e "\n${YELLOW}[2/6] Setting up environment variables...${NC}"

if [ ! -f .env ]; then
    echo -e "${BLUE}Creating .env file from .env.example...${NC}"
    cp .env.example .env

    # Generate random JWT secret
    JWT_SECRET=$(openssl rand -hex 32 2>/dev/null || head -c 32 /dev/urandom | base64)
    sed -i "s/your-secret-key-change-in-production/${JWT_SECRET}/" .env

    echo -e "${GREEN}✓ .env file created with generated secrets${NC}"
else
    echo -e "${GREEN}✓ .env file already exists${NC}"
fi

# Create necessary directories
echo -e "\n${YELLOW}[3/6] Creating necessary directories...${NC}"

mkdir -p logs
mkdir -p ml-models/nlu
mkdir -p ml-models/stt
mkdir -p ml-models/tts
mkdir -p audio-storage
mkdir -p tmp

echo -e "${GREEN}✓ Directories created${NC}"

# Start infrastructure services
echo -e "\n${YELLOW}[4/6] Starting infrastructure services (PostgreSQL & Redis)...${NC}"
echo -e "${BLUE}This may take a few minutes on first run...${NC}"

docker-compose up -d postgres redis adminer

# Wait for PostgreSQL to be ready
echo -e "${BLUE}Waiting for PostgreSQL to be ready...${NC}"
sleep 5

max_attempts=30
attempt=0

while ! docker-compose exec -T postgres pg_isready -U ocpuser -d ocplatform > /dev/null 2>&1; do
    attempt=$((attempt + 1))
    if [ $attempt -ge $max_attempts ]; then
        echo -e "${RED}Error: PostgreSQL failed to start within 60 seconds${NC}"
        exit 1
    fi
    echo -n "."
    sleep 2
done

echo -e "\n${GREEN}✓ PostgreSQL is ready${NC}"
echo -e "${GREEN}✓ Redis is ready${NC}"

# Verify database initialization
echo -e "\n${YELLOW}[5/6] Verifying database initialization...${NC}"

TABLES=$(docker-compose exec -T postgres psql -U ocpuser -d ocplatform -t -c "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = 'public';" | xargs)

if [ "$TABLES" -gt 0 ]; then
    echo -e "${GREEN}✓ Database initialized with $TABLES tables${NC}"
else
    echo -e "${RED}Error: Database initialization failed${NC}"
    exit 1
fi

# Display access information
echo -e "\n${YELLOW}[6/6] Setup complete!${NC}"
echo -e "${GREEN}"
echo "╔════════════════════════════════════════════════════════════════╗"
echo "║                    SETUP SUCCESSFUL!                           ║"
echo "╚════════════════════════════════════════════════════════════════╝"
echo -e "${NC}"

echo -e "${BLUE}Infrastructure Services:${NC}"
echo "  ✓ PostgreSQL:  localhost:5432"
echo "  ✓ Redis:       localhost:6379"
echo "  ✓ Adminer:     http://localhost:8080"
echo ""

echo -e "${BLUE}Database Credentials:${NC}"
echo "  Username: ocpuser"
echo "  Password: ocppassword"
echo "  Database: ocplatform"
echo ""

echo -e "${BLUE}Default Admin User:${NC}"
echo "  Username: admin"
echo "  Password: admin123"
echo -e "  ${RED}⚠ CHANGE THIS IN PRODUCTION!${NC}"
echo ""

echo -e "${YELLOW}Next Steps:${NC}"
echo "1. Review the architecture: ${GREEN}cat ARCHITECTURE.md${NC}"
echo "2. Start implementing Phase 1 services (Orchestrator, NLU, Chat Connector)"
echo "3. Or start all services: ${GREEN}docker-compose up -d${NC}"
echo ""

echo -e "${BLUE}Useful Commands:${NC}"
echo "  View logs:           ${GREEN}docker-compose logs -f${NC}"
echo "  Stop services:       ${GREEN}docker-compose down${NC}"
echo "  Restart services:    ${GREEN}docker-compose restart${NC}"
echo "  Access database:     ${GREEN}docker-compose exec postgres psql -U ocpuser -d ocplatform${NC}"
echo "  Access Redis CLI:    ${GREEN}docker-compose exec redis redis-cli${NC}"
echo ""

echo -e "${BLUE}Documentation:${NC}"
echo "  Architecture:  ARCHITECTURE.md"
echo "  README:        README.md"
echo "  API Docs:      http://localhost:8000/docs (when orchestrator is running)"
echo ""

echo -e "${GREEN}Happy building! 🚀${NC}"
