"""
Flask Backend API for Audio Timestamp Generator
Supports large file uploads using signed URLs and chunked uploads
"""

from flask import Flask, request, jsonify, send_file, url_for
from flask_cors import CORS
from werkzeug.utils import secure_filename
from dotenv import load_dotenv
import os
import json
import uuid
import tempfile
from pathlib import Path
from datetime import datetime, timedelta
import hashlib
import hmac
from quick_mapper import map_dialogue_timestamps
from auto_transcribe_mapper import transcribe_and_map_timestamps
import logging
import threading

load_dotenv()

app = Flask(__name__)
CORS(app)

# Configuration
app.config['MAX_CONTENT_LENGTH'] = 1000 * 1024 * 1024  # 1000MB max file size
app.config['UPLOAD_FOLDER'] = tempfile.gettempdir() + '/audio_uploads'
app.config['OUTPUT_FOLDER'] = tempfile.gettempdir() + '/audio_outputs'
app.config['SECRET_KEY'] = os.environ["SECRET_KEY"]
app.config['SIGNED_URL_EXPIRY'] = 3600  # 1 hour

# Ensure folders exist
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs(app.config['OUTPUT_FOLDER'], exist_ok=True)

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Store for upload sessions
upload_sessions = {}

def generate_signed_url(file_id, expiry_minutes=60):
    """Generate a signed URL for secure file upload"""
    expires_at = datetime.utcnow() + timedelta(minutes=expiry_minutes)
    expires_timestamp = int(expires_at.timestamp())

    # Create signature
    message = f"{file_id}:{expires_timestamp}"
    signature = hmac.new(
        app.config['SECRET_KEY'].encode(),
        message.encode(),
        hashlib.sha256
    ).hexdigest()

    return {
        'file_id': file_id,
        'expires_at': expires_timestamp,
        'signature': signature,
        'upload_url': f'/api/upload/{file_id}'
    }

def verify_signed_url(file_id, expires_at, signature):
    """Verify a signed URL"""
    if datetime.utcnow().timestamp() > expires_at:
        return False

    message = f"{file_id}:{expires_at}"
    expected_signature = hmac.new(
        app.config['SECRET_KEY'].encode(),
        message.encode(),
        hashlib.sha256
    ).hexdigest()

    return hmac.compare_digest(signature, expected_signature)

def cleanup_session(file_id):
    """Delete all files and session data"""

    try:
        if file_id not in upload_sessions:
            return

        session = upload_sessions[file_id]

        if 'file_path' in session and os.path.exists(session['file_path']):
            os.remove(session['file_path'])

        if 'output_path' in session and os.path.exists(session['output_path']):
            os.remove(session['output_path'])

        if 'transcript_path' in session and os.path.exists(session['transcript_path']):
            os.remove(session['transcript_path'])

        del upload_sessions[file_id]

        logger.info(f"🧹 Auto-cleaned session: {file_id}")

    except Exception as e:
        logger.error(f"Cleanup failed: {e}")

