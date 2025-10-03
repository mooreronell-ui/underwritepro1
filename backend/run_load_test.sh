#!/bin/bash
# Automated Load Test Script for UnderwritePro SaaS

echo "========================================="
echo "UnderwritePro SaaS - Load Test"
echo "========================================="
echo ""

# Configuration
HOST="http://localhost:8000"
USERS=100  # Start with 100 users
SPAWN_RATE=10  # Spawn 10 users per second
DURATION=60  # Run for 60 seconds

echo "Configuration:"
echo "  Host: $HOST"
echo "  Users: $USERS"
echo "  Spawn Rate: $SPAWN_RATE/sec"
echo "  Duration: ${DURATION}s"
echo ""

# Check if application is running
echo "Checking if application is running..."
if ! curl -s "$HOST/api/health" > /dev/null; then
    echo "ERROR: Application is not running at $HOST"
    exit 1
fi
echo "✓ Application is running"
echo ""

# Run load test
echo "Starting load test..."
echo "Running locust in headless mode..."
echo ""

locust -f load_test.py \
    --host="$HOST" \
    --users=$USERS \
    --spawn-rate=$SPAWN_RATE \
    --run-time=${DURATION}s \
    --headless \
    --html=load_test_report.html \
    --csv=load_test_results

echo ""
echo "========================================="
echo "Load Test Complete!"
echo "========================================="
echo ""
echo "Results saved to:"
echo "  - load_test_report.html (HTML report)"
echo "  - load_test_results_stats.csv (Statistics)"
echo "  - load_test_results_failures.csv (Failures)"
echo ""
