import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import Navbar from '../components/Navbar';
import Footer from '../components/Footer';
import AudioRecorder from '../components/AudioRecorder';
import { apiService } from '../utils/api';

const RecordingPage = () => {
  const navigate = useNavigate();
  const [isUploading, setIsUploading] = useState(false);
  const [error, setError] = useState(null);

  const handleRecordingComplete = async (audioBlob, duration) => {
    setIsUploading(true);
    setError(null);

    try {
      // Determine file extension based on blob type
      const mimeType = audioBlob.type;
      let extension = 'webm'; // default

      if (mimeType.includes('ogg')) {
        extension = 'ogg';
      } else if (mimeType.includes('mp4') || mimeType.includes('m4a')) {
        extension = 'm4a';
      } else if (mimeType.includes('wav')) {
        extension = 'wav';
      } else if (mimeType.includes('webm')) {
        extension = 'webm';
      }

      // Convert blob to file with correct extension
      const audioFile = new File([audioBlob], `recording.${extension}`, { type: mimeType });

      // Create form data
      const formData = new FormData();
      formData.append('file', audioFile);

      // Upload audio
      const response = await apiService.uploadAudio(formData);
      const recordingId = response.data.id;

      // Navigate to processing page with recording ID
      navigate('/processing', { state: { recordingId } });
    } catch (err) {
      console.error('Error uploading audio:', err);
      setError(err.response?.data?.detail || 'Failed to upload audio. Please try again.');
      setIsUploading(false);
    }
  };

  return (
    <div className="flex flex-col min-h-screen">
      <Navbar />

      <main className="flex-1 bg-gray-50 py-12">
        <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="bg-white rounded-lg shadow-lg p-8">
            <h1 className="text-4xl font-bold text-center mb-4 text-gray-800">
              Record Your Audio
            </h1>
            <p className="text-center text-gray-600 mb-8">
              Click the microphone to start recording. You can pause and resume anytime.
            </p>

            {error && (
              <div className="mb-6 bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded">
                {error}
              </div>
            )}

            {isUploading ? (
              <div className="text-center py-12">
                <div className="inline-block animate-spin rounded-full h-12 w-12 border-b-2 border-primary mb-4"></div>
                <p className="text-lg text-gray-700">Uploading your recording...</p>
              </div>
            ) : (
              <AudioRecorder
                onRecordingComplete={handleRecordingComplete}
                maxDuration={600} // 10 minutes for free users
              />
            )}

            <div className="mt-8 bg-blue-50 border border-blue-200 rounded-lg p-4">
              <h3 className="font-semibold text-blue-900 mb-2">Tips for Better Results:</h3>
              <ul className="list-disc list-inside text-blue-800 space-y-1">
                <li>Speak clearly and at a moderate pace</li>
                <li>Use a quiet environment to reduce background noise</li>
                <li>Use headphones with a microphone for best quality</li>
                <li>Free users: 10-minute recording limit</li>
              </ul>
            </div>
          </div>
        </div>
      </main>

      <Footer />
    </div>
  );
};

export default RecordingPage;
