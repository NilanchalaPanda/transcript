
# Audio Timestamp Generator

A full-stack application for generating accurate timestamps and transcripts from audio files with speaker diarization. Built with Flask backend and React frontend, supporting large file uploads via signed URLs and chunked transfers.

## Features

- **Large File Support**: Handles files up to 500MB using chunked uploads with signed URLs
- **Speaker Diarization**: Automatically identifies and labels different speakers (A and B)
- **Accurate Timestamps**: Uses WhisperX for precise word-level alignment
- **Multiple Export Formats**: Download results as JSON, CSV, or TXT
- **Real-time Progress**: Visual feedback during upload and processing
- **Search & Filter**: Find specific segments and filter by speaker

## Architecture

### Backend (Flask)

- RESTful API with CORS support
- Signed URL authentication for secure uploads
- Chunked file upload for large files
- WhisperX integration for audio processing
- Automatic cleanup of temporary files

### Frontend (React + Vite)

- Modern, responsive UI with Tailwind CSS
- Drag-and-drop file upload
- Real-time progress tracking
- Interactive results display with search and filtering
- Multiple download formats

## Prerequisites

- Python 3.8+
- Node.js 18+
- npm or yarn
- FFmpeg (required by WhisperX)

### Install FFmpeg

**macOS:**

```bash
brew install ffmpeg
```

**Ubuntu/Debian:**

```bash
sudo apt update
sudo apt install ffmpeg
```

**Windows:**
Download from [ffmpeg.org](https://ffmpeg.org/download.html)

## Installation

### 1. Clone the Repository

```bash
cd rani-timestamps-generator
```

### 2. Backend Setup

```bash
# Create virtual environment
python -m venv venv

# Activate virtual environment
# On macOS/Linux:
source venv/bin/activate
# On Windows:
venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### 3. Frontend Setup

```bash
cd frontend

# Install dependencies
npm install

# Create environment file (optional)
cp .env.example .env
```

### 4. Ngrok Setup (Optional - for exposing local server)

If you want to expose your local development server to the internet:

1. **Get your ngrok authtoken**:

   - Sign up or log in at [ngrok.com](https://dashboard.ngrok.com/)
   - Get your authtoken from [https://dashboard.ngrok.com/get-started/your-authtoken](https://dashboard.ngrok.com/get-started/your-authtoken)

2. **Create environment file**:

   ```bash
   # From project root directory
   cp .env.example .env
   ```

3. **Add your authtoken to `.env`**:
   ```env
   NGROK_AUTHTOKEN=your_ngrok_authtoken_here
   ```

## Running the Application

### Start Backend Server

```bash
# From project root directory
# Make sure virtual environment is activated
python app.py
```

The backend will start on `http://localhost:5000`

### Start Frontend Development Server

```bash
# From frontend directory
npm run dev
```

The frontend will start on `http://localhost:3000`

## Usage

1. **Open the Application**: Navigate to `http://localhost:3000` in your browser

2. **Upload Audio File**:

   - Drag and drop an audio file, or click to browse
   - Supported formats: WAV, MP3, M4A, FLAC
   - Files under 100MB use direct upload
   - Files over 100MB use chunked upload with signed URLs

3. **Optional: Add Script Text**:

   - If you have a pre-written script, paste it in the text area
   - Format: `A: dialogue text` and `B: dialogue text`
   - Leave empty to process without a script

4. **Select Language**: Choose the primary language of the audio

5. **Process**: Click "Upload and Process Audio"

6. **View Results**:

   - See statistics (total segments, speaker breakdown, duration)
   - Search within transcripts
   - Filter by speaker
   - View detailed timestamps for each segment

7. **Download Results**:
   - JSON: Full structured data
   - CSV: Spreadsheet-compatible format
   - TXT: Human-readable transcript with timestamps

## API Endpoints

### Backend API

- `GET /api/health` - Health check
- `POST /api/init-upload` - Initialize chunked upload session
- `POST /api/upload/<file_id>` - Upload file chunks
- `POST /api/upload-direct` - Direct upload for smaller files
- `POST /api/process/<file_id>` - Process uploaded audio
- `GET /api/status/<file_id>` - Get processing status
- `GET /api/download/<file_id>` - Download results
- `DELETE /api/cleanup/<file_id>` - Cleanup uploaded files

## Configuration

### Backend Configuration

Edit [app.py](app.py:24) to modify:

```python
app.config['MAX_CONTENT_LENGTH'] = 500 * 1024 * 1024  # Max file size
app.config['SECRET_KEY'] = 'your-secret-key'  # Change in production
app.config['SIGNED_URL_EXPIRY'] = 3600  # URL expiry in seconds
```

### Frontend Configuration

Create `frontend/.env`:

```env
VITE_API_URL=http://localhost:5001/api
```

## Project Structure

```
rani-timestamps-generator/
├── app.py                      # Flask backend API
├── quick_mapper.py             # Core timestamp generation logic
├── requirements.txt            # Python dependencies
├── README.md                   # This file
├── .gitignore                  # Git ignore rules
│
└── frontend/                   # React frontend
    ├── src/
    │   ├── components/
    │   │   ├── FileUpload.jsx      # File upload component
    │   │   ├── ProgressBar.jsx     # Progress indicator
    │   │   └── ResultsDisplay.jsx  # Results viewer
    │   ├── services/
    │   │   └── api.js              # API client
    │   ├── utils/
    │   │   └── formatters.js       # Formatting utilities
    │   ├── App.jsx                 # Main application
    │   ├── main.jsx                # Entry point
    │   └── index.css               # Global styles
    ├── package.json
    ├── vite.config.js
    └── tailwind.config.js
```

## File Size Limits

- **Direct Upload**: Up to 100MB
- **Chunked Upload**: 100MB - 500MB
- **Chunk Size**: 5MB per chunk

For larger files, modify `MAX_CONTENT_LENGTH` in [app.py](app.py:24) and `CHUNK_SIZE` in [frontend/src/services/api.js](frontend/src/services/api.js).

## Deployment

### Backend Deployment

For production deployment:

1. Set a secure `SECRET_KEY` environment variable
2. Use a production WSGI server (e.g., Gunicorn):
   ```bash
   pip install gunicorn
   gunicorn -w 4 -b 0.0.0.0:5000 app:app
   ```
3. Configure CORS for your production domain
4. Set up proper file storage (e.g., S3) for uploaded files

### Frontend Deployment

1. Build the production bundle:

   ```bash
   cd frontend
   npm run build
   ```

2. Deploy the `frontend/dist` folder to your hosting service (Vercel, Netlify, etc.)

3. Update `VITE_API_URL` to point to your production backend

## Troubleshooting

### Backend Issues

**WhisperX not found:**

```bash
pip install whisperx --upgrade
```

**FFmpeg errors:**

```bash
# Verify FFmpeg installation
ffmpeg -version
```

**Port already in use:**

```python
# Change port in app.py
app.run(debug=True, host='0.0.0.0', port=5001)
```

### Frontend Issues

**API connection errors:**

- Ensure backend is running on port 5000
- Check CORS configuration in [app.py](app.py)
- Verify `VITE_API_URL` in `.env`

**Build errors:**

```bash
# Clear cache and reinstall
rm -rf node_modules package-lock.json
npm install
```

## Technologies Used

### Backend

- Flask - Web framework
- WhisperX - Audio transcription and alignment
- librosa - Audio processing
- Flask-CORS - Cross-origin resource sharing

### Frontend

- React 18 - UI framework
- Vite - Build tool
- Tailwind CSS - Styling
- Axios - HTTP client
- Lucide React - Icons
