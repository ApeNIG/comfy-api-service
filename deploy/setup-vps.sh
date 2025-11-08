#!/bin/bash
# ComfyUI API Service - VPS Setup Script
# Run this on your fresh Ubuntu 22.04 VPS

set -e  # Exit on error

echo "============================================================"
echo "          ComfyUI API Service - VPS Setup"
echo "============================================================"
echo ""

# Update system
echo "Step 1: Updating system packages..."
apt update && apt upgrade -y

# Install Docker
echo ""
echo "Step 2: Installing Docker..."
curl -fsSL https://get.docker.com | sh
systemctl enable docker
systemctl start docker

# Install Docker Compose
echo ""
echo "Step 3: Installing Docker Compose..."
apt install docker-compose-plugin -y

# Install Nginx and Certbot
echo ""
echo "Step 4: Installing Nginx and Certbot..."
apt install nginx certbot python3-certbot-nginx -y

# Configure firewall
echo ""
echo "Step 5: Configuring firewall..."
ufw allow OpenSSH
ufw allow 80/tcp
ufw allow 443/tcp
ufw --force enable

echo ""
echo "============================================================"
echo "                    Setup Complete!"
echo "============================================================"
echo ""
echo "Next steps:"
echo "  1. Clone your repository"
echo "  2. Configure .env file"
echo "  3. Run docker compose up -d"
echo ""
echo "Run the deployment script: ./deploy/deploy-api.sh"
echo ""