def process_audio_background(file_id, script_text, language, num_speakers):
    """Background processing function that runs in a separate thread"""
    try:
        session = upload_sessions[file_id]
        audio_path = session['file_path']
        output_json_path = os.path.join(app.config['OUTPUT_FOLDER'], f"{file_id}_timestamps.json")

        logger.info(f"🎬 Background processing started for: {audio_path}")

        # Choose processing method based on whether script is provided
        if script_text:
            # User provided script - use forced alignment
            logger.info("Using forced alignment with provided script")
            script_path = os.path.join(app.config['UPLOAD_FOLDER'], f"{file_id}_script.txt")
            with open(script_path, 'w', encoding='utf-8') as f:
                f.write(script_text)

            result = map_dialogue_timestamps(
                script_path=script_path,
                merged_audio_path=audio_path,
                output_json_path=output_json_path,
                language=language,
                save_transcript=True
            )
        else:
            # No script - use automatic transcription + speaker diarization
            logger.info("Using automatic transcription and speaker diarization")
            result = transcribe_and_map_timestamps(
                audio_path=audio_path,
                output_json_path=output_json_path,
                language=language,
                num_speakers=num_speakers
            )

        if result is None:
            session['status'] = 'failed'
            session['error'] = 'Processing failed. Check backend logs for details.'
            logger.error(f"❌ Background processing failed for {file_id}")
            return

        # Handle different result formats (dict from forced alignment, list from auto transcription)
        if isinstance(result, dict):
            timestamps = result.get('timestamps', [])
            transcript_path = result.get('transcript_path')
        else:
            timestamps = result
            transcript_path = None

        # Update session with results
        session['status'] = 'completed'
        
        # Automatic Cleanup config
        threading.Timer(1800, cleanup_session, args=[file_id]).start()
        
        session['output_path'] = output_json_path
        session['results'] = timestamps
        if transcript_path:
            session['transcript_path'] = transcript_path

        logger.info(f"✅ Background processing completed: {len(timestamps)} timestamps generated for {file_id}")

    except Exception as e:
        logger.error(f"❌ Error in background processing for {file_id}: {e}")
        if file_id in upload_sessions:
            upload_sessions[file_id]['status'] = 'failed'
            upload_sessions[file_id]['error'] = str(e)

