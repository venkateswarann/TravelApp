#!/bin/bash
# Travel App Launcher

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${BLUE}╔════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║         🌍  Travel Planner App - Launcher             ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════════════════════╝${NC}"
echo ""

# Check if Python is available
if ! command -v python3 &> /dev/null; then
    echo -e "${YELLOW}⚠️  Python 3 not found! Please install Python 3.8+${NC}"
    exit 1
fi

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo -e "${GREEN}📦 Creating virtual environment...${NC}"
    python3 -m venv venv
fi

# Activate virtual environment
echo -e "${GREEN}🔨 Activating virtual environment...${NC}"
source venv/bin/activate

# Install requirements if needed
if [ ! -f "venv/installed.flag" ]; then
    echo -e "${GREEN}📦 Installing dependencies...${NC}"
    pip install -r requirements.txt
    touch venv/installed.flag
fi

# Initialize database if needed
echo -e "${GREEN}💾 Initializing database...${NC}"
python3 -c "
import sys
sys.path.insert(0, '.')
from app import init_db
init_db()
print('✅ Database initialized!')
"

# Get device info
echo ""
echo -e "${BLUE}══════════════════════════════════════════════════════════${NC}"
echo -e "${BLUE}                📱 Access Information${NC}"
echo -e "${BLUE}══════════════════════════════════════════════════════════${NC}"
echo ""

# Check if tailscale is running
if command -v tailscale &> /dev/null && systemctl is-active --quiet tailscaled; then
    TS_IP=$(tailscale ip | head -n1)
    TS_HOSTNAME=$(hostname)
    echo -e "${GREEN}✅ Tailscale is active!${NC}"
    echo -e "${YELLOW}Access via:${NC}"
    echo -e "${GREEN}  → http://localhost:5001${NC}"
    echo -e "${GREEN}  → http://${TS_IP}:5001${NC}"
    echo -e "${GREEN}  → http://${TS_HOSTNAME}:5001${NC}"
    echo -e "${GREEN}  → http://${TS_HOSTNAME}.local:5001${NC}"
else
    echo -e "${YELLOW}⚠️  Tailscale not detected${NC}"
    echo -e "${GREEN}Access locally at: http://localhost:5001${NC}"
fi

echo ""
echo -e "${BLUE}══════════════════════════════════════════════════════════${NC}"
echo -e "${BLUE}                   🚀 Starting App${NC}"
echo -e "${BLUE}══════════════════════════════════════════════════════════${NC}"
echo ""

# Run the app
echo -e "${GREEN}Starting Flask server...${NC}"
python3 app.py

# Deactivate virtual environment when done
deactivate
EOF
chmod +x /home/pandora/travel-app/run.sh