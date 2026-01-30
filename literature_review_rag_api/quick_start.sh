#!/bin/bash
# Quick Start Script for Literature Review RAG System

set -e  # Exit on error

echo "=========================================="
echo "Literature Review RAG - Quick Start"
echo "=========================================="
echo ""

# Check Python version
python_version=$(python --version 2>&1 | awk '{print $2}')
echo "Python version: $python_version"

# Create virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
    echo ""
    echo "Creating virtual environment..."
    python -m venv venv
fi

# Activate virtual environment
echo ""
echo "Activating virtual environment..."
source venv/bin/activate

# Install dependencies
echo ""
echo "Installing dependencies..."
pip install --upgrade pip
pip install -r requirements.txt

# Copy .env.example to .env if .env doesn't exist
if [ ! -f ".env" ]; then
    echo ""
    echo "Creating .env file from .env.example..."
    cp .env.example .env
    echo "✅ Created .env file. Edit it if you need to customize paths."
fi

# Check if indices exist
if [ ! -d "indices" ] || [ -z "$(ls -A indices 2>/dev/null)" ]; then
    echo ""
    echo "=========================================="
    echo "Building Index"
    echo "=========================================="
    echo "Processing 86 academic PDFs..."
    echo "This will take ~10-15 minutes..."
    echo ""
    python scripts/build_index.py
else
    echo ""
    echo "✅ Indices already exist. Skipping index building."
    echo "   To rebuild, delete the 'indices' folder and run this script again."
fi

echo ""
echo "=========================================="
echo "Setup Complete!"
echo "=========================================="
echo ""
echo "To start the API server, run:"
echo "  source venv/bin/activate"
echo "  uvicorn literature_rag.api:app --host 0.0.0.0 --port 8001"
echo ""
echo "Then open your browser to:"
echo "  http://localhost:8001/docs"
echo ""
echo "Or run this command to start the server now:"
read -p "Start server now? (y/n) " -n 1 -r
echo ""
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo ""
    echo "Starting server..."
    uvicorn literature_rag.api:app --host 0.0.0.0 --port 8001
fi
