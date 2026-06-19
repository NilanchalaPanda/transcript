import React, { useState, useEffect } from 'react';
import { AlertCircle, CheckCircle, Loader, Radio } from 'lucide-react';
import FileUpload from './components/FileUpload';
import ProgressBar from './components/ProgressBar';
import ResultsDisplay from './components/ResultsDisplay';
import {
  initializeUpload,
  uploadFileChunked,
  uploadFileDirect,
  processAudio,
  getStatus,
} from './services/api';

function App() {
  const [selectedFile, setSelectedFile] = useState(null);
  const [uploadProgress, setUploadProgress] = useState(0);
  const [processingStatus, setProcessingStatus] = useState('idle'); // idle, uploading, processing, completed, error
  const [fileId, setFileId] = useState(null);
  const [timestamps, setTimestamps] = useState([]);
  const [error, setError] = useState(null);
  const [scriptText, setScriptText] = useState('');
  const [language, setLanguage] = useState('hi');
  const [numSpeakers, setNumSpeakers] = useState(2);
  const [hasTranscript, setHasTranscript] = useState(false);
  const [pollingInterval, setPollingInterval] = useState(null);

  const FILE_SIZE_THRESHOLD = 100 * 1024 * 1024; // 100MB

  // Debug: Log status changes
  useEffect(() => {
    console.log('🔄 Processing Status Changed:', processingStatus);
    console.log('📝 Timestamps count:', timestamps.length);
  }, [processingStatus, timestamps]);

  // Poll for status updates when processing
  useEffect(() => {
    if (processingStatus === 'processing' && fileId) {
      console.log('🔄 Starting status polling for fileId:', fileId);

      const interval = setInterval(async () => {
        try {
          console.log('🔍 Polling status...');
          const statusData = await getStatus(fileId);

          if (statusData.status === 'completed') {
            console.log('✅ Status poll detected completion!');
            setTimestamps(statusData.timestamps || []);
            setHasTranscript(!!statusData.transcript_download_url);
            setProcessingStatus('completed');
            clearInterval(interval);
          } else if (statusData.status === 'failed') {
            console.error('❌ Status poll detected failure');
            setError('Processing failed');
            setProcessingStatus('error');
            clearInterval(interval);
          }
        } catch (err) {
          console.error('⚠️ Error polling status:', err);
          // Don't clear interval on poll errors, keep trying
        }
      }, 5000); // Poll every 5 seconds

      setPollingInterval(interval);

      return () => {
        console.log('🛑 Clearing status polling interval');
        clearInterval(interval);
      };
    }
  }, [processingStatus, fileId]);

  const handleFileSelect = (file) => {
    setSelectedFile(file);
    setError(null);
    setTimestamps([]);
    setProcessingStatus('idle');
    setUploadProgress(0);
  };

  const handleUploadAndProcess = async () => {
    if (!selectedFile) {
      setError('Please select an audio file first');
      return;
    }

    try {
      setError(null);
      setProcessingStatus('uploading');
      setUploadProgress(0);

      let uploadedFileId;

      // Choose upload method based on file size
      if (selectedFile.size > FILE_SIZE_THRESHOLD) {
        // Large file: use chunked upload with signed URL
        console.log('Using chunked upload for large file');
        const initData = await initializeUpload(selectedFile.name, selectedFile.size);
        uploadedFileId = initData.file_id;

        await uploadFileChunked(
          selectedFile,
          uploadedFileId,
          initData.signed_url,
          (progress) => {
            setUploadProgress(progress);
          }
        );
      } else {
        // Small file: use direct upload
        console.log('Using direct upload for small file');
        const uploadData = await uploadFileDirect(selectedFile, (progress) => {
          setUploadProgress(progress);
        });
        uploadedFileId = uploadData.file_id;
      }

      setFileId(uploadedFileId);
      setUploadProgress(100);

      // Start processing
      console.log('Starting audio processing...');
      setProcessingStatus('processing');

      try {
        const result = await processAudio(uploadedFileId, scriptText, language, numSpeakers);

        console.log('✅ Received result from API:', result);

        // Handle 202 Accepted - processing started in background
        if (result.success && result.status === 'processing') {
          console.log('🔄 Processing started in background, polling will detect completion');
          // Keep processingStatus as 'processing', polling will update when done
          return;
        }

        // Handle immediate success (if backend returns results immediately)
        if (result.success && result.timestamps) {
          console.log(`📊 Setting ${result.timestamps.length} timestamps`);
          setTimestamps(result.timestamps);
          setHasTranscript(!!result.transcript_download_url);
          setProcessingStatus('completed');
          console.log(`✅ Processing completed: ${result.timestamps.length} segments`);
          console.log('🎯 Status set to: completed');
          if (result.transcript_download_url) {
            console.log('📄 WhisperX transcript available for download');
          }
        } else if (!result.success) {
          throw new Error(result.error || 'Processing failed');
        }
      } catch (processError) {
        // Handle 409 Conflict - file already being processed (ignore duplicate request)
        if (processError.response?.status === 409) {
          console.warn('⚠️ File is already being processed (duplicate request ignored)');
          // Keep the processing status, this is just a race condition
          // The polling mechanism will detect completion
          return;
        }

        // Handle 503 Service Unavailable from ngrok timeout
        if (processError.response?.status === 503) {
          console.warn('⚠️ Ngrok timeout detected (normal for long processing)');
          console.warn('⚠️ Processing continues on server. Polling will detect completion...');
          // Keep the processing status, polling will handle completion detection
          return;
        }

        // If we get a timeout or network error, it might still be processing
        if (processError.code === 'ECONNABORTED' || processError.message.includes('timeout')) {
          console.warn('⚠️ Request timed out, but processing may still be running on server');
          console.warn('⚠️ This is normal for very large files. Polling will detect completion...');
          // Keep the processing status, polling will handle completion detection
          return;
        } else {
          throw processError;
        }
      }
    } catch (err) {
      console.error('❌ Error:', err);
      console.error('❌ Error response:', err.response);
      console.error('❌ Error data:', err.response?.data);
      const errorMessage = err.response?.data?.error || err.message || 'An error occurred';
      console.error('❌ Final error message:', errorMessage);
      setError(errorMessage);
      setProcessingStatus('error');
    }
  };

  const handleReset = () => {
    setSelectedFile(null);
    setUploadProgress(0);
    setProcessingStatus('idle');
    setFileId(null);
    setTimestamps([]);
    setError(null);
    setScriptText('');
    setHasTranscript(false);
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 via-white to-purple-50">
      <div className="container mx-auto px-4 py-8 max-w-6xl">
        {/* Header */}
        <div className="text-center mb-8">
          <div className="flex items-center justify-center mb-4">
            <Radio className="h-12 w-12 text-blue-600 mr-3" />
            <h1 className="text-4xl font-bold text-gray-900">
              Audio Timestamp Generator
            </h1>
          </div>
          <p className="text-gray-600 text-lg">
            Upload your audio file and get accurate timestamps with speaker diarization
          </p>
        </div>

        {/* Main Content */}
        <div className="bg-white rounded-xl shadow-lg p-8">
          {processingStatus === 'idle' || processingStatus === 'error' ? (
            <div className="space-y-6">
              {/* File Upload */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Audio File
                </label>
                <FileUpload onFileSelect={handleFileSelect} />
              </div>

              {/* Optional Script Input */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Script Text
                </label>
                <textarea
                  value={scriptText}
                  onChange={(e) => setScriptText(e.target.value)}
                  placeholder="A: First dialogue&#10;B: Second dialogue&#10;A: Third dialogue..."
                  className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent resize-none"
                  rows={6}
                />
              </div>

              {/* Language and Speaker Selection */}
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Language
                  </label>
                  <select
                    value={language}
                    onChange={(e) => setLanguage(e.target.value)}
                    className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                  >
                    <option value="hi">Hindi</option>
                    <option value="en">English</option>
                    <option value="es">Spanish</option>
                    <option value="fr">French</option>
                    <option value="de">German</option>
                    <option value="zh">Chinese</option>
                    <option value="ja">Japanese</option>
                    <option value="ko">Korean</option>
                  </select>
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Number of Speakers
                  </label>
                  <select
                    value={numSpeakers}
                    onChange={(e) => setNumSpeakers(parseInt(e.target.value))}
                    className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                  >
                    <option value="2">2 Speakers</option>
                    <option value="3">3 Speakers</option>
                    <option value="4">4 Speakers</option>
                    <option value="5">5 Speakers</option>
                  </select>
                </div>
              </div>

              {/* Error Display */}
              {error && (
                <div className="flex items-start space-x-3 p-4 bg-red-50 border border-red-200 rounded-lg">
                  <AlertCircle className="h-5 w-5 text-red-600 flex-shrink-0 mt-0.5" />
                  <div className="flex-1">
                    <p className="text-sm font-medium text-red-800">Error</p>
                    <p className="text-sm text-red-700 mt-1">{error}</p>
                  </div>
                </div>
              )}

              {/* Process Button */}
              <button
                onClick={handleUploadAndProcess}
                disabled={!selectedFile}
                className="w-full py-3 px-6 bg-blue-600 text-white font-medium rounded-lg hover:bg-blue-700 disabled:bg-gray-300 disabled:cursor-not-allowed transition-colors"
              >
                {selectedFile
                  ? 'Upload and Process Audio'
                  : 'Select an Audio File First'}
              </button>

              {/* File Size Info */}
              {selectedFile && selectedFile.size > FILE_SIZE_THRESHOLD && (
                <div className="flex items-start space-x-3 p-4 bg-blue-50 border border-blue-200 rounded-lg">
                  <AlertCircle className="h-5 w-5 text-blue-600 flex-shrink-0 mt-0.5" />
                  <div className="flex-1">
                    <p className="text-sm font-medium text-blue-800">Large File Detected</p>
                    <p className="text-sm text-blue-700 mt-1">
                      This file will be uploaded using chunked transfer for reliability.
                    </p>
                  </div>
                </div>
              )}
            </div>
          ) : processingStatus === 'uploading' ? (
            <div className="space-y-6 py-8">
              <div className="text-center">
                <Loader className="h-16 w-16 text-blue-600 mx-auto mb-4 animate-spin" />
                <h2 className="text-2xl font-semibold text-gray-900 mb-2">
                  Uploading Audio File
                </h2>
                <p className="text-gray-600">
                  Please wait while we upload your file...
                </p>
              </div>
              <ProgressBar
                progress={uploadProgress}
                label="Upload Progress"
                status="uploading"
              />
            </div>
          ) : processingStatus === 'processing' ? (
            <div className="space-y-6 py-8">
              <div className="text-center">
                <Loader className="h-16 w-16 text-purple-600 mx-auto mb-4 animate-spin" />
                <h2 className="text-2xl font-semibold text-gray-900 mb-2">
                  Processing Audio
                </h2>
                <p className="text-gray-600">
                  Generating timestamps and transcripts... This may take a few minutes.
                </p>
                {pollingInterval && (
                  <p className="text-sm text-purple-600 mt-2">
                    Checking for updates every 5 seconds...
                  </p>
                )}
              </div>
              <div className="bg-purple-50 border border-purple-200 rounded-lg p-4">
                <div className="flex items-center justify-center space-x-2">
                  <div className="h-2 w-2 bg-purple-600 rounded-full animate-bounce" style={{ animationDelay: '0ms' }}></div>
                  <div className="h-2 w-2 bg-purple-600 rounded-full animate-bounce" style={{ animationDelay: '150ms' }}></div>
                  <div className="h-2 w-2 bg-purple-600 rounded-full animate-bounce" style={{ animationDelay: '300ms' }}></div>
                </div>
              </div>
            </div>
          ) : processingStatus === 'completed' ? (
            <div className="space-y-6">
              <div className="flex items-center justify-between p-4 bg-green-50 border border-green-200 rounded-lg">
                <div className="flex items-center space-x-3">
                  <CheckCircle className="h-6 w-6 text-green-600" />
                  <div>
                    <p className="text-sm font-medium text-green-800">
                      Processing Completed Successfully
                    </p>
                    <p className="text-sm text-green-700">
                      {timestamps.length} dialogue segments generated
                    </p>
                  </div>
                </div>
                <button
                  onClick={handleReset}
                  className="px-4 py-2 bg-white border border-gray-300 text-gray-700 rounded-lg hover:bg-gray-50 transition-colors"
                >
                  Process Another File
                </button>
              </div>

              <ResultsDisplay timestamps={timestamps} fileId={fileId} hasTranscript={hasTranscript} />
            </div>
          ) : null}
        </div>

        {/* Footer */}
        <div className="mt-8 text-center text-sm text-gray-500">
          <p>Powered by WhisperX and React</p>
        </div>
      </div>
    </div>
  );
}

export default App;
