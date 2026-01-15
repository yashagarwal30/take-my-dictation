import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import Navbar from '../components/Navbar';
import Footer from '../components/Footer';
import AudioRecorder from '../components/AudioRecorder';
import { apiService } from '../utils/api';
import { FaClock } from 'react-icons/fa';

const RecordingPage = () => {
  const navigate = useNavigate();
  const [isUploading, setIsUploading] = useState(false);
  const [error, setError] = useState(null);
  const [trialUsage, setTrialUsage] = useState(null);
  const [isTrial, setIsTrial] = useState(false);
  const [subscriptionRequired, setSubscriptionRequired] = useState(false);
  const [checkingSubscription, setCheckingSubscription] = useState(true);

  useEffect(() => {
    checkUserSubscriptionStatus();
  }, []);

  const checkUserSubscriptionStatus = async () => {
    try {
      // Check if user is in trial mode
      const trialMode = localStorage.getItem('isTrial') === 'true';
      setIsTrial(trialMode);

      if (trialMode) {
        // Fetch trial usage
        const response = await apiService.getTrialUsage();
        setTrialUsage(response.data);
        setCheckingSubscription(false);
      } else {
        // Check regular user's subscription status
        const usageResponse = await apiService.checkUsageStatus();
        const usageData = usageResponse.data;

        // If user has no subscription (monthly_hours_limit = 0), redirect to subscription page
        if (usageData.monthly_hours_limit <= 0) {
          // Redirect to subscription page with a message
          navigate('/subscription', {
            state: {
              message: 'Please subscribe to start recording. Your free trial has ended.'
            }
          });
          return;
        }

        setCheckingSubscription(false);
      }
    } catch (err) {
      console.error('Error checking subscription status:', err);
      setCheckingSubscription(false);
    }
  };

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
      const errorDetail = err.response?.data?.detail;

      // Handle both string and object error details
      if (typeof errorDetail === 'object' && errorDetail !== null) {
        // Check if subscription is required
        if (errorDetail.subscription_required || errorDetail.upgrade_required) {
          setError(errorDetail.message || 'Subscription required to continue.');
          setSubscriptionRequired(true);
        } else {
          setError(errorDetail.message || 'Failed to upload audio. Please try again.');
        }
      } else {
        setError(errorDetail || 'Failed to upload audio. Please try again.');
      }
      setIsUploading(false);
    }
  };

  return (
    <div className="flex flex-col min-h-screen">
      <Navbar />

      <main className="flex-1 bg-gray-50 py-12">
        <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8">
          {/* Trial Usage Banner */}
          {isTrial && trialUsage && (
            <div className="mb-6 bg-gradient-to-r from-yellow-400 to-orange-400 rounded-lg shadow-lg p-6 text-white">
              <div className="flex items-center justify-between">
                <div className="flex items-center space-x-3">
                  <FaClock className="text-3xl" />
                  <div>
                    <h3 className="text-xl font-bold">Free Trial</h3>
                    <p className="text-sm">
                      {trialUsage.trial_minutes_remaining > 0
                        ? `${trialUsage.trial_minutes_remaining.toFixed(1)} minutes remaining`
                        : 'Trial time expired'}
                    </p>
                  </div>
                </div>
                <button
                  onClick={() => navigate('/subscribe')}
                  className="bg-white text-orange-600 hover:bg-gray-100 font-bold py-2 px-6 rounded-lg transition duration-200"
                >
                  Upgrade Now
                </button>
              </div>
              {trialUsage.trial_minutes_remaining <= 2 && trialUsage.trial_minutes_remaining > 0 && (
                <p className="mt-3 text-sm">
                  You're almost out of trial time! Subscribe to get unlimited recording.
                </p>
              )}
            </div>
          )}

          <div className="bg-white rounded-lg shadow-lg p-8">
            <h1 className="text-4xl font-bold text-center mb-4 text-gray-800">
              Record Your Audio
            </h1>
            <p className="text-center text-gray-600 mb-8">
              Click the microphone to start recording. You can pause and resume anytime.
            </p>

            {error && (
              <div className="mb-6 bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded">
                <p className="mb-2">{error}</p>
                {subscriptionRequired && (
                  <button
                    onClick={() => navigate('/subscribe')}
                    className="mt-2 bg-red-600 hover:bg-red-700 text-white font-semibold py-2 px-4 rounded transition duration-200"
                  >
                    View Subscription Plans
                  </button>
                )}
              </div>
            )}

            {checkingSubscription ? (
              <div className="text-center py-12">
                <div className="inline-block animate-spin rounded-full h-12 w-12 border-b-2 border-primary mb-4"></div>
                <p className="text-lg text-gray-700">Checking subscription status...</p>
              </div>
            ) : isUploading ? (
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
