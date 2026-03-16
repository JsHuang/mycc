#!/bin/bash
# MyCC Backend One-Click Startup Script
# Run: ./start-mycc.sh

set -e

# Configuration
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SCRIPT_DIR="$PROJECT_DIR/.claude/skills/mycc/scripts"
LOG_FILE="$PROJECT_DIR/.claude/skills/mycc/backend.log"
CONFIG_FILE="$PROJECT_DIR/.claude/skills/mycc/current.json"
ENV_FILE="$PROJECT_DIR/.env"
TSX_BIN="$SCRIPT_DIR/node_modules/.bin/tsx"

# Load .env file if exists
if [ -f "$ENV_FILE" ]; then
    export $(grep -v '^#' "$ENV_FILE" | xargs)
fi

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
GRAY='\033[0;37m'
WHITE='\033[1;37m'
NC='\033[0m' # No Color

clear

echo ""
echo -e "${CYAN}============================================${NC}"
echo -e "${CYAN}       MyCC Backend v0.5.1${NC}"
echo -e "${CYAN}       + 飞书通道 (Feishu)${NC}"
echo -e "${CYAN}============================================${NC}"
echo ""

# Check dependencies
echo -e "${YELLOW}[1/5] Checking dependencies...${NC}"

if [ ! -f "$TSX_BIN" ]; then
    echo -e "  ${RED}ERROR: tsx not found!${NC}"
    echo -e "  ${GRAY}Run: cd $SCRIPT_DIR && npm install${NC}"
    echo ""
    read -p "Press Enter to exit"
    exit 1
fi
echo -e "  ${GREEN}tsx: OK${NC}"

if command -v claude &> /dev/null; then
    echo -e "  ${GREEN}Claude Code: OK${NC}"
else
    echo -e "  ${YELLOW}WARNING: Claude Code CLI not found in PATH${NC}"
fi

# Feishu configuration
if [ -n "$FEISHU_APP_ID" ]; then
    echo -e "  ${GRAY}Feishu App ID: $FEISHU_APP_ID${NC}"
fi
if [ -n "$FEISHU_RECEIVE_USER_ID" ]; then
    echo -e "  ${GRAY}Feishu Group ID: $FEISHU_RECEIVE_USER_ID${NC}"
fi

echo ""

# Check and stop existing process
echo -e "${YELLOW}[2/5] Checking port 18080...${NC}"
if lsof -Pi :18080 -sTCP:LISTEN -t >/dev/null 2>&1; then
    PID=$(lsof -Pi :18080 -sTCP:LISTEN -t)
    echo -e "  ${RED}Port occupied (PID: $PID), stopping...${NC}"
    kill -9 "$PID" 2>/dev/null || true
    sleep 2
fi
echo -e "  ${GREEN}Port 18080 available${NC}"
echo ""

# Start backend
echo -e "${YELLOW}[3/5] Starting backend...${NC}"

# Clear old log
[ -f "$LOG_FILE" ] && rm -f "$LOG_FILE"

# Start in background using nohup
nohup "$TSX_BIN" "$SCRIPT_DIR/src/index.ts" start >> "$LOG_FILE" 2>&1 &
BACKEND_PID=$!

# Wait for process to start
sleep 3

# Check if port 18080 is now listening
if lsof -Pi :18080 -sTCP:LISTEN -t >/dev/null 2>&1; then
    NEW_PID=$(lsof -Pi :18080 -sTCP:LISTEN -t)
    echo -e "  ${GREEN}Backend started (PID: $NEW_PID)${NC}"
else
    echo -e "  ${YELLOW}WARNING: Port 18080 not listening yet${NC}"
fi

echo ""

