# Nginx Setup Guide for Sharing via Ngrok

This setup allows you to expose both frontend and backend through a **single ngrok tunnel** using nginx as a reverse proxy.

## Architecture

```
┌─────────────┐
│   Ngrok     │  Single tunnel
│   (port     │
│    8080)    │
└──────┬──────┘
       │
       ▼
┌─────────────┐
│   Nginx     │  Reverse proxy
│  (port 8080)│
└──────┬──────┘
       │
       ├─────────────────┬──────────────┐
       ▼                 ▼              ▼
┌─────────────┐   ┌──────────┐   ┌──────────┐
│  Frontend   │   │ Backend  │   │   API    │
│    Vite     │   │  Flask   │   │   /api/* │
│ (port 5173) │   │  (5001)  │   │          │
└─────────────┘   └──────────┘   └──────────┘
```

## Quick Start

### Step 1: Install nginx (if not installed)

**macOS:**
```bash
brew install nginx
```

**Linux (Ubuntu/Debian):**
```bash
sudo apt-get update
sudo apt-get install nginx
```

### Step 2: Start all services

Run the startup script:
```bash
./start-all.sh
```

This will automatically:
- ✅ Start Flask backend on port 5001
- ✅ Start Vite frontend on port 5173
- ✅ Start nginx on port 8080

### Step 3: Expose via ngrok

In a **new terminal**, run:
```bash
ngrok http 8080
```

You'll get a URL like: `https://abc123.ngrok-free.app`

### Step 4: Share with your colleague

Send them the ngrok URL. They can access:
- **App**: `https://abc123.ngrok-free.app/`
- **API**: `https://abc123.ngrok-free.app/api/health`

Everything works through the same domain! 🎉

## Manual Setup (Alternative)

If you prefer to start services manually:

### 1. Start Backend
```bash
cd /Users/dhruveel/Development_Tools/rani-timestamps-generator
source venv/bin/activate
python app.py
```

### 2. Start Frontend (new terminal)
```bash
cd /Users/dhruveel/Development_Tools/rani-timestamps-generator/frontend
npm run dev
```

### 3. Start Nginx (new terminal)
```bash
cd /Users/dhruveel/Development_Tools/rani-timestamps-generator
nginx -c "$(pwd)/nginx.conf" -p "$(pwd)"
```

### 4. Expose via Ngrok (new terminal)
```bash
ngrok http 8080
```

## Stopping Services

### If using start-all.sh:
Press `Ctrl+C` in the terminal running the script.

### If started manually:
```bash
# Stop nginx
nginx -s stop -c "$(pwd)/nginx.conf" -p "$(pwd)"

# Stop Flask and Vite (Ctrl+C in their terminals)
```

## Troubleshooting

### Port already in use
If you get port conflicts:
```bash
# Kill processes on specific ports
lsof -ti:5001 | xargs kill -9  # Backend
lsof -ti:5173 | xargs kill -9  # Frontend
lsof -ti:8080 | xargs kill -9  # Nginx
```

### Nginx config errors
Test the config:
```bash
nginx -t -c "$(pwd)/nginx.conf" -p "$(pwd)"
```

### Large file upload fails
The nginx.conf is already configured for:
- ✅ 1000MB max file size
- ✅ 10-minute timeout for processing
- ✅ Chunked upload support

Check the logs:
```bash
tail -f /tmp/nginx-access.log
tail -f /tmp/nginx-error.log
```

## Configuration Files

- `nginx.conf` - Nginx reverse proxy configuration
- `start-all.sh` - Automated startup script
- `frontend/src/services/api.js` - Auto-detects ngrok and routes API calls correctly

## How It Works

1. **Nginx listens on port 8080**
2. **Routes `/api/*` to Flask (port 5001)**
3. **Routes `/*` to Vite frontend (port 5173)**
4. **Ngrok exposes port 8080 to the internet**
5. **Frontend automatically detects it's behind ngrok and uses the same domain for API calls**

Your colleague gets a single URL and everything just works! 🚀
