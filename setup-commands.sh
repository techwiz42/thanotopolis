#!/bin/bash
# Thanotopolis Dev Environment Setup Script
# Run these commands with sudo to complete the setup

echo "=== Thanotopolis Dev Environment Setup ==="
echo "This script shows the commands needed to complete the setup."
echo "You'll need to run these with sudo."
echo ""

echo "1. Generate SSL Certificate:"
echo "sudo certbot certonly --nginx -d dev.thanotopolis.com"
echo ""

echo "2. Copy nginx configuration:"
echo "sudo cp /home/peter/thanotopolis_dev/nginx-thanotopolis-dev.conf /etc/nginx/sites-available/thanotopolis-dev"
echo "sudo ln -s /etc/nginx/sites-available/thanotopolis-dev /etc/nginx/sites-enabled/"
echo "sudo nginx -t"
echo "sudo systemctl reload nginx"
echo ""

echo "3. Install systemd services:"
echo "sudo cp /home/peter/thanotopolis_dev/thanotopolis-backend-dev.service /etc/systemd/system/"
echo "sudo cp /home/peter/thanotopolis_dev/thanotopolis-frontend-dev.service /etc/systemd/system/"
echo "sudo systemctl daemon-reload"
echo "sudo systemctl enable thanotopolis-backend-dev"
echo "sudo systemctl enable thanotopolis-frontend-dev"
echo "sudo systemctl start thanotopolis-backend-dev"
echo "sudo systemctl start thanotopolis-frontend-dev"
echo ""

echo "4. Check service status:"
echo "sudo systemctl status thanotopolis-backend-dev"
echo "sudo systemctl status thanotopolis-frontend-dev"
echo ""

echo "5. Test the setup:"
echo "curl https://dev.thanotopolis.com/api/health"
echo "curl https://dev.thanotopolis.com"
echo ""

echo "=== Manual Testing Commands ==="
echo "If you want to test manually before setting up services:"
echo ""
echo "Backend (in one terminal):"
echo "cd /home/peter/thanotopolis_dev/backend"
echo "~/.virtualenvs/thanos/bin/uvicorn app.main:app --host 0.0.0.0 --port 8001"
echo ""
echo "Frontend (in another terminal):"
echo "cd /home/peter/thanotopolis_dev/frontend"
echo "npm run dev -- --port 3001"