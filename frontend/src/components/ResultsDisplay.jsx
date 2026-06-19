import React, { useState } from 'react';
import { Download, FileJson, FileText, FileSpreadsheet, Search, FileCode } from 'lucide-react';
import { formatTime, downloadJSON, downloadCSV, downloadTXT } from '../utils/formatters';
import { downloadTranscript } from '../services/api';

const ResultsDisplay = ({ timestamps, fileId, hasTranscript }) => {
  const [searchTerm, setSearchTerm] = useState('');
  const [filterSpeaker, setFilterSpeaker] = useState('all');

  const filteredTimestamps = timestamps.filter(item => {
    const matchesSearch = item.text.toLowerCase().includes(searchTerm.toLowerCase());
    const matchesSpeaker = filterSpeaker === 'all' || item.speaker === filterSpeaker;
    return matchesSearch && matchesSpeaker;
  });

  const handleDownload = (format) => {
    const filename = `timestamps_${fileId}`;
    switch (format) {
      case 'json':
        downloadJSON(timestamps, `${filename}.json`);
        break;
      case 'csv':
        downloadCSV(timestamps, `${filename}.csv`);
        break;
      case 'txt':
        downloadTXT(timestamps, `${filename}.txt`);
        break;
      default:
        break;
    }
  };

  const handleDownloadTranscript = async () => {
    try {
      const blob = await downloadTranscript(fileId);
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = `transcript_${fileId}.json`;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      window.URL.revokeObjectURL(url);
    } catch (error) {
      console.error('Error downloading transcript:', error);
      alert('Failed to download transcript. Please try again.');
    }
  };

  const stats = {
    total: timestamps.length,
    speakerA: timestamps.filter(t => t.speaker === 'A').length,
    speakerB: timestamps.filter(t => t.speaker === 'B').length,
    duration: timestamps.length > 0 ? Math.max(...timestamps.map(t => t.end_time_seconds || t.end_time || 0)) : 0,
  };

  return (
    <div className="w-full space-y-6">
      {/* Statistics */}
      <div className="grid grid-cols-4 gap-4">
        <div className="bg-blue-50 rounded-lg p-4">
          <p className="text-sm text-blue-600 font-medium">Total Segments</p>
          <p className="text-2xl font-bold text-blue-900">{stats.total}</p>
        </div>
        <div className="bg-green-50 rounded-lg p-4">
          <p className="text-sm text-green-600 font-medium">Speaker A</p>
          <p className="text-2xl font-bold text-green-900">{stats.speakerA}</p>
        </div>
        <div className="bg-purple-50 rounded-lg p-4">
          <p className="text-sm text-purple-600 font-medium">Speaker B</p>
          <p className="text-2xl font-bold text-purple-900">{stats.speakerB}</p>
        </div>
        <div className="bg-orange-50 rounded-lg p-4">
          <p className="text-sm text-orange-600 font-medium">Duration</p>
          <p className="text-2xl font-bold text-orange-900">{formatTime(stats.duration)}</p>
        </div>
      </div>

      {/* Download Buttons */}
      <div className="space-y-4">
        <div>
          <h3 className="text-sm font-semibold text-gray-700 mb-2">Download Timestamps</h3>
          <div className="flex flex-wrap gap-3">
            <button
              onClick={() => handleDownload('json')}
              className="flex items-center space-x-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
            >
              <FileJson className="h-4 w-4" />
              <span>Timestamps JSON</span>
            </button>
            {/* <button
              onClick={() => handleDownload('csv')}
              className="flex items-center space-x-2 px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 transition-colors"
            >
              <FileSpreadsheet className="h-4 w-4" />
              <span>CSV</span>
            </button>
            <button
              onClick={() => handleDownload('txt')}
              className="flex items-center space-x-2 px-4 py-2 bg-purple-600 text-white rounded-lg hover:bg-purple-700 transition-colors"
            >
              <FileText className="h-4 w-4" />
              <span>TXT</span>
            </button> */}
          </div>
        </div>

        {/* Transcript Download */}
        {hasTranscript && (
          <div>
            <h3 className="text-sm font-semibold text-gray-700 mb-2">
              Download WhisperX Transcript
              <span className="ml-2 text-xs font-normal text-gray-500">
                (Compare with original script)
              </span>
            </h3>
            <button
              onClick={handleDownloadTranscript}
              className="flex items-center space-x-2 px-4 py-2 bg-orange-600 text-white rounded-lg hover:bg-orange-700 transition-colors"
            >
              <FileCode className="h-4 w-4" />
              <span>Transcript JSON</span>
            </button>
            <p className="text-xs text-gray-500 mt-2">
              Contains word-by-word timestamps and confidence scores from WhisperX
            </p>
          </div>
        )}
      </div>

      {/* Filters */}
      <div className="flex gap-4">
        <div className="flex-1 relative">
          <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-5 w-5 text-gray-400" />
          <input
            type="text"
            placeholder="Search in transcripts..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="w-full pl-10 pr-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
          />
        </div>
        <select
          value={filterSpeaker}
          onChange={(e) => setFilterSpeaker(e.target.value)}
          className="px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
        >
          <option value="all">All Speakers</option>
          <option value="A">Speaker A</option>
          <option value="B">Speaker B</option>
        </select>
      </div>

      {/* Results List */}
      <div className="bg-white border border-gray-200 rounded-lg overflow-hidden">
        <div className="max-h-96 overflow-y-auto">
          {filteredTimestamps.length === 0 ? (
            <div className="p-8 text-center text-gray-500">
              No results found
            </div>
          ) : (
            <div className="divide-y divide-gray-200">
              {filteredTimestamps.map((item) => (
                <div
                  key={item.index}
                  className={`p-4 hover:bg-gray-50 transition-colors ${
                    item.speaker === 'A' ? 'border-l-4 border-l-green-500' : 'border-l-4 border-l-purple-500'
                  }`}
                >
                  <div className="flex items-start justify-between mb-2">
                    <div className="flex items-center space-x-3">
                      <span className="text-xs font-semibold text-gray-500">
                        #{item.index}
                      </span>
                      <span
                        className={`px-2 py-1 text-xs font-medium rounded ${
                          item.speaker === 'A'
                            ? 'bg-green-100 text-green-800'
                            : 'bg-purple-100 text-purple-800'
                        }`}
                      >
                        Speaker {item.speaker}
                      </span>
                    </div>
                    <div className="text-sm text-gray-600">
                      {item.start_time_seconds !== undefined ? formatTime(item.start_time_seconds) : item.start_time} - {item.end_time_seconds !== undefined ? formatTime(item.end_time_seconds) : item.end_time}
                      <span className="ml-2 text-xs text-gray-400">
                        ({(() => {
                          const endTime = item.end_time_seconds ?? item.end_time ?? 0;
                          const startTime = item.start_time_seconds ?? item.start_time ?? 0;
                          const duration = endTime - startTime;
                          return !isNaN(duration) ? duration.toFixed(2) : '0.00';
                        })()}s)
                      </span>
                    </div>
                  </div>
                  <p className="text-gray-800 leading-relaxed">{item.text}</p>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>

      <div className="text-sm text-gray-500 text-center">
        Showing {filteredTimestamps.length} of {timestamps.length} segments
      </div>
    </div>
  );
};

export default ResultsDisplay;
