#!/bin/bash

# Database Setup Script for Trender
# This script initializes the PostgreSQL database schema

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo "🚀 Trender Database Setup"
echo "=========================="
echo ""

# Get the directory where the script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$( cd "$SCRIPT_DIR/.." && pwd )"

# Load environment variables from .env file if it exists
ENV_FILE="$PROJECT_ROOT/.env"
if [ -f "$ENV_FILE" ]; then
    echo "📄 Loading environment variables from .env file..."
    # Export variables from .env file (ignoring comments and empty lines)
    export $(grep -v '^#' "$ENV_FILE" | grep -v '^[[:space:]]*$' | xargs)
    echo -e "${GREEN}✓ Environment variables loaded${NC}"
    echo ""
fi

# Check if DATABASE_URL is set
if [ -z "$DATABASE_URL" ]; then
    echo -e "${RED}Error: DATABASE_URL environment variable is not set${NC}"
    echo ""
    echo "Please either:"
    echo "  1. Create a .env file with DATABASE_URL (see env.example)"
    echo "  2. Export DATABASE_URL: export DATABASE_URL=your_database_url"
    echo "  3. Run with the variable: DATABASE_URL=your_database_url ./bin/db_setup.sh"
    exit 1
fi

# Get the directory where the script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$( cd "$SCRIPT_DIR/.." && pwd )"

echo "📁 Project root: $PROJECT_ROOT"
echo ""

# Check if init.sql exists
INIT_SQL="$PROJECT_ROOT/database/init.sql"
if [ ! -f "$INIT_SQL" ]; then
    echo -e "${RED}Error: database/init.sql not found${NC}"
    exit 1
fi

echo "🔍 Checking database connection..."
if ! psql "$DATABASE_URL" -c "SELECT 1;" > /dev/null 2>&1; then
    echo -e "${RED}Error: Could not connect to database${NC}"
    echo "Please check your DATABASE_URL"
    exit 1
fi
echo -e "${GREEN}✓ Database connection successful${NC}"
echo ""

echo "📊 Initializing database schema..."
echo "Running: database/init.sql"
echo ""

if psql "$DATABASE_URL" -f "$INIT_SQL"; then
    echo ""
    echo -e "${GREEN}✅ Database setup completed successfully!${NC}"
    echo ""
    echo "The following layers have been initialized:"
    echo "  • Raw Layer (staging tables for API data)"
    echo "  • Staging Layer (cleaned and validated data)"
    echo "  • Analytics Layer (aggregated metrics)"
    echo "  • Views (user-facing data views)"
    echo ""
else
    echo ""
    echo -e "${RED}❌ Database setup failed${NC}"
    exit 1
fi

