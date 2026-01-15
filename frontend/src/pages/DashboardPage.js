import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import Navbar from '../components/Navbar';
import Footer from '../components/Footer';
import { apiService } from '../utils/api';
import { FaFileAlt, FaTrash, FaClock, FaCheckCircle } from 'react-icons/fa';

const DashboardPage = () => {
  const navigate = useNavigate();
  const [recordings, setRecordings] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [usageInfo, setUsageInfo] = useState(null);
  const [isTrial, setIsTrial] = useState(false);

  useEffect(() => {
    fetchRecordings();
    fetchUsageInfo();
  }, []);

  const fetchUsageInfo = async () => {
    try {
      const trialMode = localStorage.getItem('isTrial') === 'true';
      setIsTrial(trialMode);

      if (trialMode) {
        const response = await apiService.getTrialUsage();
        setUsageInfo(response.data);
      } else {
        const response = await apiService.checkUsageStatus();
        setUsageInfo(response.data);
      }
    } catch (err) {
      console.error('Error fetching usage info:', err);
    }
  };

  const fetchRecordings = async () => {
    try {
      setLoading(true);
      const response = await apiService.listRecordings(1, 20);
      setRecordings(response.data.items || []);
      setLoading(false);
    } catch (err) {
      console.error('Error fetching recordings:', err);
      setError('Failed to load recordings.');
      setLoading(false);
    }
  };

  const handleDelete = async (recordingId) => {
    if (window.confirm('Are you sure you want to delete this recording?')) {
      try {
        await apiService.deleteRecording(recordingId);
        setRecordings(recordings.filter(r => r.id !== recordingId));
      } catch (err) {
        console.error('Error deleting recording:', err);
        alert('Failed to delete recording.');
      }
    }
  };

  const handleView = (recordingId) => {
    navigate('/summary', { state: { recordingId } });
  };

  const handleNewRecording = () => {
    // Check if user needs subscription
    if (!isTrial && usageInfo && usageInfo.monthly_hours_limit <= 0) {
      navigate('/subscription', {
        state: {
          message: 'Please subscribe to start recording. Your free trial has ended.'
        }
      });
    } else {
      navigate('/record');
    }
  };

  const canRecord = () => {
    if (!usageInfo) return false;

    if (isTrial) {
      return usageInfo.trial_minutes_remaining > 0;
    } else {
      return usageInfo.monthly_hours_limit > 0;
    }
  };

  if (loading) {
    return (
      <div className="flex flex-col min-h-screen">
        <Navbar />
        <main className="flex-1 flex items-center justify-center">
          <div className="text-center">
            <div className="inline-block animate-spin rounded-full h-12 w-12 border-b-2 border-primary mb-4"></div>
            <p className="text-lg text-gray-700">Loading your recordings...</p>
          </div>
        </main>
        <Footer />
      </div>
    );
  }

  return (
    <div className="flex flex-col min-h-screen">
      <Navbar />

      <main className="flex-1 bg-gray-50 py-12">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between items-center mb-8">
            <h1 className="text-4xl font-bold text-gray-800">My Dashboard</h1>
            {canRecord() ? (
              <button
                onClick={handleNewRecording}
                className="bg-primary hover:bg-primary-dark text-white font-semibold py-3 px-6 rounded-lg transition duration-200"
              >
                New Recording
              </button>
            ) : (
              <button
                onClick={() => navigate('/subscribe')}
                className="bg-orange-500 hover:bg-orange-600 text-white font-semibold py-3 px-6 rounded-lg transition duration-200"
              >
                Subscribe to Record
              </button>
            )}
          </div>

          {/* Subscription Status Card */}
          {usageInfo && (
            <div className="mb-6 bg-white rounded-lg shadow-lg p-6">
              <div className="flex items-center justify-between">
                <div>
                  <h2 className="text-xl font-bold text-gray-800 mb-2">
                    {isTrial ? 'Free Trial' : `${usageInfo.subscription_tier?.toUpperCase() || 'FREE'} Plan`}
                  </h2>
                  {isTrial ? (
                    <div className="flex items-center space-x-2 text-gray-600">
                      <FaClock />
                      <span>
                        {usageInfo.trial_minutes_remaining > 0
                          ? `${usageInfo.trial_minutes_remaining?.toFixed(1)} minutes remaining`
                          : 'Trial expired'}
                      </span>
                    </div>
                  ) : usageInfo.monthly_hours_limit > 0 ? (
                    <div className="space-y-2">
                      <div className="flex items-center space-x-2 text-gray-600">
                        <FaCheckCircle className="text-green-500" />
                        <span>
                          {usageInfo.monthly_hours_remaining?.toFixed(1)} of {usageInfo.monthly_hours_limit} hours remaining this month
                        </span>
                      </div>
                      <div className="w-full bg-gray-200 rounded-full h-2">
                        <div
                          className="bg-green-500 h-2 rounded-full"
                          style={{
                            width: `${100 - (usageInfo.usage_percentage || 0)}%`
                          }}
                        ></div>
                      </div>
                    </div>
                  ) : (
                    <div className="text-red-600 font-semibold">
                      No active subscription - Subscribe to start recording
                    </div>
                  )}
                </div>
                {!isTrial && usageInfo.monthly_hours_limit <= 0 && (
                  <button
                    onClick={() => navigate('/subscribe')}
                    className="bg-primary hover:bg-primary-dark text-white font-semibold py-2 px-6 rounded-lg transition duration-200"
                  >
                    View Plans
                  </button>
                )}
              </div>
            </div>
          )}

          {error && (
            <div className="mb-6 bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded">
              {error}
            </div>
          )}

          {recordings.length === 0 ? (
            <div className="bg-white rounded-lg shadow-lg p-12 text-center">
              <FaFileAlt className="text-gray-300 text-6xl mx-auto mb-4" />
              <h2 className="text-2xl font-semibold text-gray-700 mb-2">No recordings yet</h2>
              <p className="text-gray-500 mb-6">Start by creating your first recording</p>
              {canRecord() ? (
                <button
                  onClick={handleNewRecording}
                  className="bg-primary hover:bg-primary-dark text-white font-semibold py-3 px-6 rounded-lg transition duration-200"
                >
                  Create Recording
                </button>
              ) : (
                <button
                  onClick={() => navigate('/subscribe')}
                  className="bg-orange-500 hover:bg-orange-600 text-white font-semibold py-3 px-6 rounded-lg transition duration-200"
                >
                  Subscribe to Start Recording
                </button>
              )}
            </div>
          ) : (
            <div className="grid grid-cols-1 gap-6">
              {recordings.map((recording) => (
                <div key={recording.id} className="bg-white rounded-lg shadow-lg p-6 hover:shadow-xl transition">
                  <div className="flex justify-between items-start">
                    <div className="flex-1">
                      <h3 className="text-xl font-semibold text-gray-800 mb-2">
                        {recording.filename || 'Untitled Recording'}
                      </h3>
                      <div className="text-sm text-gray-500 space-y-1">
                        <p>Duration: {Math.floor(recording.duration / 60)}:{(recording.duration % 60).toString().padStart(2, '0')}</p>
                        <p>Created: {new Date(recording.created_at).toLocaleString()}</p>
                        <p>Status: <span className="font-semibold text-green-600">{recording.status}</span></p>
                      </div>
                    </div>

                    <div className="flex space-x-2">
                      <button
                        onClick={() => handleView(recording.id)}
                        className="bg-primary hover:bg-primary-dark text-white font-semibold py-2 px-4 rounded-lg transition duration-200"
                      >
                        View
                      </button>
                      <button
                        onClick={() => handleDelete(recording.id)}
                        className="bg-red-500 hover:bg-red-600 text-white font-semibold py-2 px-4 rounded-lg transition duration-200"
                      >
                        <FaTrash />
                      </button>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </main>

      <Footer />
    </div>
  );
};

export default DashboardPage;
