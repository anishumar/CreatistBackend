#!/bin/bash

# Development startup script
set -e

echo "🚀 Starting Creatist Backend in Development Mode"

# Activate virtual environment
source venv/bin/activate

# Use development environment variables
export $(cat .env.dev | grep -v '^#' | xargs)

# Check if we can connect to Supabase
echo "🔍 Testing Supabase connection..."
if curl -s --connect-timeout 5 "https://wkmribpqhgdpklwovrov.supabase.co" > /dev/null; then
    echo "✅ Supabase connection successful"
else
    echo "⚠️  Supabase connection failed, but continuing..."
fi

echo "🚀 Starting server on http://localhost:8000"
echo "📊 Health check: http://localhost:8000/health"
echo "📚 API docs: http://localhost:8000/docs"

# Run the application
python main.py
