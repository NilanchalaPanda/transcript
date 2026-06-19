#!/bin/bash

# Script to start ngrok tunnel for the Audio Timestamp Generator
# This exposes your local React frontend (port 3000) to the internet
# The frontend automatically proxies API requests to the backend (port 5001)

echo "================================================================"
echo "🌐 Starting ngrok tunnel for Audio Timestamp Generator"
echo "================================================================"
echo ""
echo "📋 Setup:"
echo "   - Frontend: http://localhost:3000 (exposed via ngrok)"
echo "   - Backend:  http://localhost:5001 (proxied via frontend)"
echo ""
echo "⚠️  Important Notes for Large File Uploads (500+ MB):"
echo "   - Free ngrok has connection time limits"
echo "   - Frontend proxies all /api requests to backend"
echo "   - For production with large files, consider ngrok paid plan"
echo ""
echo "🔧 Starting tunnel on port 3000..."
echo ""

# Start ngrok tunnel
# Using --config flag if you have custom ngrok.yml
if [ -f "ngrok.yml" ]; then
    echo "📋 Using custom ngrok.yml configuration..."
    ngrok start react-frontend --config=ngrok.yml
else
    echo "📋 Using default configuration..."
    ngrok http 3000 --log=stdout
fi
