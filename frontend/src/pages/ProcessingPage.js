import { useEffect, useState, useCallback } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import Navbar from '../components/Navbar';
import Footer from '../components/Footer';
import { apiService } from '../utils/api';

const ProcessingPage = () => {
  const navigate = useNavigate();
  const location = useLocation();
  const { recordingId } = location.state || {};

  const [status, setStatus] = useState('Uploading audio...');
  const [error, setError] = useState(null);
  const [subscriptionRequired, setSubscriptionRequired] = useState(false);

  const processRecording = useCallback(async () => {
    try {
      // Step 1: Transcribe
      setStatus('Transcribing your audio with AI...');
      await apiService.createTranscription(recordingId);

      // Wait a bit for transcription to complete
      await new Promise(resolve => setTimeout(resolve, 1000));

      // Dispatch event to update navbar usage
      window.dispatchEvent(new Event('usageUpdated'));

      // Navigate to summary page (user will choose summary format there)
      setStatus('Transcription complete! Redirecting...');
      setTimeout(() => {
        navigate('/summary', { state: { recordingId } });
      }, 500);
    } catch (err) {
      console.error('Error processing recording:', err);
      const errorDetail = err.response?.data?.detail;

      // Handle both string and object error details
      if (typeof errorDetail === 'object' && errorDetail !== null) {
        // Check if subscription is required
        if (errorDetail.subscription_required || errorDetail.upgrade_required) {
          // Show error message and allow navigation to subscription page
          setError(errorDetail.message || 'Subscription required to continue.');
          setSubscriptionRequired(true);
        } else {
          // If it's an object with a message property, use that
          setError(errorDetail.message || 'Failed to process recording. Please try again.');
        }
      } else {
        setError(errorDetail || 'Failed to process recording. Please try again.');
      }
    }
  }, [recordingId, navigate]);

  useEffect(() => {
    if (!recordingId) {
      navigate('/record');
      return;
    }

    processRecording();
  }, [recordingId, navigate, processRecording]);

  return (
    <div className="flex flex-col min-h-screen">
      <Navbar />

      <main className="flex-1 bg-gray-50 py-12">
        <div className="max-w-2xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="bg-white rounded-lg shadow-lg p-8 text-center">
            {error ? (
              <>
                <div className="text-red-500 text-6xl mb-4">✕</div>
                <h1 className="text-3xl font-bold text-red-600 mb-4">
                  {subscriptionRequired ? 'Subscription Required' : 'Processing Failed'}
                </h1>
                <p className="text-gray-600 mb-6">{error}</p>
                <div className="flex gap-4 justify-center">
                  {subscriptionRequired ? (
                    <>
                      <button
                        onClick={() => navigate('/subscribe')}
                        className="bg-primary hover:bg-primary-dark text-white font-semibold py-3 px-6 rounded-lg transition duration-200"
                      >
                        View Plans
                      </button>
                      <button
                        onClick={() => navigate('/dashboard')}
                        className="bg-gray-500 hover:bg-gray-600 text-white font-semibold py-3 px-6 rounded-lg transition duration-200"
                      >
                        Go to Dashboard
                      </button>
                    </>
                  ) : (
                    <button
                      onClick={() => navigate('/record')}
                      className="bg-primary hover:bg-primary-dark text-white font-semibold py-3 px-6 rounded-lg transition duration-200"
                    >
                      Try Again
                    </button>
                  )}
                </div>
              </>
            ) : (
              <>
                <div className="inline-block animate-spin rounded-full h-16 w-16 border-b-4 border-primary mb-6"></div>
                <h1 className="text-3xl font-bold text-gray-800 mb-4">Processing Your Recording</h1>
                <p className="text-xl text-gray-600 mb-8">{status}</p>

                <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
                  <p className="text-blue-800">
                    This may take a minute depending on the length of your recording.
                    Please don't close this page.
                  </p>
                </div>
              </>
            )}
          </div>
        </div>
      </main>

      <Footer />
    </div>
  );
};

export default ProcessingPage;
