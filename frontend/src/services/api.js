// import axios from 'axios';

// // When deployed via ngrok with nginx, use same host
// // For local development, check if we're accessing through nginx (port 8080) or directly
// const API_BASE_URL = import.meta.env.VITE_API_URL ||
//   (window.location.port === '8080' || window.location.hostname.includes('ngrok')
//     ? `${window.location.protocol}//${window.location.host}/api`
//     : 'http://localhost:5001/api');

// // Log API URL for debugging
// console.log('🔧 API Base URL:', API_BASE_URL);
// console.log('🌐 Current Location:', {
//   protocol: window.location.protocol,
//   hostname: window.location.hostname,
//   port: window.location.port,
//   host: window.location.host
// });

// const api = axios.create({
//   baseURL: API_BASE_URL,
//   timeout: 3600000, // 60 minutes (1 hour) for very large file processing
// });

// /**
//  * Initialize a file upload session
//  */
// export const initializeUpload = async (filename, fileSize) => {
//   const response = await api.post('/init-upload', {
//     filename,
//     file_size: fileSize,
//   });
//   return response.data;
// };

// /**
//  * Upload file in chunks using signed URL
//  */
// export const uploadFileChunked = async (file, fileId, signedUrlData, onProgress) => {
//   const CHUNK_SIZE = 5 * 1024 * 1024; // 5MB chunks
//   const totalChunks = Math.ceil(file.size / CHUNK_SIZE);

//   let lastResponse;

//   for (let chunkIndex = 0; chunkIndex < totalChunks; chunkIndex++) {
//     const start = chunkIndex * CHUNK_SIZE;
//     const end = Math.min(start + CHUNK_SIZE, file.size);
//     const chunk = file.slice(start, end);

//     console.log(`📤 Uploading chunk ${chunkIndex + 1}/${totalChunks}`);

//     const response = await api.post(`/upload/${fileId}`, chunk, {
//       headers: {
//         'Content-Type': 'application/octet-stream',
//         'X-Chunk-Index': chunkIndex,
//         'X-Total-Chunks': totalChunks,
//         'X-Expires-At': signedUrlData.expires_at,
//         'X-Signature': signedUrlData.signature,
//       },
//     });

//     lastResponse = response.data;
//     console.log(`✅ Chunk ${chunkIndex + 1}/${totalChunks} uploaded:`, lastResponse);

//     if (onProgress) {
//       const progress = ((chunkIndex + 1) / totalChunks) * 100;
//       onProgress(progress);
//     }
//   }

//   // Verify upload is complete and ready for processing
//   if (!lastResponse || !lastResponse.ready_for_processing) {
//     throw new Error('Upload completed but file is not ready for processing');
//   }

//   console.log('✅ All chunks uploaded and merged successfully');
//   return lastResponse;
// };

// /**
//  * Direct upload for smaller files
//  */
// export const uploadFileDirect = async (file, onProgress) => {
//   const formData = new FormData();
//   formData.append('file', file);

//   const response = await api.post('/upload-direct', formData, {
//     headers: {
//       'Content-Type': 'multipart/form-data',
//     },
//     onUploadProgress: (progressEvent) => {
//       if (onProgress && progressEvent.total) {
//         const progress = (progressEvent.loaded / progressEvent.total) * 100;
//         onProgress(progress);
//       }
//     },
//   });

//   return response.data;
// };

// /**
//  * Process uploaded audio file
//  */
// export const processAudio = async (fileId, scriptText = '', language = 'hi', numSpeakers = 2) => {
//   console.log('🎬 processAudio() called with fileId:', fileId);
//   console.log('📋 Script text length:', scriptText.length);
//   console.log('🌍 Language:', language);
//   console.log('🎤 Num speakers:', numSpeakers);

//   const response = await api.post(`/process/${fileId}`, {
//     script_text: scriptText,
//     language,
//     num_speakers: numSpeakers,
//   });

//   console.log('✅ processAudio() response received:', response.data);
//   return response.data;
// };

