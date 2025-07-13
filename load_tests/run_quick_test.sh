#!/bin/bash

# Quick 2-minute load test for immediate feedback
# Usage: ./run_quick_test.sh

set -e

echo "Quick Thanotopolis Load Test (2 minutes)"
echo "========================================"

# Check if we're in the load_tests directory
if [ ! -f "main_load_test.py" ]; then
    echo "Please run this script from the load_tests directory"
    exit 1
fi

# Quick test parameters
USERS=5
SPAWN_RATE=1
RUN_TIME=120s
HOST=http://localhost:8001

echo "Test Parameters:"
echo "  Target: $HOST"
echo "  Users: $USERS"
echo "  Duration: $RUN_TIME"
echo ""

# Run a quick test
echo "Running quick load test..."
locust -f main_load_test.py \
    --host="$HOST" \
    --users="$USERS" \
    --spawn-rate="$SPAWN_RATE" \
    --run-time="$RUN_TIME" \
    --headless

echo ""
echo "Quick test completed!"