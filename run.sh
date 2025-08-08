#!/bin/bash

# Simple run script for the Document Vault Service
echo "Starting Document Vault Service..."

# Check if .env exists
if [ ! -f ".env" ]; then
    echo "Creating .env file from .env.example..."
    cp .env.example .env
    echo "Please edit .env file with your Supabase configuration before running the server."
    exit 1
fi

# Run the FastAPI server
echo "Starting FastAPI server on http://localhost:8000"
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000