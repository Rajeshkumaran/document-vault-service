#!/bin/bash

# Setup script for document-vault-service
# This script sets up the environment and installs all dependencies

echo "🚀 Setting up document-vault-service..."

# Check if Python is installed
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 is not installed. Please install Python 3.8+ first."
    exit 1
fi

# Check if pip is installed
if ! command -v pip3 &> /dev/null; then
    echo "❌ pip3 is not installed. Please install pip first."
    exit 1
fi

# Create virtual environment if it doesn't exist
if [ ! -d ".venv" ]; then
    echo "📦 Creating virtual environment..."
    python3 -m venv .venv
fi

# Activate virtual environment
echo "🔧 Activating virtual environment..."
source .venv/bin/activate

# Upgrade pip
echo "⬆️ Upgrading pip..."
pip install --upgrade pip

# Install production dependencies
echo "📋 Installing production dependencies..."
pip install -r requirements.txt


# Create .env file if it doesn't exist
if [ ! -f ".env" ]; then
    echo "⚙️ Creating .env file..."
    cat > .env << EOF
# Firebase Configuration
FIREBASE_CREDENTIALS_PATH=./app/service-account.json
FIREBASE_STORAGE_BUCKET=your-storage-bucket

# LLM Configuration
ANTHROPIC_API_KEY=your-anthropic-api-key

# Application Configuration
DEBUG=True
LOG_LEVEL=INFO
EOF
    echo "📝 Please update .env file with your actual configuration values"
fi

echo "✅ Setup complete!"
echo ""
echo "Next steps:"
echo "1. Update .env file with your configuration"
echo "2. Add your Firebase service account JSON file"
echo "3. Run the application with: ./run.sh"
