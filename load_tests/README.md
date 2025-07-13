# Thanotopolis Load Testing Suite

A comprehensive load testing suite for the Thanotopolis cemetery management platform using Locust.

## Overview

This load testing suite covers all major API endpoints and WebSocket connections in the Thanotopolis platform:

- **Authentication**: Login, registration, token management
- **CRM**: Contact management, interactions, search
- **Calendar**: Event creation, scheduling, statistics
- **Telephony**: Call management, verification, webhooks
- **WebSocket**: Real-time communication, voice streaming, notifications

## Setup

### 1. Install Dependencies

```bash
cd load_tests
pip install -r requirements.txt
```

### 2. Configuration

The load tests work out-of-the-box with sensible defaults:

- **Default target**: `https://dev.thanotopolis.com`
- **Default credentials**: `loadtest@thanotopolis.com` / `LoadTest2025!`
- **WebSocket URL**: Auto-detected from base URL

**Optional environment variables** (only if you need to override defaults):

```bash
# Override target server (optional)
export LOAD_TEST_BASE_URL=http://localhost:8001

# Override test credentials (optional)
export LOAD_TEST_USER_EMAIL=mytest@example.com
export LOAD_TEST_USER_PASSWORD=MyPassword123

# Disable external service simulation (optional)
export SIMULATE_EXTERNAL_SERVICES=false
```

## Running Load Tests

### Quick Start (Headless - No Browser Required)

```bash
cd load_tests
pip install -r requirements.txt

# Run quick authentication test (expect auth failures - this tests the framework)
locust -f scenarios/auth_load_test.py AuthenticationUser --host=http://localhost:8001 \
  --users=5 --spawn-rate=1 --run-time=60s --headless

# Run comprehensive test for 5 minutes with 10 users
locust -f main_load_test.py --host=http://localhost:8001 \
  --users=10 --spawn-rate=2 --run-time=300s --headless

# Generate HTML report
locust -f main_load_test.py --host=http://localhost:8001 \
  --users=10 --spawn-rate=2 --run-time=300s --headless \
  --html=load_test_report.html
```

**Note**: Authentication tests will show failures (401/422 errors) since test users don't exist. This demonstrates the load testing framework is working correctly.

### Individual Test Scenarios (Headless)

Run specific test scenarios for focused testing:

```bash
# Authentication endpoints only
locust -f scenarios/auth_load_test.py --host=https://dev.thanotopolis.com \
  --users=5 --spawn-rate=1 --run-time=180s --headless

# CRM endpoints only  
locust -f scenarios/crm_load_test.py --host=https://dev.thanotopolis.com \
  --users=8 --spawn-rate=2 --run-time=300s --headless

# Calendar endpoints only
locust -f scenarios/calendar_load_test.py --host=https://dev.thanotopolis.com \
  --users=6 --spawn-rate=1 --run-time=240s --headless

# Telephony endpoints only
locust -f scenarios/telephony_load_test.py --host=https://dev.thanotopolis.com \
  --users=4 --spawn-rate=1 --run-time=180s --headless

# WebSocket connections only
locust -f scenarios/websocket_load_test.py --host=https://dev.thanotopolis.com \
  --users=3 --spawn-rate=1 --run-time=120s --headless
```

### Comprehensive Testing

Run the full suite with realistic user workflows:

```bash
# Complete load test with all scenarios
locust -f main_load_test.py --host=https://dev.thanotopolis.com \
  --users=20 --spawn-rate=3 --run-time=600s --headless \
  --html=comprehensive_report.html --csv=results
```

### Command Line Options

```bash
# Run with specific user count and spawn rate
locust -f main_load_test.py --host=http://localhost:8001 -u 10 -r 2

# Run headless (no web UI) for CI/CD
locust -f main_load_test.py --host=http://localhost:8001 -u 10 -r 2 --headless -t 300s

# Generate HTML report
locust -f main_load_test.py --host=http://localhost:8001 -u 10 -r 2 --headless -t 300s --html report.html
```

## Test Scenarios Explained

### Authentication Load Test (`auth_load_test.py`)
- Tests user registration, login, logout flows
- Token refresh and validation
- Profile updates
- **Weight Distribution**: 40% login, 30% registration, 20% profile operations, 10% logout

### CRM Load Test (`crm_load_test.py`)
- Contact CRUD operations
- Contact search and filtering
- Interaction logging
- Dashboard statistics
- **Weight Distribution**: 50% read operations, 30% create, 15% update, 5% delete

### Calendar Load Test (`calendar_load_test.py`)
- Event creation and management
- Date range queries
- Event statistics
- CRM integration (linking contacts to events)
- **Weight Distribution**: 40% list/view, 25% create, 20% range queries, 10% update, 5% delete

### Telephony Load Test (`telephony_load_test.py`)
- Phone verification workflows
- Call listing and details
- Webhook simulation (Twilio)
- Call analytics
- **Weight Distribution**: 50% call listing, 20% verification, 15% webhook simulation, 15% analytics