// /**
//  * Get processing status
//  */
// export const getStatus = async (fileId) => {
//   const response = await api.get(`/status/${fileId}`);
//   return response.data;
// };

// /**
//  * Download results
//  */
// export const downloadResults = async (fileId) => {
//   const response = await api.get(`/download/${fileId}`, {
//     responseType: 'blob',
//   });
//   return response.data;
// };

// /**
//  * Download WhisperX transcript
//  */
// export const downloadTranscript = async (fileId) => {
//   const response = await api.get(`/download-transcript/${fileId}`, {
//     responseType: 'blob',
//   });
//   return response.data;
// };

// /**
//  * Cleanup files
//  */
// export const cleanupFiles = async (fileId) => {
//   const response = await api.delete(`/cleanup/${fileId}`);
//   return response.data;
// };

// /**
//  * Health check
//  */
// export const healthCheck = async () => {
//   const response = await api.get('/health');
//   return response.data;
// };

// export default api;

import axios from "axios";

const API_BASE_URL =
  import.meta.env.VITE_API_URL || "http://localhost:5001/api";

console.log("🔧 API Base URL:", API_BASE_URL);

const api = axios.create({
  baseURL: API_BASE_URL,
  timeout: 3600000,
});

export const initializeUpload = async (filename, fileSize) => {
  const response = await api.post("/init-upload", {
    filename,
    file_size: fileSize,
  });
  return response.data;
};

export const uploadFileChunked = async (
  file,
  fileId,
  signedUrlData,
  onProgress,
) => {
  const CHUNK_SIZE = 5 * 1024 * 1024;
  const totalChunks = Math.ceil(file.size / CHUNK_SIZE);

  let lastResponse;

  for (let chunkIndex = 0; chunkIndex < totalChunks; chunkIndex++) {
    const start = chunkIndex * CHUNK_SIZE;
    const end = Math.min(start + CHUNK_SIZE, file.size);

    const chunk = file.slice(start, end);

    const response = await api.post(`/upload/${fileId}`, chunk, {
      headers: {
        "Content-Type": "application/octet-stream",
        "X-Chunk-Index": chunkIndex,
        "X-Total-Chunks": totalChunks,
        "X-Expires-At": signedUrlData.expires_at,
        "X-Signature": signedUrlData.signature,
      },
    });

    lastResponse = response.data;

    if (onProgress) {
      onProgress(((chunkIndex + 1) / totalChunks) * 100);
    }
  }

  if (!lastResponse?.ready_for_processing) {
    throw new Error("Upload completed but file is not ready for processing");
  }

  return lastResponse;
};

export const uploadFileDirect = async (file, onProgress) => {
  const formData = new FormData();
  formData.append("file", file);

  const response = await api.post("/upload-direct", formData, {
    headers: {
      "Content-Type": "multipart/form-data",
    },
    onUploadProgress: (event) => {
      if (onProgress && event.total) {
        onProgress((event.loaded / event.total) * 100);
      }
    },
  });

  return response.data;
};

export const processAudio = async (
  fileId,
  scriptText = "",
  language = "hi",
  numSpeakers = 2,
) => {
  const response = await api.post(`/process/${fileId}`, {
    script_text: scriptText,
    language,
    num_speakers: numSpeakers,
  });

  return response.data;
};

export const getStatus = async (fileId) => {
  const response = await api.get(`/status/${fileId}`);
  return response.data;
};

export const downloadResults = async (fileId) => {
  const response = await api.get(`/download/${fileId}`, {
    responseType: "blob",
  });

  return response.data;
};

export const downloadTranscript = async (fileId) => {
  const response = await api.get(`/download-transcript/${fileId}`, {
    responseType: "blob",
  });

  return response.data;
};

export const cleanupFiles = async (fileId) => {
  const response = await api.delete(`/cleanup/${fileId}`);
  return response.data;
};

export const healthCheck = async () => {
  const response = await api.get("/health");
  return response.data;
};

export default api;