@app.route('/api/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({'status': 'healthy', 'message': 'Audio Timestamp Generator API is running'}), 200

@app.route('/api/init-upload', methods=['POST'])
def init_upload():
    """Initialize an upload session and return signed URL"""
    try:
        data = request.json
        filename = secure_filename(data.get('filename', 'audio.wav'))
        file_size = data.get('file_size', 0)

        # Generate unique file ID
        file_id = str(uuid.uuid4())

        # Create upload session
        upload_sessions[file_id] = {
            'filename': filename,
            'file_size': file_size,
            'created_at': datetime.utcnow(),
            'status': 'initialized',
            'chunks_received': []
        }

        # Generate signed URL
        signed_url_data = generate_signed_url(file_id)

        logger.info(f"Upload session initialized: {file_id} for file {filename}")

        return jsonify({
            'success': True,
            'file_id': file_id,
            'signed_url': signed_url_data
        }), 200

    except Exception as e:
        logger.error(f"Error initializing upload: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/upload/<file_id>', methods=['POST'])
def upload_file(file_id):
    """Handle chunked file upload"""
    try:
        # Verify signed URL parameters
        expires_at = int(request.headers.get('X-Expires-At', 0))
        signature = request.headers.get('X-Signature', '')

        if not verify_signed_url(file_id, expires_at, signature):
            return jsonify({'success': False, 'error': 'Invalid or expired upload URL'}), 403

        # Check if session exists
        if file_id not in upload_sessions:
            return jsonify({'success': False, 'error': 'Upload session not found'}), 404

        session = upload_sessions[file_id]

        # Handle chunked upload
        chunk_index = int(request.headers.get('X-Chunk-Index', 0))
        total_chunks = int(request.headers.get('X-Total-Chunks', 1))

        # Save chunk
        chunk_data = request.data
        chunk_path = os.path.join(app.config['UPLOAD_FOLDER'], f"{file_id}_chunk_{chunk_index}")

        with open(chunk_path, 'wb') as f:
            f.write(chunk_data)

        session['chunks_received'].append(chunk_index)
        logger.info(f"Received chunk {chunk_index + 1}/{total_chunks} for {file_id}")

        # Check if all chunks received
        if len(session['chunks_received']) == total_chunks:
            # Merge chunks
            final_path = os.path.join(app.config['UPLOAD_FOLDER'], f"{file_id}_{session['filename']}")

            with open(final_path, 'wb') as outfile:
                for i in range(total_chunks):
                    chunk_path = os.path.join(app.config['UPLOAD_FOLDER'], f"{file_id}_chunk_{i}")
                    with open(chunk_path, 'rb') as infile:
                        outfile.write(infile.read())
                    os.remove(chunk_path)  # Clean up chunk

            session['status'] = 'uploaded'
            session['file_path'] = final_path
            logger.info(f"File upload completed: {final_path}")

            return jsonify({
                'success': True,
                'message': 'Upload complete',
                'file_id': file_id,
                'ready_for_processing': True
            }), 200
        else:
            return jsonify({
                'success': True,
                'message': f'Chunk {chunk_index + 1}/{total_chunks} received',
                'chunks_received': len(session['chunks_received']),
                'total_chunks': total_chunks
            }), 200

    except Exception as e:
        logger.error(f"Error uploading file: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/upload-direct', methods=['POST'])
def upload_direct():
    """Direct upload for smaller files (< 100MB)"""
    try:
        if 'file' not in request.files:
            return jsonify({'success': False, 'error': 'No file provided'}), 400

        file = request.files['file']
        if file.filename == '':
            return jsonify({'success': False, 'error': 'No file selected'}), 400

        # Generate unique file ID
        file_id = str(uuid.uuid4())
        filename = secure_filename(file.filename)
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], f"{file_id}_{filename}")

        # Save file
        file.save(file_path)

        # Create session
        upload_sessions[file_id] = {
            'filename': filename,
            'file_path': file_path,
            'created_at': datetime.utcnow(),
            'status': 'uploaded'
        }

        logger.info(f"Direct upload completed: {file_path}")

        return jsonify({
            'success': True,
            'file_id': file_id,
            'message': 'File uploaded successfully',
            'ready_for_processing': True
        }), 200

    except Exception as e:
        logger.error(f"Error in direct upload: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/process/<file_id>', methods=['POST'])
def process_audio(file_id):
    """Process uploaded audio file to generate timestamps"""
    try:
        logger.info(f"🎬 PROCESS REQUEST RECEIVED for file_id: {file_id}")

        # Check if session exists
        if file_id not in upload_sessions:
            logger.error(f"❌ File not found: {file_id}")
            return jsonify({'success': False, 'error': 'File not found'}), 404

        session = upload_sessions[file_id]
        logger.info(f"📊 Current session status: {session['status']}")

        # If already processing, return a "processing in progress" response instead of error
        if session['status'] == 'processing':
            logger.warning(f"⚠️ File is already being processed. Returning processing status.")
            return jsonify({
                'success': False,
                'error': 'File is already being processed',
                'status': 'processing'
            }), 409  # 409 Conflict - indicates request conflicts with current state

        # If already completed, return the cached results
        if session['status'] == 'completed':
            logger.info(f"✅ File already processed. Returning cached results.")
            timestamps = session.get('results', [])
            response_data = {
                'success': True,
                'file_id': file_id,
                'message': f'Successfully processed {len(timestamps)} dialogue segments',
                'timestamps': timestamps,
                'download_url': f'/api/download/{file_id}'
            }
            if 'transcript_path' in session:
                response_data['transcript_download_url'] = f'/api/download-transcript/{file_id}'
            return jsonify(response_data), 200

        if session['status'] != 'uploaded':
            logger.error(f"❌ File not ready for processing. Status is: {session['status']} (expected: 'uploaded')")
            return jsonify({'success': False, 'error': 'File not ready for processing'}), 400

        # Get processing parameters
        data = request.json or {}
        script_text = data.get('script_text', '')
        language = data.get('language', 'hi')
        num_speakers = data.get('num_speakers', 2)

        # Update session status
        session['status'] = 'processing'
        logger.info(f"🚀 Starting background processing for {file_id}")

        # Start background processing in a separate thread
        thread = threading.Thread(
            target=process_audio_background,
            args=(file_id, script_text, language, num_speakers),
            daemon=True
        )
        thread.start()

        # Return immediately - client will poll for status
        return jsonify({
            'success': True,
            'file_id': file_id,
            'message': 'Processing started. Use /api/status endpoint to check progress.',
            'status': 'processing'
        }), 202  # 202 Accepted - request accepted for processing

    except Exception as e:
        logger.error(f"Error processing audio: {e}")
        if file_id in upload_sessions:
            upload_sessions[file_id]['status'] = 'failed'
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/status/<file_id>', methods=['GET'])
def get_status(file_id):
    """Get processing status for a file"""
    try:
        if file_id not in upload_sessions:
            return jsonify({'success': False, 'error': 'File not found'}), 404

        session = upload_sessions[file_id]

        response = {
            'success': True,
            'file_id': file_id,
            'status': session['status'],
            'filename': session['filename']
        }

        if session['status'] == 'completed':
            response['timestamps'] = session.get('results', [])
            response['download_url'] = f'/api/download/{file_id}'
            if 'transcript_path' in session:
                response['transcript_download_url'] = f'/api/download-transcript/{file_id}'

        return jsonify(response), 200

    except Exception as e:
        logger.error(f"Error getting status: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/download/<file_id>', methods=['GET'])
def download_results(file_id):
    """Download the generated timestamps JSON"""
    try:
        if file_id not in upload_sessions:
            return jsonify({'success': False, 'error': 'File not found'}), 404

        session = upload_sessions[file_id]

        if session['status'] != 'completed':
            return jsonify({'success': False, 'error': 'Results not available'}), 400

        output_path = session.get('output_path')
        if not output_path or not os.path.exists(output_path):
            return jsonify({'success': False, 'error': 'Output file not found'}), 404

        return send_file(
            output_path,
            mimetype='application/json',
            as_attachment=True,
            download_name=f'timestamps_{file_id}.json'
        )

    except Exception as e:
        logger.error(f"Error downloading results: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/download-transcript/<file_id>', methods=['GET'])
def download_transcript(file_id):
    """Download the WhisperX-generated transcript JSON"""
    try:
        if file_id not in upload_sessions:
            return jsonify({'success': False, 'error': 'File not found'}), 404

        session = upload_sessions[file_id]

        if session['status'] != 'completed':
            return jsonify({'success': False, 'error': 'Results not available'}), 400

        transcript_path = session.get('transcript_path')
        if not transcript_path or not os.path.exists(transcript_path):
            return jsonify({'success': False, 'error': 'Transcript file not found'}), 404

        return send_file(
            transcript_path,
            mimetype='application/json',
            as_attachment=True,
            download_name=f'transcript_{file_id}.json'
        )

    except Exception as e:
        logger.error(f"Error downloading transcript: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/cleanup/<file_id>', methods=['DELETE'])
def cleanup(file_id):
    """Clean up uploaded files and results"""
    try:
        if file_id not in upload_sessions:
            return jsonify({'success': False, 'error': 'File not found'}), 404

        session = upload_sessions[file_id]

        # Delete files
        if 'file_path' in session and os.path.exists(session['file_path']):
            os.remove(session['file_path'])

        if 'output_path' in session and os.path.exists(session['output_path']):
            os.remove(session['output_path'])

        if 'transcript_path' in session and os.path.exists(session['transcript_path']):
            os.remove(session['transcript_path'])

        # Remove session
        del upload_sessions[file_id]

        logger.info(f"Cleaned up session: {file_id}")

        return jsonify({'success': True, 'message': 'Files cleaned up successfully'}), 200

    except Exception as e:
        logger.error(f"Error cleaning up: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

if __name__ == '__main__':
    print("=" * 60)
    print("🚀 Audio Timestamp Generator API Server")
    print("=" * 60)
    print(f"📁 Upload folder: {app.config['UPLOAD_FOLDER']}")
    print(f"📁 Output folder: {app.config['OUTPUT_FOLDER']}")
    print(f"🌐 Starting server on http://localhost:5001")
    print("=" * 60)
    
    app.run(debug=True, host='0.0.0.0', port=5001)