### WebSocket Load Test (`websocket_load_test.py`)
- Real-time conversation streams
- Voice-to-text streaming
- Telephony media streaming  
- Push notifications
- **Special handling**: Persistent connections, binary data simulation

## Load Test Patterns

### User Distribution
The comprehensive test (`main_load_test.py`) simulates realistic user distribution:
- **40% CRM Users**: Heavy contact management
- **30% Calendar Users**: Scheduling and appointments  
- **15% Authentication Users**: New users, login/logout
- **15% Telephony Users**: Call management

### Realistic Workflows
Multi-step workflows that span features:
1. **Customer Intake**: Create contact → Log interaction → Schedule appointment
2. **Daily Admin**: Check dashboard → Review calendar → Update records
3. **Search & Schedule**: Find contact → View details → Create appointment
4. **Bulk Operations**: Multiple contacts → Batch scheduling

## Performance Targets

### Response Time Targets
- **Authentication**: < 500ms average
- **CRM Operations**: < 1000ms average  
- **Calendar Operations**: < 800ms average
- **Search Operations**: < 1500ms average
- **WebSocket Connection**: < 2000ms setup

### Throughput Targets
- **Peak Load**: 100 concurrent users
- **Sustained Load**: 50 concurrent users
- **Rate Limit Compliance**: < 120 req/min per user

### Error Rate Targets
- **Overall Error Rate**: < 1%
- **Authentication Errors**: < 0.5%
- **Critical Path Errors**: < 0.1%

## Monitoring During Tests

### Console Output (Headless Mode)
When running in headless mode, Locust provides real-time statistics in the console:
- Request statistics (RPS, response times, failures)
- User count and spawn rate
- Test progress and duration
- Error summaries

### Key Metrics to Watch
- **Response Times**: Average, median, 95th/99th percentiles
- **Failure Rate**: Overall and per endpoint
- **Requests/Second**: Throughput measurement
- **User Distribution**: Ensure balanced scenario execution

### System Resources
Monitor server resources during tests:
```bash
# CPU and memory usage
htop

# Database connections
sudo -u postgres psql -c "SELECT count(*) FROM pg_stat_activity;"

# Network connections  
netstat -an | grep :8001 | wc -l
```

## CI/CD Integration

### Automated Testing
```bash
#!/bin/bash
# Example CI script

# Install dependencies
pip install -r load_tests/requirements.txt

# Run load test
locust -f load_tests/main_load_test.py \
  --host=https://dev.thanotopolis.com \
  --users=20 \
  --spawn-rate=2 \
  --headless \
  --run-time=300s \
  --html=load_test_report.html \
  --csv=load_test_results

# Check for acceptable failure rate
python check_results.py load_test_results_stats.csv
```

### Performance Regression Detection
Set thresholds in your CI pipeline:
- Fail if average response time > 2000ms
- Fail if error rate > 2%
- Fail if 95th percentile > 5000ms

## Troubleshooting

### Common Issues

#### Authentication Failures
```bash
# Check if test user exists and credentials are correct
LOAD_TEST_USER_EMAIL=test@example.com python -c "
from load_tests.utils.auth import auth_manager
token = auth_manager.get_or_create_token()
print('Success' if token else 'Failed')
"
```

#### Connection Errors
```bash
# Verify server is running
curl http://localhost:8001/health

# Check WebSocket connectivity
wscat -c ws://localhost:8001/api/ws/notifications
```

#### Rate Limiting
```bash
# Reduce user count or spawn rate
locust -f main_load_test.py --host=http://localhost:8001 -u 5 -r 1
```

### Debug Mode
Enable debug logging:
```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

## Best Practices

### Test Environment
- Use dedicated test database
- Ensure adequate server resources
- Monitor system metrics during tests
- Clean up test data between runs

### Load Test Design
- Start with small user counts
- Gradually increase load
- Test individual components before comprehensive tests
- Include realistic wait times between requests

### Data Management
- Use realistic test data
- Avoid hardcoded values
- Clean up test artifacts
- Respect rate limits and quotas

### Reporting
- Generate HTML reports for stakeholders
- Track performance trends over time
- Document performance requirements
- Share results with development team

## Security Considerations

- Use test credentials only
- Don't run against production
- Limit scope of destructive operations
- Monitor for sensitive data exposure
- Clean up authentication tokens

## Support

For issues with the load testing suite:
1. Check the troubleshooting section
2. Review Locust documentation: https://docs.locust.io/
3. Examine test logs for specific errors
4. Verify environment configuration

## File Structure

```
load_tests/
├── README.md                 # This file
├── requirements.txt          # Python dependencies
├── main_load_test.py        # Comprehensive test suite
├── configs/
│   └── settings.py          # Configuration settings
├── utils/
│   ├── __init__.py
│   └── auth.py              # Authentication helpers
└── scenarios/
    ├── __init__.py
    ├── auth_load_test.py     # Authentication tests
    ├── crm_load_test.py      # CRM tests
    ├── calendar_load_test.py # Calendar tests
    ├── telephony_load_test.py # Telephony tests
    └── websocket_load_test.py # WebSocket tests
```