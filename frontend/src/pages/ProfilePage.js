import React, { useState, useEffect, useContext } from 'react';
import { useNavigate } from 'react-router-dom';
import { FaUser, FaEnvelope, FaCalendar, FaCrown, FaLock, FaArrowLeft } from 'react-icons/fa';
import { UserContext } from '../context/UserContext';
import { apiService } from '../utils/api';
import Navbar from '../components/Navbar';

const ProfilePage = () => {
  const { user, updateUser } = useContext(UserContext);
  const navigate = useNavigate();
  const [loading, setLoading] = useState(true);
  const [passwordLoading, setPasswordLoading] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  const [passwordData, setPasswordData] = useState({
    currentPassword: '',
    newPassword: '',
    confirmPassword: ''
  });
  const [passwordErrors, setPasswordErrors] = useState({});

  useEffect(() => {
    const fetchUserData = async () => {
      try {
        const response = await apiService.getCurrentUser();
        updateUser(response.data);
      } catch (err) {
        console.error('Error fetching user data:', err);
        setError('Failed to load profile data');
      } finally {
        setLoading(false);
      }
    };

    fetchUserData();
  }, [updateUser]);

  const validatePassword = () => {
    const errors = {};

    if (!passwordData.currentPassword) {
      errors.currentPassword = 'Current password is required';
    }

    if (!passwordData.newPassword) {
      errors.newPassword = 'New password is required';
    } else if (passwordData.newPassword.length < 8) {
      errors.newPassword = 'Password must be at least 8 characters';
    } else if (!/(?=.*[a-zA-Z])/.test(passwordData.newPassword)) {
      errors.newPassword = 'Password must contain at least one letter';
    } else if (!/(?=.*\d)/.test(passwordData.newPassword)) {
      errors.newPassword = 'Password must contain at least one number';
    }

    if (!passwordData.confirmPassword) {
      errors.confirmPassword = 'Please confirm your new password';
    } else if (passwordData.newPassword !== passwordData.confirmPassword) {
      errors.confirmPassword = 'Passwords do not match';
    }

    if (passwordData.currentPassword && passwordData.newPassword &&
        passwordData.currentPassword === passwordData.newPassword) {
      errors.newPassword = 'New password must be different from current password';
    }

    return errors;
  };

  const handlePasswordChange = async (e) => {
    e.preventDefault();
    setError('');
    setSuccess('');
    setPasswordErrors({});

    const errors = validatePassword();
    if (Object.keys(errors).length > 0) {
      setPasswordErrors(errors);
      return;
    }

    setPasswordLoading(true);

    try {
      await apiService.changePassword(
        passwordData.currentPassword,
        passwordData.newPassword
      );
      setSuccess('Password changed successfully!');
      setPasswordData({
        currentPassword: '',
        newPassword: '',
        confirmPassword: ''
      });
      setTimeout(() => setSuccess(''), 5000);
    } catch (err) {
      const errorMessage = err.response?.data?.detail || 'Failed to change password';
      setError(errorMessage);
      setTimeout(() => setError(''), 5000);
    } finally {
      setPasswordLoading(false);
    }
  };

  const handlePasswordInputChange = (e) => {
    const { name, value } = e.target;
    setPasswordData(prev => ({ ...prev, [name]: value }));
    // Clear error for this field when user starts typing
    if (passwordErrors[name]) {
      setPasswordErrors(prev => ({ ...prev, [name]: '' }));
    }
  };

  const formatDate = (dateString) => {
    if (!dateString) return 'N/A';
    return new Date(dateString).toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'long',
      day: 'numeric'
    });
  };

  const getSubscriptionBadge = (tier) => {
    const badges = {
      trial: 'bg-gray-100 text-gray-800 border-gray-300',
      basic: 'bg-blue-100 text-blue-800 border-blue-300',
      pro: 'bg-purple-100 text-purple-800 border-purple-300'
    };
    return badges[tier?.toLowerCase()] || badges.trial;
  };

  if (loading) {
    return (
      <>
        <Navbar />
        <div className="min-h-screen bg-gray-50 flex items-center justify-center">
          <div className="text-center">
            <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary mx-auto"></div>
            <p className="mt-4 text-gray-600">Loading profile...</p>
          </div>
        </div>
      </>
    );
  }

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

          <h1 className="text-3xl font-bold text-gray-900 mb-8">Profile Settings</h1>

          {/* Profile Information Card */}
          <div className="bg-white rounded-lg shadow-md p-6 mb-6">
            <h2 className="text-xl font-semibold text-gray-900 mb-6 flex items-center">
              <FaUser className="mr-2 text-primary" />
              Profile Information
            </h2>

            <div className="space-y-4">
              {/* Full Name */}
              <div className="border-b border-gray-200 pb-4">
                <label className="block text-sm font-medium text-gray-600 mb-1">
                  Full Name
                </label>
                <div className="flex items-center text-gray-900">
                  <FaUser className="mr-3 text-gray-400" />
                  <span className="text-lg">{user?.full_name || 'N/A'}</span>
                </div>
              </div>

              {/* Email */}
              <div className="border-b border-gray-200 pb-4">
                <label className="block text-sm font-medium text-gray-600 mb-1">
                  Email Address
                </label>
                <div className="flex items-center text-gray-900">
                  <FaEnvelope className="mr-3 text-gray-400" />
                  <span className="text-lg">{user?.email || 'N/A'}</span>
                </div>
              </div>

              {/* Account Created */}
              <div className="border-b border-gray-200 pb-4">
                <label className="block text-sm font-medium text-gray-600 mb-1">
                  Account Created
                </label>
                <div className="flex items-center text-gray-900">
                  <FaCalendar className="mr-3 text-gray-400" />
                  <span className="text-lg">{formatDate(user?.created_at)}</span>
                </div>
              </div>

              {/* Subscription Tier */}
              <div className="pb-2">
                <label className="block text-sm font-medium text-gray-600 mb-1">
                  Subscription Plan
                </label>
                <div className="flex items-center">
                  <FaCrown className="mr-3 text-gray-400" />
                  <span
                    className={`inline-flex items-center px-3 py-1 rounded-full text-sm font-semibold border ${getSubscriptionBadge(
                      user?.subscription_tier
                    )}`}
                  >
                    {user?.subscription_tier?.toUpperCase() || 'TRIAL'}
                  </span>
                </div>
              </div>
            </div>
          </div>

          {/* Change Password Card */}
          <div className="bg-white rounded-lg shadow-md p-6">
            <h2 className="text-xl font-semibold text-gray-900 mb-6 flex items-center">
              <FaLock className="mr-2 text-primary" />
              Change Password
            </h2>

            {/* Success/Error Messages */}
            {success && (
              <div className="mb-4 p-4 bg-green-50 border border-green-200 rounded-lg">
                <p className="text-green-800 text-sm">{success}</p>
              </div>
            )}

            {error && (
              <div className="mb-4 p-4 bg-red-50 border border-red-200 rounded-lg">
                <p className="text-red-800 text-sm">{error}</p>
              </div>
            )}

            <form onSubmit={handlePasswordChange} className="space-y-4">
              {/* Current Password */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Current Password
                </label>
                <input
                  type="password"
                  name="currentPassword"
                  value={passwordData.currentPassword}
                  onChange={handlePasswordInputChange}
                  className={`w-full px-4 py-2 border ${
                    passwordErrors.currentPassword ? 'border-red-300' : 'border-gray-300'
                  } rounded-lg focus:ring-2 focus:ring-primary focus:border-transparent`}
                  placeholder="Enter your current password"
                />
                {passwordErrors.currentPassword && (
                  <p className="mt-1 text-sm text-red-600">{passwordErrors.currentPassword}</p>
                )}
              </div>

              {/* New Password */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  New Password
                </label>
                <input
                  type="password"
                  name="newPassword"
                  value={passwordData.newPassword}
                  onChange={handlePasswordInputChange}
                  className={`w-full px-4 py-2 border ${
                    passwordErrors.newPassword ? 'border-red-300' : 'border-gray-300'
                  } rounded-lg focus:ring-2 focus:ring-primary focus:border-transparent`}
                  placeholder="Enter your new password"
                />
                {passwordErrors.newPassword && (
                  <p className="mt-1 text-sm text-red-600">{passwordErrors.newPassword}</p>
                )}
                <p className="mt-1 text-xs text-gray-500">
                  Must be at least 8 characters with letters and numbers
                </p>
              </div>

              {/* Confirm New Password */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Confirm New Password
                </label>
                <input
                  type="password"
                  name="confirmPassword"
                  value={passwordData.confirmPassword}
                  onChange={handlePasswordInputChange}
                  className={`w-full px-4 py-2 border ${
                    passwordErrors.confirmPassword ? 'border-red-300' : 'border-gray-300'
                  } rounded-lg focus:ring-2 focus:ring-primary focus:border-transparent`}
                  placeholder="Confirm your new password"
                />
                {passwordErrors.confirmPassword && (
                  <p className="mt-1 text-sm text-red-600">{passwordErrors.confirmPassword}</p>
                )}
              </div>

              {/* Submit Button */}
              <button
                type="submit"
                disabled={passwordLoading}
                className="w-full bg-primary hover:bg-primary-dark text-white font-semibold py-3 px-4 rounded-lg transition duration-200 disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center"
              >
                {passwordLoading ? (
                  <>
                    <div className="animate-spin rounded-full h-5 w-5 border-b-2 border-white mr-2"></div>
                    Changing Password...
                  </>
                ) : (
                  'Change Password'
                )}
              </button>
            </form>
          </div>
        </div>
      </div>
    </>
  );
};

export default ProfilePage;
