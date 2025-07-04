#!/bin/bash

# Test Email API Script
# This script tests the /api/crm/test-email endpoint

echo "=== Thanotopolis CRM Email API Test ==="
echo

# Check if API URL is provided
API_URL=${1:-"http://localhost:8000"}
echo "API URL: $API_URL"

# Get test email address
read -p "Enter the email address to send test email to: " TEST_EMAIL

if [ -z "$TEST_EMAIL" ]; then
    echo "❌ No email address provided"
    exit 1
fi

# Get JWT token (you'll need to replace this with actual login)
read -p "Enter your JWT token (or press Enter to skip): " JWT_TOKEN

if [ -z "$JWT_TOKEN" ]; then
    echo "⚠️  No JWT token provided. You'll need to authenticate first."
    echo "   You can get a token by logging into the application."
    exit 1
fi

echo

# Test simple email
echo "📧 Testing simple email..."
SIMPLE_RESPONSE=$(curl -s -X POST "$API_URL/api/crm/test-email" \
    -H "Content-Type: application/json" \
    -H "Authorization: Bearer $JWT_TOKEN" \
    -d "{\"to_email\": \"$TEST_EMAIL\", \"test_type\": \"simple\"}")

echo "Response: $SIMPLE_RESPONSE"

# Check if successful
if echo "$SIMPLE_RESPONSE" | grep -q '"success": true'; then
    echo "✅ Simple email test successful!"
else
    echo "❌ Simple email test failed"
fi

echo

# Test template email
echo "📧 Testing template email..."
TEMPLATE_RESPONSE=$(curl -s -X POST "$API_URL/api/crm/test-email" \
    -H "Content-Type: application/json" \
    -H "Authorization: Bearer $JWT_TOKEN" \
    -d "{\"to_email\": \"$TEST_EMAIL\", \"test_type\": \"template\"}")

echo "Response: $TEMPLATE_RESPONSE"

# Check if successful
if echo "$TEMPLATE_RESPONSE" | grep -q '"success": true'; then
    echo "✅ Template email test successful!"
else
    echo "❌ Template email test failed"
fi

echo
echo "🎉 Email API testing complete!"
echo
echo "To get a JWT token:"
echo "1. Log into your Thanotopolis application"
echo "2. Open browser dev tools (F12)"
echo "3. Go to Application/Storage tab"
echo "4. Find 'access_token' in localStorage"
echo "5. Copy the token value (without quotes)"