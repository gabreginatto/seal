#!/bin/bash
###############################################################################
# Seal - PNCP Lacre Discovery Runner
#
# Proper startup script for running lacre tender discovery
#
# Usage:
#   ./run_lacre_discovery.sh --start-date YYYYMMDD --end-date YYYYMMDD --states XX [--discovery-only]
#
# Examples:
#   ./run_lacre_discovery.sh --start-date 20251001 --end-date 20251031 --states SP --discovery-only
#   ./run_lacre_discovery.sh --start-date 20251001 --end-date 20251031 --states "SP,RJ,MG"
###############################################################################

# Error handling
set -euo pipefail

# Get the script directory (absolute path to Seal directory)
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

# Check if we're in the Seal directory
if [ ! -f "$SCRIPT_DIR/main.py" ]; then
    echo "Error: main.py not found in $SCRIPT_DIR"
    echo "Please run this script from the Seal directory"
    exit 1
fi

# Change to Seal directory
cd "$SCRIPT_DIR"

# Set Google Cloud credentials
CREDENTIALS_PATH="$SCRIPT_DIR/setup/pncp-key.json"
if [ ! -f "$CREDENTIALS_PATH" ]; then
    echo "Error: Google Cloud credentials not found at $CREDENTIALS_PATH"
    exit 1
fi

export GOOGLE_APPLICATION_CREDENTIALS="$CREDENTIALS_PATH"

# Create logs directory if it doesn't exist
mkdir -p "$SCRIPT_DIR/logs"

# Parse arguments
ARGS="$@"

# Generate timestamp for log file
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
LOG_FILE="$SCRIPT_DIR/logs/seal_run_${TIMESTAMP}.log"

# Print startup information
echo "======================================================================="
echo "Starting PNCP Lacre Discovery"
echo "======================================================================="
echo "Working Directory: $SCRIPT_DIR"
echo "Credentials: $CREDENTIALS_PATH"
echo "Arguments: $ARGS"
echo "Log File: $LOG_FILE"
echo "======================================================================="
echo ""

# Run the script in the background with nohup
nohup python main.py $ARGS > "$LOG_FILE" 2>&1 &
PID=$!

echo "✓ Process started with PID: $PID"
echo ""
echo "Monitor progress with:"
echo "  tail -f $LOG_FILE"
echo ""
echo "Or check the main log at:"
echo "  tail -f $SCRIPT_DIR/logs/pncp_lacre_*.log"
echo ""
echo "Check process status:"
echo "  ps aux | grep $PID"
echo ""
echo "Kill process if needed:"
echo "  kill $PID"
echo ""