# Wait for service ready
echo -e "${YELLOW}[4/5] Waiting for service ready...${NC}"
timeout=30
elapsed=0
while [ $elapsed -lt $timeout ]; do
    # Check if backend process is running
    if kill -0 $BACKEND_PID 2>/dev/null; then
        # Check if Feishu WebSocket is connected (simple check)
        if [ -f "$LOG_FILE" ] && grep -q "Feishu WebSocket connected" "$LOG_FILE" 2>/dev/null; then
            break
        fi
    else
        echo ""
        echo -e "  ${RED}ERROR: Backend process died!${NC}"
        echo -e "  ${GRAY}Check log: tail -50 '$LOG_FILE'${NC}"
        echo ""
        read -p "Press Enter to exit"
        exit 1
    fi
    sleep 1
    elapsed=$((elapsed + 1))
    echo -ne "  Waiting... ($elapsed/$timeout sec)\r"
done

echo ""

# Check if Feishu is configured
if [ -z "$FEISHU_APP_ID" ]; then
    echo ""
    echo -e "  ${RED}ERROR: FEISHU_APP_ID not configured!${NC}"
    echo -e "  ${GRAY}Please set FEISHU_APP_ID in .env file${NC}"
    echo ""
    read -p "Press Enter to exit"
    exit 1
fi

# Display service status
echo ""
echo -e "${CYAN}============================================${NC}"
echo -e "${GREEN}           Service Started!${NC}"
echo -e "${CYAN}============================================${NC}"
echo ""

# Feishu channel status - Check actual connection
if [ -n "$FEISHU_APP_ID" ]; then
    # Check actual connection status from log
    if [ -f "$LOG_FILE" ] && grep -q "Feishu WebSocket connected" "$LOG_FILE" 2>/dev/null; then
        echo -e "${GREEN}✓ 飞书通道已连接${NC}"
        echo -e "${GRAY}  App ID: ${FEISHU_APP_ID}${NC}"
        if [ -n "$FEISHU_RECEIVE_USER_ID" ]; then
            echo -e "${GRAY}  Group: ${FEISHU_RECEIVE_USER_ID}${NC}"
        fi
    else
        echo -e "${YELLOW}⚠ 飞书通道正在连接中...${NC}"
        echo -e "${GRAY}  App ID: ${FEISHU_APP_ID}${NC}"
        echo -e "${GRAY}  查看日志获取详细状态: tail -f '$LOG_FILE'${NC}"
    fi
else
    echo -e "${RED}✗ 飞书通道未配置${NC}"
    echo -e "${GRAY}  请在 .env 中设置 FEISHU_APP_ID${NC}"
fi
echo ""

echo ""
echo -e "${CYAN}============================================${NC}"
echo -e "${CYAN}  Commands:${NC}"
echo -e "${CYAN}============================================${NC}"
echo ""
echo -e "  ${GRAY}View logs (live):${NC}"
echo -e "    ${GRAY}tail -f '$LOG_FILE'${NC}"
echo ""
echo -e "  ${GRAY}Stop service:${NC}"
echo -e "    ${GRAY}./stop-mycc.sh${NC}"
echo ""
echo -e "  ${GRAY}Or kill by port:${NC}"
echo -e "    ${GRAY}lsof -i :18080 -t | xargs kill${NC}"
echo ""
echo "============================================" | sed $'s/$/\\e[0;36m/'
echo ""

# Show initial logs (only last 20 lines, monitor for 10 seconds)
echo "显示初始日志 (监控 10 秒后自动退出)..."
echo ""

timeout_end=$(($(date +%s) + 10))
last_line_count=0
while [ $(date +%s) -lt $timeout_end ]; do
    if [ -f "$LOG_FILE" ]; then
        current_line_count=$(wc -l < "$LOG_FILE")
        if [ $current_line_count -gt $last_line_count ]; then
            # Only show last 20 lines
            tail -n 20 "$LOG_FILE" | tail -n +$((last_line_count + 1))
            last_line_count=$current_line_count
        fi
    fi
    sleep 1
done

echo ""
echo -e "${CYAN}============================================${NC}"
echo -e "${GREEN}  Startup script exiting...${NC}"
echo -e "${GREEN}  Backend continues running in background${NC}"
echo -e "${CYAN}============================================${NC}"
echo ""
