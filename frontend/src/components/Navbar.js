import React, { useContext, useState, useEffect } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { UserContext } from '../context/UserContext';
import { FaMicrophone, FaUser, FaSignOutAlt, FaClock } from 'react-icons/fa';
import { apiService } from '../utils/api';
import { formatHoursMinutes } from '../utils/formatTime';

const Navbar = () => {
  const { user, logout } = useContext(UserContext);
  const navigate = useNavigate();
  const [usageInfo, setUsageInfo] = useState(null);
  const [isTrial, setIsTrial] = useState(false);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchUsageInfo = async () => {
      if (!user) {
        setLoading(false);
        return;
      }

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
      } finally {
        setLoading(false);
      }
    };

    fetchUsageInfo();

    // Listen for subscription updates
    const handleSubscriptionUpdate = () => {
      setLoading(true);
      fetchUsageInfo();
    };

    // Listen for usage updates (after recordings/transcriptions)
    const handleUsageUpdate = () => {
      fetchUsageInfo();
    };

    window.addEventListener('subscriptionUpdated', handleSubscriptionUpdate);
    window.addEventListener('usageUpdated', handleUsageUpdate);

    return () => {
      window.removeEventListener('subscriptionUpdated', handleSubscriptionUpdate);
      window.removeEventListener('usageUpdated', handleUsageUpdate);
    };
  }, [user]);

  const handleLogout = () => {
    logout();
    navigate('/');
  };

  // Helper functions for color coding based on usage percentage
  const getBackgroundColor = () => {
    if (!usageInfo) return 'bg-gray-50';
    if (isTrial) {
      const remaining = usageInfo.trial_minutes_remaining || 0;
      if (remaining > 2) return 'bg-green-50';
      if (remaining > 0) return 'bg-yellow-50';
      return 'bg-red-50';
    }
    const usagePercent = usageInfo.usage_percentage || 0;
    if (usagePercent < 80) return 'bg-green-50';
    if (usagePercent < 90) return 'bg-yellow-50';
    return 'bg-red-50';
  };

  const getBorderColor = () => {
    if (!usageInfo) return 'border-gray-300';
    if (isTrial) {
      const remaining = usageInfo.trial_minutes_remaining || 0;
      if (remaining > 2) return 'border-green-300';
      if (remaining > 0) return 'border-yellow-300';
      return 'border-red-300';
    }
    const usagePercent = usageInfo.usage_percentage || 0;
    if (usagePercent < 80) return 'border-green-300';
    if (usagePercent < 90) return 'border-yellow-300';
    return 'border-red-300';
  };

  const getIconColor = () => {
    if (!usageInfo) return 'text-gray-500';
    if (isTrial) {
      const remaining = usageInfo.trial_minutes_remaining || 0;
      if (remaining > 2) return 'text-green-600';
      if (remaining > 0) return 'text-yellow-600';
      return 'text-red-600';
    }
    const usagePercent = usageInfo.usage_percentage || 0;
    if (usagePercent < 80) return 'text-green-600';
    if (usagePercent < 90) return 'text-yellow-600';
    return 'text-red-600';
  };

  const getProgressColor = () => {
    if (!usageInfo) return 'bg-gray-500';
    const usagePercent = usageInfo.usage_percentage || 0;
    if (usagePercent < 80) return 'bg-green-500';
    if (usagePercent < 90) return 'bg-yellow-500';
    return 'bg-red-500';
  };

  return (
    <>
      <nav className="bg-white shadow-md">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between items-center h-16">
            {/* Logo - redirect based on authentication status */}
            <Link to={user ? "/dashboard" : "/"} className="flex items-center space-x-2">
              <FaMicrophone className="text-primary text-2xl" />
              <span className="text-xl font-bold text-gray-800">Take My Dictation</span>
            </Link>

            {/* Navigation Links */}
            <div className="flex items-center space-x-4">
              {user ? (
                <>
                  <Link
                    to="/dashboard"
                    className="flex items-center space-x-1 text-gray-700 hover:text-primary transition"
                  >
                    <FaUser />
                    <span>Dashboard</span>
                  </Link>
                  <button
                    onClick={handleLogout}
                    className="flex items-center space-x-1 text-gray-700 hover:text-red-600 transition"
                  >
                    <FaSignOutAlt />
                    <span>Logout</span>
                  </button>
                </>
              ) : (
                <>
                  <Link
                    to="/login"
                    className="text-gray-700 hover:text-primary font-semibold transition"
                  >
                    Login
                  </Link>
                  <Link
                    to="/signup"
                    className="bg-primary hover:bg-primary-dark text-white font-semibold py-2 px-4 rounded-lg transition duration-200"
                  >
                    Sign Up
                  </Link>
                </>
              )}
            </div>
          </div>
        </div>
      </nav>

      {/* Subscription Status Banner */}
      {user && !loading && usageInfo && (
        <div className={`w-full ${getBackgroundColor()} border-b-2 ${getBorderColor()}`}>
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-2 sm:py-3">
            <div className="flex items-center justify-between flex-wrap gap-3">
              <div className="flex items-center space-x-3 flex-1 min-w-0">
                <FaClock className={`${getIconColor()} text-lg flex-shrink-0`} />
                <div className="flex-1 min-w-0">
                  <div className="text-sm sm:text-base font-semibold text-gray-800 truncate">
                    {isTrial ? (
                      <>
                        <span className="hidden sm:inline">Free Trial: </span>
                        <span className="sm:hidden">Trial: </span>
                        {usageInfo.trial_minutes_remaining?.toFixed(1)}
                        <span className="hidden sm:inline"> minutes remaining</span>
                        <span className="sm:hidden"> min left</span>
                      </>
                    ) : (
                      <>
                        <span className="hidden sm:inline">
                          {usageInfo.subscription_tier?.toUpperCase()} Plan: {formatHoursMinutes(usageInfo.monthly_hours_remaining)} of {usageInfo.monthly_hours_limit} hours remaining this month
                        </span>
                        <span className="sm:hidden">
                          {usageInfo.subscription_tier?.toUpperCase()}: {formatHoursMinutes(usageInfo.monthly_hours_remaining, true)}/{usageInfo.monthly_hours_limit} hrs
                        </span>
                      </>
                    )}
                  </div>
                  {!isTrial && (
                    <div className="w-full sm:w-64 bg-gray-200 rounded-full h-2 mt-1">
                      <div
                        className={`${getProgressColor()} h-2 rounded-full transition-all`}
                        style={{ width: `${Math.max(0, 100 - (usageInfo.usage_percentage || 0))}%` }}
                      />
                    </div>
                  )}
                </div>
              </div>
              {(isTrial || (usageInfo.usage_percentage || 0) > 80) && (
                <button
                  onClick={() => navigate('/subscribe')}
                  className="bg-primary hover:bg-primary-dark text-white text-sm font-semibold py-2 px-4 rounded-lg transition duration-200 flex-shrink-0"
                >
                  {isTrial ? 'Upgrade' : 'View Plans'}
                </button>
              )}
            </div>
          </div>
        </div>
      )}
    </>
  );
};

export default Navbar;
