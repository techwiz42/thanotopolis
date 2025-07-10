#!/bin/bash
# Thanotopolis Dev Environment Deployment Script
# This script will actually run the setup commands

set -e  # Exit on error

echo "=== Thanotopolis Dev Environment Deployment ==="
echo "This script will set up the complete dev environment."
echo "Make sure you have sudo access."
echo ""

# Function to check command success
check_status() {
    if [ $? -eq 0 ]; then
        echo "✓ $1 successful"
    else
        echo "✗ $1 failed"
        exit 1
    fi
}

echo "Step 1: Generating SSL Certificate..."
sudo certbot certonly --nginx -d dev.thanotopolis.com
check_status "SSL certificate generation"
echo ""

echo "Step 2: Deploying nginx configuration..."
sudo cp /home/peter/thanotopolis_dev/nginx-thanotopolis-dev.conf /etc/nginx/sites-available/thanotopolis-dev
check_status "Copy nginx config"

sudo ln -sf /etc/nginx/sites-available/thanotopolis-dev /etc/nginx/sites-enabled/
check_status "Enable nginx site"

echo "Testing nginx configuration..."
sudo nginx -t
check_status "Nginx config test"

echo "Reloading nginx..."
sudo systemctl reload nginx
check_status "Nginx reload"
echo ""

echo "Step 3: Installing systemd services..."
sudo cp /home/peter/thanotopolis_dev/thanotopolis-backend-dev.service /etc/systemd/system/
check_status "Copy backend service"

sudo cp /home/peter/thanotopolis_dev/thanotopolis-frontend-dev.service /etc/systemd/system/
check_status "Copy frontend service"

echo "Reloading systemd daemon..."
sudo systemctl daemon-reload
check_status "Systemd daemon reload"
echo ""

echo "Step 4: Enabling and starting services..."
sudo systemctl enable thanotopolis-backend-dev
check_status "Enable backend service"

sudo systemctl enable thanotopolis-frontend-dev
check_status "Enable frontend service"

echo "Starting backend service..."
sudo systemctl start thanotopolis-backend-dev
check_status "Start backend service"

echo "Starting frontend service..."
sudo systemctl start thanotopolis-frontend-dev
check_status "Start frontend service"
echo ""

echo "Step 5: Checking service status..."
echo "Backend service status:"
sudo systemctl status thanotopolis-backend-dev --no-pager | head -10
echo ""

echo "Frontend service status:"
sudo systemctl status thanotopolis-frontend-dev --no-pager | head -10
echo ""

echo "Step 6: Testing endpoints..."
sleep 5  # Give services time to start

echo "Testing backend health endpoint..."
curl -s https://dev.thanotopolis.com/api/health || echo "Backend not responding yet"
echo ""

echo "Testing frontend..."
curl -sI https://dev.thanotopolis.com | head -5 || echo "Frontend not responding yet"
echo ""

echo "=== Deployment Complete ==="
echo ""
echo "If services aren't responding yet, they may still be starting up."
echo "Check logs with:"
echo "  sudo journalctl -u thanotopolis-backend-dev -f"
echo "  sudo journalctl -u thanotopolis-frontend-dev -f"
echo ""
echo "Access your dev environment at: https://dev.thanotopolis.com"