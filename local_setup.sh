#!/bin/bash
set -e

echo "🚀 Setting up OCP Platform for Local Development (No Docker)"
echo "============================================================"

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Check Python version
echo -e "${YELLOW}Checking Python version...${NC}"
PYTHON_VERSION=$(python3 --version | cut -d' ' -f2 | cut -d'.' -f1,2)
echo "Python version: $PYTHON_VERSION"

# Check if PostgreSQL is installed
echo -e "${YELLOW}Checking PostgreSQL...${NC}"
if command -v psql &> /dev/null; then
    echo -e "${GREEN}✓ PostgreSQL found${NC}"
else
    echo -e "${RED}✗ PostgreSQL not found. Please install: sudo apt-get install postgresql postgresql-contrib${NC}"
fi

# Check if Redis is installed
echo -e "${YELLOW}Checking Redis...${NC}"
if command -v redis-cli &> /dev/null; then
    echo -e "${GREEN}✓ Redis found${NC}"
else
    echo -e "${RED}✗ Redis not found. Please install: sudo apt-get install redis-server${NC}"
fi

# Check if Node.js is installed
echo -e "${YELLOW}Checking Node.js...${NC}"
if command -v node &> /dev/null; then
    NODE_VERSION=$(node --version)
    echo -e "${GREEN}✓ Node.js found: $NODE_VERSION${NC}"
else
    echo -e "${RED}✗ Node.js not found. Please install Node.js 18+${NC}"
fi

# Create .env file if it doesn't exist
if [ ! -f .env ]; then
    echo -e "${YELLOW}Creating .env file...${NC}"
    cp .env.example .env
    echo -e "${GREEN}✓ .env file created${NC}"
fi

# Setup virtual environments for each service
echo -e "${YELLOW}Setting up Python virtual environments...${NC}"

# Orchestrator
cd services/orchestrator
if [ ! -d "venv" ]; then
    python3 -m venv venv
    source venv/bin/activate
    pip install --upgrade pip
    pip install -r requirements.txt
    deactivate
    echo -e "${GREEN}✓ Orchestrator venv setup complete${NC}"
else
    echo -e "${GREEN}✓ Orchestrator venv already exists${NC}"
fi
cd ../..

# NLU Service
cd services/nlu-service
if [ ! -d "venv" ]; then
    python3 -m venv venv
    source venv/bin/activate
    pip install --upgrade pip
    pip install -r requirements.txt
    deactivate
    echo -e "${GREEN}✓ NLU Service venv setup complete${NC}"
else
    echo -e "${GREEN}✓ NLU Service venv already exists${NC}"
fi
cd ../..

# Chat Connector
cd services/chat-connector
if [ ! -d "venv" ]; then
    python3 -m venv venv
    source venv/bin/activate
    pip install --upgrade pip
    pip install -r requirements.txt
    deactivate
    echo -e "${GREEN}✓ Chat Connector venv setup complete${NC}"
else
    echo -e "${GREEN}✓ Chat Connector venv already exists${NC}"
fi
cd ../..

# Setup Frontend
echo -e "${YELLOW}Setting up frontend...${NC}"
cd frontend/chat-widget
if [ ! -d "node_modules" ]; then
    npm install
    echo -e "${GREEN}✓ Frontend dependencies installed${NC}"
else
    echo -e "${GREEN}✓ Frontend dependencies already installed${NC}"
fi
cd ../..

echo ""
echo -e "${GREEN}============================================================${NC}"
echo -e "${GREEN}✓ Setup complete!${NC}"
echo ""
echo -e "${YELLOW}Next steps:${NC}"
echo "1. Start PostgreSQL: sudo service postgresql start"
echo "2. Start Redis: sudo service redis-server start"
echo "3. Run: ./local_run.sh"
echo ""
