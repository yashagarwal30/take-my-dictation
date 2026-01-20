import React, { useState, useEffect, useContext } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  FaCreditCard,
  FaArrowLeft,
  FaCheckCircle,
  FaClock,
  FaCalendar,
  FaTimes,
  FaExclamationTriangle
} from 'react-icons/fa';
import { UserContext } from '../context/UserContext';
import { apiService } from '../utils/api';
import { formatHoursMinutes } from '../utils/formatTime';
import Navbar from '../components/Navbar';

const SubscriptionManagementPage = () => {
  const { user, updateUser } = useContext(UserContext);
  const navigate = useNavigate();
  const [loading, setLoading] = useState(true);
  const [subscriptionData, setSubscriptionData] = useState(null);
  const [error, setError] = useState('');
  const [showCancelModal, setShowCancelModal] = useState(false);
  const [cancelLoading, setCancelLoading] = useState(false);

  useEffect(() => {
    const fetchSubscriptionDetails = async () => {
      try {
        const response = await apiService.getSubscriptionDetails();
        setSubscriptionData(response.data);
      } catch (err) {
        console.error('Error fetching subscription details:', err);
        setError('Failed to load subscription data');
      } finally {
        setLoading(false);
      }
    };

    fetchSubscriptionDetails();
  }, []);

  const handleCancelSubscription = async () => {
    setCancelLoading(true);
    try {
      await apiService.cancelSubscription();

      // Update user context
      const updatedUser = { ...user, subscription_tier: 'free' };
      updateUser(updatedUser);

      // Refresh subscription data
      const response = await apiService.getSubscriptionDetails();
      setSubscriptionData(response.data);

      setShowCancelModal(false);

      // Dispatch event to update navbar
      window.dispatchEvent(new Event('subscriptionUpdated'));

      alert('Subscription cancelled successfully. You will have access until the end of your billing period.');
    } catch (err) {
      console.error('Error cancelling subscription:', err);
      alert(err.response?.data?.detail || 'Failed to cancel subscription. Please try again.');
    } finally {
      setCancelLoading(false);
    }
  };

  const getStatusBadge = (status) => {
    const badges = {
      trial: { color: 'bg-gray-100 text-gray-800 border-gray-300', text: 'Trial' },
      active: { color: 'bg-green-100 text-green-800 border-green-300', text: 'Active' },
      expired: { color: 'bg-red-100 text-red-800 border-red-300', text: 'Expired' },
      cancelled: { color: 'bg-yellow-100 text-yellow-800 border-yellow-300', text: 'Cancelled' }
    };
    return badges[status?.toLowerCase()] || badges.trial;
  };

  const getPlanBadge = (tier) => {
    const badges = {
      trial: 'bg-gray-100 text-gray-800 border-gray-300',
      basic: 'bg-blue-100 text-blue-800 border-blue-300',
      pro: 'bg-purple-100 text-purple-800 border-purple-300'
    };
    return badges[tier?.toLowerCase()] || badges.trial;
  };

  const formatRenewalDate = (dateString) => {
    if (!dateString) return 'N/A';
    return new Date(dateString).toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'long',
      day: 'numeric'
    });
  };

  const getUsagePercentage = () => {
    if (!subscriptionData?.monthly_hours_limit || subscriptionData.monthly_hours_limit === 0) {
      return 0;
    }
    const used = subscriptionData.monthly_hours_used || 0;
    const limit = subscriptionData.monthly_hours_limit;
    return Math.min((used / limit) * 100, 100);
  };

  const getProgressColor = () => {
    const percentage = getUsagePercentage();
    if (percentage < 80) return 'bg-green-500';
    if (percentage < 90) return 'bg-yellow-500';
    return 'bg-red-500';
  };

  const getRemainingHours = () => {
    const used = subscriptionData?.monthly_hours_used || 0;
    const limit = subscriptionData?.monthly_hours_limit || 0;
    return Math.max(limit - used, 0);
  };

  if (loading) {
    return (
      <>
        <Navbar />
        <div className="min-h-screen bg-gray-50 flex items-center justify-center">
          <div className="text-center">
            <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary mx-auto"></div>
            <p className="mt-4 text-gray-600">Loading subscription details...</p>
          </div>
        </div>
      </>
    );
  }

  if (error) {
    return (
      <>
        <Navbar />
        <div className="min-h-screen bg-gray-50 py-8">
          <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8">
            <div className="bg-red-50 border border-red-200 rounded-lg p-6">
              <p className="text-red-800">{error}</p>
            </div>
          </div>
        </div>
      </>
    );
  }

  const isTrial = subscriptionData?.is_trial_user;
  const isPaidUser = !isTrial && subscriptionData?.subscription_tier !== 'free';

  return (
    <>
      <Navbar />
      <div className="min-h-screen bg-gray-50 py-8">
        <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8">
          {/* Back Button */}
          <button
            onClick={() => navigate('/dashboard')}
            className="flex items-center text-gray-600 hover:text-gray-900 mb-6 transition"
          >
            <FaArrowLeft className="mr-2" />
            Back to Dashboard
          </button>

          <h1 className="text-3xl font-bold text-gray-900 mb-8">Subscription Management</h1>

          {/* Current Plan Card */}
          <div className="bg-white rounded-lg shadow-md p-6 mb-6">
            <h2 className="text-xl font-semibold text-gray-900 mb-6 flex items-center">
              <FaCreditCard className="mr-2 text-primary" />
              Current Plan
            </h2>

            <div className="space-y-4">
              {/* Plan Name and Status */}
              <div className="flex items-center justify-between border-b border-gray-200 pb-4">
                <div>
                  <p className="text-sm font-medium text-gray-600 mb-2">Plan Type</p>
                  <span
                    className={`inline-flex items-center px-4 py-2 rounded-full text-lg font-semibold border ${getPlanBadge(
                      subscriptionData?.subscription_tier
                    )}`}
                  >
                    {subscriptionData?.subscription_tier?.toUpperCase() || 'TRIAL'}
                  </span>
                </div>
                <div>
                  <p className="text-sm font-medium text-gray-600 mb-2">Status</p>
                  <span
                    className={`inline-flex items-center px-4 py-2 rounded-full text-sm font-semibold border ${
                      getStatusBadge(subscriptionData?.status).color
                    }`}
                  >
                    <FaCheckCircle className="mr-2" />
                    {getStatusBadge(subscriptionData?.status).text}
                  </span>
                </div>
              </div>

              {/* Usage Information */}
              <div className="border-b border-gray-200 pb-4">
                <div className="flex items-center justify-between mb-2">
                  <p className="text-sm font-medium text-gray-600">Monthly Usage</p>
                  <p className="text-sm text-gray-900 font-semibold">
                    {formatHoursMinutes(getRemainingHours())} of{' '}
                    {subscriptionData?.monthly_hours_limit || 0} hours remaining
                  </p>
                </div>
                <div className="w-full bg-gray-200 rounded-full h-3">
                  <div
                    className={`${getProgressColor()} h-3 rounded-full transition-all`}
                    style={{ width: `${Math.max(0, 100 - getUsagePercentage())}%` }}
                  />
                </div>
                <p className="text-xs text-gray-500 mt-1">
                  Used: {formatHoursMinutes(subscriptionData?.monthly_hours_used || 0)}
                </p>
              </div>

              {/* Hours Limit */}
              <div className="flex items-center justify-between border-b border-gray-200 pb-4">
                <div className="flex items-center text-gray-700">
                  <FaClock className="mr-3 text-gray-400" />
                  <span className="font-medium">Monthly Hours Limit</span>
                </div>
                <span className="text-lg font-semibold text-gray-900">
                  {subscriptionData?.monthly_hours_limit || 0} hours
                </span>
              </div>
            </div>
          </div>

          {/* Billing Information Card - Only for paid users */}
          {isPaidUser && (
            <div className="bg-white rounded-lg shadow-md p-6 mb-6">
              <h2 className="text-xl font-semibold text-gray-900 mb-6 flex items-center">
                <FaCalendar className="mr-2 text-primary" />
                Billing Information
              </h2>

              <div className="space-y-4">
                {/* Next Renewal Date */}
                {subscriptionData?.subscription_expires_at && (
                  <div className="flex items-center justify-between border-b border-gray-200 pb-4">
                    <div className="flex items-center text-gray-700">
                      <FaCalendar className="mr-3 text-gray-400" />
                      <span className="font-medium">Next Renewal Date</span>
                    </div>
                    <span className="text-lg font-semibold text-gray-900">
                      {formatRenewalDate(subscriptionData.subscription_expires_at)}
                    </span>
                  </div>
                )}

                {/* Anniversary Day */}
                {subscriptionData?.subscription_anniversary_date && (
                  <div className="flex items-center justify-between border-b border-gray-200 pb-4">
                    <div className="flex items-center text-gray-700">
                      <FaCalendar className="mr-3 text-gray-400" />
                      <span className="font-medium">Billing Anniversary Day</span>
                    </div>
                    <span className="text-lg font-semibold text-gray-900">
                      Day {subscriptionData.subscription_anniversary_date} of each month
                    </span>
                  </div>
                )}

                {/* Razorpay Subscription ID */}
                {subscriptionData?.razorpay_subscription_id && (
                  <div className="flex items-center justify-between pb-2">
                    <div className="flex items-center text-gray-700">
                      <FaCreditCard className="mr-3 text-gray-400" />
                      <span className="font-medium">Subscription ID</span>
                    </div>
                    <span className="text-sm text-gray-600 font-mono">
                      {subscriptionData.razorpay_subscription_id}
                    </span>
                  </div>
                )}
              </div>
            </div>
          )}

          {/* Actions Card */}
          <div className="bg-white rounded-lg shadow-md p-6">
            <h2 className="text-xl font-semibold text-gray-900 mb-6">Actions</h2>

            <div className="space-y-4">
              {isTrial ? (
                <>
                  {/* Upgrade Button for Trial Users */}
                  <button
                    onClick={() => navigate('/subscribe')}
                    className="w-full bg-primary hover:bg-primary-dark text-white font-semibold py-3 px-6 rounded-lg transition duration-200 flex items-center justify-center"
                  >
                    <FaCheckCircle className="mr-2" />
                    Upgrade to Premium
                  </button>
                  <p className="text-sm text-gray-600 text-center">
                    Get unlimited access with a paid subscription
                  </p>
                </>
              ) : isPaidUser ? (
                <>
                  {/* Change Plan Button */}
                  <button
                    onClick={() => navigate('/subscribe')}
                    className="w-full bg-blue-600 hover:bg-blue-700 text-white font-semibold py-3 px-6 rounded-lg transition duration-200 flex items-center justify-center"
                  >
                    <FaCreditCard className="mr-2" />
                    Change Plan
                  </button>

                  {/* Cancel Subscription Button */}
                  <button
                    onClick={() => setShowCancelModal(true)}
                    className="w-full bg-red-600 hover:bg-red-700 text-white font-semibold py-3 px-6 rounded-lg transition duration-200 flex items-center justify-center"
                  >
                    <FaTimes className="mr-2" />
                    Cancel Subscription
                  </button>
                  <p className="text-sm text-gray-600 text-center">
                    You will have access until the end of your billing period
                  </p>
                </>
              ) : (
                <>
                  {/* Reactivate Button for Expired/Cancelled Users */}
                  <button
                    onClick={() => navigate('/subscribe')}
                    className="w-full bg-primary hover:bg-primary-dark text-white font-semibold py-3 px-6 rounded-lg transition duration-200 flex items-center justify-center"
                  >
                    <FaCheckCircle className="mr-2" />
                    Reactivate Subscription
                  </button>
                </>
              )}
            </div>
          </div>
        </div>
      </div>

      {/* Cancel Subscription Modal */}
      {showCancelModal && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-lg max-w-md w-full p-6">
            <div className="flex items-center mb-4">
              <FaExclamationTriangle className="text-red-500 text-3xl mr-3" />
              <h3 className="text-xl font-bold text-gray-900">Cancel Subscription?</h3>
            </div>

            <p className="text-gray-700 mb-6">
              Are you sure you want to cancel your subscription? You will lose access to premium
              features at the end of your current billing period.
            </p>

            <div className="flex space-x-4">
              <button
                onClick={() => setShowCancelModal(false)}
                disabled={cancelLoading}
                className="flex-1 bg-gray-200 hover:bg-gray-300 text-gray-800 font-semibold py-2 px-4 rounded-lg transition duration-200 disabled:opacity-50"
              >
                Keep Subscription
              </button>
              <button
                onClick={handleCancelSubscription}
                disabled={cancelLoading}
                className="flex-1 bg-red-600 hover:bg-red-700 text-white font-semibold py-2 px-4 rounded-lg transition duration-200 disabled:opacity-50 flex items-center justify-center"
              >
                {cancelLoading ? (
                  <>
                    <div className="animate-spin rounded-full h-5 w-5 border-b-2 border-white mr-2"></div>
                    Cancelling...
                  </>
                ) : (
                  'Yes, Cancel'
                )}
              </button>
            </div>
          </div>
        </div>
      )}
    </>
  );
};

export default SubscriptionManagementPage;
