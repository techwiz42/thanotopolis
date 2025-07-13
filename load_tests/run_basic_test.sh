#!/bin/bash

# Basic load test script for Digital Ocean droplet (headless)
# Usage: ./run_basic_test.sh

set -e

echo "Starting Thanotopolis Load Test..."
echo "=================================="

# Check if we're in the load_tests directory
if [ ! -f "main_load_test.py" ]; then
    echo "Please run this script from the load_tests directory"
    exit 1
fi

# Install dependencies if needed
if [ ! -d "venv" ]; then
    echo "Installing dependencies..."
    pip install -r requirements.txt
fi

# Set default parameters
USERS=${USERS:-10}
SPAWN_RATE=${SPAWN_RATE:-2}
RUN_TIME=${RUN_TIME:-300s}
HOST=${HOST:-http://localhost:8001}

echo "Test Parameters:"
echo "  Target: $HOST"
echo "  Users: $USERS"
echo "  Spawn Rate: $SPAWN_RATE users/second"
echo "  Duration: $RUN_TIME"
echo ""

# Run the comprehensive load test
echo "Running comprehensive load test..."
locust -f main_load_test.py \
    --host="$HOST" \
    --users="$USERS" \
    --spawn-rate="$SPAWN_RATE" \
    --run-time="$RUN_TIME" \
    --headless \
    --html=load_test_report.html \
    --csv=load_test_results

echo ""
echo "Test completed!"
echo "Results saved to:"
echo "  - HTML Report: load_test_report.html"
echo "  - CSV Data: load_test_results_*.csv"
echo ""
echo "To download the report:"
echo "  scp user@droplet:/path/to/load_tests/load_test_report.html ."