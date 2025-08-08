#!/bin/bash

# Document Vault Service Startup Script

echo "Setting up Document Vault Service..."

# Create virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
echo "Activating virtual environment..."
source venv/bin/activate

# Install dependencies
echo "Installing dependencies..."
pip install -r requirements.txt

# Create .env file if it doesn't exist
if [ ! -f ".env" ]; then
    echo "Creating .env file..."
    cp .env.example .env
    echo "⚠️  IMPORTANT: Please edit .env file with your actual Supabase configuration"
    echo "   The .env file contains secrets and will NOT be committed to git"
    echo "   Only .env.example (with placeholder values) is committed to git"
fi

# Create uploads directory
mkdir -p uploads

echo "Setup complete!"
echo ""
echo "To start the development server:"
echo "1. Activate virtual environment: source venv/bin/activate"
echo "2. Run: uvicorn app.main:app --reload"
echo "   Or use the convenience script: ./run.sh"
echo ""
echo "API Documentation will be available at:"
echo "- Swagger UI: http://localhost:8000/docs"
echo "- ReDoc: http://localhost:8000/redoc"
