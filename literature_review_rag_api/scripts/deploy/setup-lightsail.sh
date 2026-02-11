#!/bin/bash
# ============================================================================
# Lightsail Instance Setup Script
# Run this on a fresh Ubuntu 22.04 Lightsail instance
# ============================================================================

set -e

echo "=========================================="
echo "Literature RAG - Lightsail Setup"
echo "=========================================="

# Update system
echo "Updating system packages..."
sudo apt-get update && sudo apt-get upgrade -y

# Install Docker
echo "Installing Docker..."
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo usermod -aG docker $USER

# Install Docker Compose
echo "Installing Docker Compose..."
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose

# Install useful tools
echo "Installing additional tools..."
sudo apt-get install -y git htop curl wget unzip

# Create app directory
echo "Creating application directory..."
APP_ROOT="/home/$USER/literature_review_rag_api"
BACKEND_DIR="$APP_ROOT/literature_review_rag_api"
mkdir -p "$APP_ROOT"

# Create data directories (under the backend folder used by docker-compose)
mkdir -p "$BACKEND_DIR/data/db"
mkdir -p "$BACKEND_DIR/data/indices"
mkdir -p "$BACKEND_DIR/data/uploads"
mkdir -p "$BACKEND_DIR/certbot/conf"
mkdir -p "$BACKEND_DIR/certbot/www"
mkdir -p "$BACKEND_DIR/nginx/ssl"

echo "=========================================="
echo "Setup complete!"
echo ""
echo "Next steps:"
echo "1. Log out and back in (for docker group)"
echo "2. Clone your repository to ~/literature_review_rag_api"
echo "3. Copy .env.example to .env and configure"
echo "4. Run: docker-compose up -d"
echo "=========================================="
