#!/bin/bash
# ComfyUI API Service - SSL Setup Script
# Usage: ./setup-ssl.sh your-domain.com

set -e

if [ -z "$1" ]; then
    echo "Usage: $0 <domain>"
    echo "Example: $0 api.yourdomain.com"
    exit 1
fi

DOMAIN=$1

echo "============================================================"
echo "       Setting up SSL for $DOMAIN"
echo "============================================================"
echo ""

# Create Nginx configuration
echo "Creating Nginx configuration..."
cat > /etc/nginx/sites-available/comfyui-api << EOF
server {
    listen 80;
    server_name $DOMAIN;

    # Security headers
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;

    # Proxy settings
    location / {
        proxy_pass http://localhost:8000;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;

        # WebSocket support (if needed later)
        proxy_http_version 1.1;
        proxy_set_header Upgrade \$http_upgrade;
        proxy_set_header Connection "upgrade";

        # Timeouts for long-running requests
        proxy_read_timeout 600s;
        proxy_connect_timeout 600s;
        proxy_send_timeout 600s;
    }

    # Health check endpoint
    location /health {
        proxy_pass http://localhost:8000/health;
        access_log off;
    }
}
EOF

# Enable site
ln -sf /etc/nginx/sites-available/comfyui-api /etc/nginx/sites-enabled/

# Test Nginx configuration
echo ""
echo "Testing Nginx configuration..."
nginx -t

# Reload Nginx
echo ""
echo "Reloading Nginx..."
systemctl reload nginx

# Get SSL certificate
echo ""
echo "Obtaining SSL certificate from Let's Encrypt..."
echo ""
echo "IMPORTANT: Make sure $DOMAIN points to this server's IP!"
echo ""
read -p "Press Enter to continue..."

certbot --nginx -d $DOMAIN --non-interactive --agree-tos --register-unsafely-without-email || \
    certbot --nginx -d $DOMAIN

echo ""
echo "============================================================"
echo "                   SSL Setup Complete!"
echo "============================================================"
echo ""
echo "Your API is now available at: https://$DOMAIN"
echo ""
echo "Test it:"
echo "  curl https://$DOMAIN/health"
echo "  curl https://$DOMAIN/api/v1/monitoring/stats"
echo ""
echo "Next step: Generate API keys with ./deploy/create-api-key.sh"
echo ""
