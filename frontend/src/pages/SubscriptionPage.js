import React, { useState, useContext, useEffect } from 'react';
import { useNavigate, useSearchParams, useLocation } from 'react-router-dom';
import Navbar from '../components/Navbar';
import Footer from '../components/Footer';
import { UserContext } from '../context/UserContext';
import { apiService } from '../utils/api';
import { FaCheck } from 'react-icons/fa';

const SubscriptionPage = () => {
  const navigate = useNavigate();
  const location = useLocation();
  const [searchParams] = useSearchParams();
  const { user } = useContext(UserContext);
  const [loading, setLoading] = useState(null);
  const [error, setError] = useState(null);
  const [success, setSuccess] = useState(false);
  const [billingInterval, setBillingInterval] = useState('monthly'); // 'monthly' or 'annual'
  const [redirectMessage, setRedirectMessage] = useState(null);
  const [verifying, setVerifying] = useState(false);

  useEffect(() => {
    // Check for successful payment
    if (searchParams.get('success') === 'true') {
      setSuccess(true);
    } else if (searchParams.get('canceled') === 'true') {
      setError('Payment was canceled. Please try again.');
    }

    // Check if redirected with a message
    if (location.state?.message) {
      setRedirectMessage(location.state.message);
    }
  }, [searchParams, location]);

  // Verification function to poll backend for subscription activation
  const verifySubscriptionActivation = async (maxAttempts = 20) => {
    // First, try webhook-based verification (poll user data)
    for (let i = 0; i < Math.floor(maxAttempts * 0.6); i++) {
      try {
        const response = await apiService.getCurrentUser();
        const userData = response.data;

        console.log(`Verification attempt ${i + 1}:`, {
          subscription_tier: userData.subscription_tier,
          monthly_hours_limit: userData.monthly_hours_limit,
          razorpay_subscription_id: userData.razorpay_subscription_id
        });

        // Check if subscription was activated - check for monthly_hours_limit or subscription_tier change
        if (userData.monthly_hours_limit && userData.monthly_hours_limit > 0) {
          console.log('Subscription verified successfully via webhook!');
          return { success: true, user: userData };
        }

        // Wait 2 seconds before next attempt
        await new Promise(resolve => setTimeout(resolve, 2000));
      } catch (err) {
        console.error('Error verifying subscription:', err);
      }
    }

    console.log('Webhook verification timed out, trying manual verification...');

    // If webhook hasn't arrived yet, try manual verification with Razorpay
    try {
      const verifyResponse = await apiService.verifySubscription();
      const verifyData = verifyResponse.data;

      console.log('Manual verification result:', verifyData);

      if (verifyData.success) {
        // Fetch updated user data
        const userResponse = await apiService.getCurrentUser();
        return { success: true, user: userResponse.data };
      } else {
        // Payment still processing
        console.log('Payment still processing:', verifyData.message);
      }
    } catch (err) {
      console.error('Error during manual verification:', err);
    }

    // Continue polling for a bit longer after manual verification
    for (let i = 0; i < Math.floor(maxAttempts * 0.4); i++) {
      try {
        const response = await apiService.getCurrentUser();
        const userData = response.data;

        if (userData.monthly_hours_limit && userData.monthly_hours_limit > 0) {
          console.log('Subscription verified successfully after manual check!');
          return { success: true, user: userData };
        }

        await new Promise(resolve => setTimeout(resolve, 2000));
      } catch (err) {
        console.error('Error verifying subscription:', err);
      }
    }

    console.log('Verification timed out after all attempts');
    return { success: false };
  };

  const handleSubscribe = async (plan) => {
    if (!user) {
      navigate('/login');
      return;
    }

    setLoading(plan);
    setError(null);

    try {
      // Map frontend interval values to backend expected values
      const backendInterval = billingInterval === 'monthly' ? 'month' : 'year';
      const response = await apiService.createCheckoutSession(plan.toLowerCase(), backendInterval);

      // Razorpay returns subscription_id and key_id
      const { subscription_id, key_id } = response.data;

      // Initialize Razorpay Checkout modal
      const options = {
        key: key_id,
        subscription_id: subscription_id,
        name: "Take My Dictation",
        description: `${plan.charAt(0).toUpperCase() + plan.slice(1)} Plan - ${billingInterval === 'monthly' ? 'Monthly' : 'Annual'} Subscription`,
        handler: async function (response) {
          // Payment successful
          console.log('Payment successful:', response);

          // Show verifying state
          setVerifying(true);
          setLoading(null);

          // Poll backend to verify subscription activation
          const result = await verifySubscriptionActivation();

          if (result.success) {
            // Clear trial mode from localStorage
            localStorage.removeItem('isTrial');

            // Dispatch event to notify components about subscription update
            window.dispatchEvent(new Event('subscriptionUpdated'));

            // Redirect to dashboard with success message
            navigate('/dashboard', {
              state: {
                successMessage: `Subscription activated! Welcome to ${result.user.subscription_tier} plan.`
              }
            });
          } else {
            // Timeout - payment received but activation taking longer
            setVerifying(false);
            setError(
              <div>
                <p className="font-semibold mb-2">Your payment was received but subscription activation is taking longer than expected.</p>
                <p className="mb-2">This usually happens when webhooks are delayed. Please try:</p>
                <ol className="list-decimal list-inside mb-3">
                  <li>Wait a moment and click the "Retry Verification" button below</li>
                  <li>Refresh the page and check your dashboard</li>
                  <li>If the issue persists after 5 minutes, contact support</li>
                </ol>
                <button
                  onClick={async () => {
                    setError(null);
                    setVerifying(true);
                    const result = await verifySubscriptionActivation();
                    if (result.success) {
                      navigate('/dashboard', {
                        state: {
                          successMessage: `Subscription activated! Welcome to ${result.user.subscription_tier} plan.`
                        }
                      });
                    } else {
                      setVerifying(false);
                      setError('Still unable to verify. Please wait a few minutes and refresh the page, or contact support.');
                    }
                  }}
                  className="bg-primary hover:bg-primary-dark text-white font-semibold py-2 px-4 rounded-lg transition duration-200"
                >
                  Retry Verification
                </button>
              </div>
            );

            // Don't auto-redirect, let user retry manually
          }
        },
        prefill: {
          name: user.full_name || '',
          email: user.email || '',
        },
        theme: {
          color: "#4F46E5"  // Primary color
        },
        modal: {
          ondismiss: function() {
            setLoading(null);
            setVerifying(false);
            setError('Payment was canceled. Please try again.');
          }
        }
      };

      // Open Razorpay modal
      const razorpay = new window.Razorpay(options);
      razorpay.open();

    } catch (err) {
      console.error('Subscription error:', err);
      setError(err.response?.data?.detail || 'Failed to create checkout session. Please try again.');
      setLoading(null);
    }
  };

  const getPrice = (plan) => {
    const prices = {
      basic: { monthly: 999, annual: 9999 },
      pro: { monthly: 1999, annual: 19999 }
    };
    return prices[plan][billingInterval];
  };

  const getAnnualSavings = (plan) => {
    const prices = {
      basic: { monthly: 999, annual: 9999 },
      pro: { monthly: 1999, annual: 19999 }
    };
    const monthlyTotal = prices[plan].monthly * 12;
    const annualPrice = prices[plan].annual;
    const savings = monthlyTotal - annualPrice;
    const savingsPercent = Math.round((savings / monthlyTotal) * 100);
    return { amount: savings.toFixed(0), percent: savingsPercent };
  };

  return (
    <div className="flex flex-col min-h-screen">
      <Navbar />

      <main className="flex-1 bg-gray-50 py-12">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="text-center mb-8">
            <h1 className="text-4xl font-bold text-gray-800 mb-4">Choose Your Plan</h1>
            <p className="text-xl text-gray-600 mb-6">
              Unlock unlimited transcription and AI-powered summaries
            </p>

            {/* Billing Toggle */}
            <div className="inline-flex items-center bg-white rounded-lg shadow-md p-1 mb-8">
              <button
                onClick={() => setBillingInterval('monthly')}
                className={`px-6 py-3 rounded-lg font-semibold transition duration-200 ${
                  billingInterval === 'monthly'
                    ? 'bg-primary text-white'
                    : 'text-gray-600 hover:text-gray-800'
                }`}
              >
                Monthly
              </button>
              <button
                onClick={() => setBillingInterval('annual')}
                className={`px-6 py-3 rounded-lg font-semibold transition duration-200 ${
                  billingInterval === 'annual'
                    ? 'bg-primary text-white'
                    : 'text-gray-600 hover:text-gray-800'
                }`}
              >
                Annual
                <span className="ml-2 text-xs bg-green-500 text-white px-2 py-1 rounded">
                  Save {getAnnualSavings('pro').percent}%
                </span>
              </button>
            </div>
          </div>

          {redirectMessage && (
            <div className="mb-6 bg-yellow-100 border border-yellow-400 text-yellow-800 px-4 py-3 rounded">
              {redirectMessage}
            </div>
          )}

          {verifying && (
            <div className="mb-6 bg-blue-100 border border-blue-400 text-blue-700 px-4 py-3 rounded flex items-center">
              <div className="inline-block animate-spin rounded-full h-5 w-5 border-b-2 border-blue-700 mr-3"></div>
              <span>Processing payment and activating subscription... Please wait.</span>
            </div>
          )}

          {success && (
            <div className="mb-6 bg-green-100 border border-green-400 text-green-700 px-4 py-3 rounded">
              Subscription successful! Your account has been upgraded.
            </div>
          )}

          {error && (
            <div className="mb-6 bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded">
              {error}
            </div>
          )}

          <div className="grid grid-cols-1 md:grid-cols-2 gap-8 max-w-5xl mx-auto items-stretch">
            {/* Basic Plan */}
            <div className="bg-white rounded-lg shadow-lg p-8 border-2 border-gray-200 flex flex-col">
              <h3 className="text-2xl font-bold text-gray-800 mb-4">Basic</h3>
              <div className="mb-6">
                <div className="text-5xl font-bold text-gray-900">
                  ₹{getPrice('basic')}<span className="text-lg text-gray-500">/{billingInterval === 'monthly' ? 'mo' : 'yr'}</span>
                </div>
                {billingInterval === 'annual' && (
                  <p className="text-sm text-green-600 font-semibold mt-2">
                    Save ₹{getAnnualSavings('basic').amount} per year
                  </p>
                )}
              </div>
              <ul className="space-y-3 mb-8">
                <li className="flex items-center">
                  <FaCheck className="text-green-500 mr-2 flex-shrink-0" />
                  <span>10 hours per month</span>
                </li>
                <li className="flex items-center">
                  <FaCheck className="text-green-500 mr-2 flex-shrink-0" />
                  <span>AI-powered transcription</span>
                </li>
                <li className="flex items-center">
                  <FaCheck className="text-green-500 mr-2 flex-shrink-0" />
                  <span>4 summary formats</span>
                </li>
                <li className="flex items-center">
                  <FaCheck className="text-green-500 mr-2 flex-shrink-0" />
                  <span>Save to dashboard</span>
                </li>
                <li className="flex items-center">
                  <FaCheck className="text-green-500 mr-2 flex-shrink-0" />
                  <span>Export to Word/PDF</span>
                </li>
                <li className="flex items-center">
                  <FaCheck className="text-green-500 mr-2 flex-shrink-0" />
                  <span>Email support</span>
                </li>
              </ul>
              <button
                onClick={() => handleSubscribe('basic')}
                disabled={loading === 'basic'}
                className="w-full bg-primary hover:bg-primary-dark text-white font-semibold py-3 px-6 rounded-lg transition duration-200 disabled:opacity-50 mt-auto"
              >
                {loading === 'basic' ? 'Processing...' : 'Get Basic'}
              </button>
            </div>

            {/* Pro Plan */}
            <div className="bg-gradient-to-br from-primary to-secondary rounded-lg shadow-xl p-8 border-2 border-primary flex flex-col relative">
              <div className="absolute -top-4 left-1/2 transform -translate-x-1/2 bg-yellow-400 text-gray-900 text-xs font-bold px-3 py-1 rounded-full whitespace-nowrap">
                MOST POPULAR
              </div>
              <h3 className="text-2xl font-bold text-white mb-4 mt-2">Pro</h3>
              <div className="mb-6">
                <div className="text-5xl font-bold text-white">
                  ₹{getPrice('pro')}<span className="text-lg text-gray-200">/{billingInterval === 'monthly' ? 'mo' : 'yr'}</span>
                </div>
                {billingInterval === 'annual' && (
                  <p className="text-sm text-yellow-300 font-semibold mt-2">
                    Save ₹{getAnnualSavings('pro').amount} per year
                  </p>
                )}
              </div>
              <ul className="space-y-3 mb-8 text-white">
                <li className="flex items-center">
                  <FaCheck className="text-yellow-300 mr-2 flex-shrink-0" />
                  <span>50 hours per month</span>
                </li>
                <li className="flex items-center">
                  <FaCheck className="text-yellow-300 mr-2 flex-shrink-0" />
                  <span>AI-powered transcription</span>
                </li>
                <li className="flex items-center">
                  <FaCheck className="text-yellow-300 mr-2 flex-shrink-0" />
                  <span>4 summary formats</span>
                </li>
                <li className="flex items-center">
                  <FaCheck className="text-yellow-300 mr-2 flex-shrink-0" />
                  <span>10-day audio retention</span>
                </li>
                <li className="flex items-center">
                  <FaCheck className="text-yellow-300 mr-2 flex-shrink-0" />
                  <span>Regenerate summaries</span>
                </li>
                <li className="flex items-center">
                  <FaCheck className="text-yellow-300 mr-2 flex-shrink-0" />
                  <span>Save to dashboard</span>
                </li>
                <li className="flex items-center">
                  <FaCheck className="text-yellow-300 mr-2 flex-shrink-0" />
                  <span>Export to Word/PDF</span>
                </li>
                <li className="flex items-center">
                  <FaCheck className="text-yellow-300 mr-2 flex-shrink-0" />
                  <span>Priority support</span>
                </li>
              </ul>
              <button
                onClick={() => handleSubscribe('pro')}
                disabled={loading === 'pro'}
                className="w-full bg-white text-primary hover:bg-gray-100 font-semibold py-3 px-6 rounded-lg transition duration-200 disabled:opacity-50 mt-auto"
              >
                {loading === 'pro' ? 'Processing...' : 'Get Pro'}
              </button>
            </div>
          </div>

          {/* Feature Comparison Table */}
          <div className="mt-16 max-w-4xl mx-auto">
            <h2 className="text-3xl font-bold text-center mb-8 text-gray-800">Compare Plans</h2>
            <div className="bg-white rounded-lg shadow-lg overflow-hidden">
              <table className="w-full">
                <thead className="bg-gray-50">
                  <tr>
                    <th className="px-6 py-4 text-left text-sm font-semibold text-gray-700 w-1/2">Feature</th>
                    <th className="px-6 py-4 text-center text-sm font-semibold text-gray-700 w-1/4">Basic</th>
                    <th className="px-6 py-4 text-center text-sm font-semibold text-gray-700 bg-primary/10 w-1/4">Pro</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-200">
                  <tr>
                    <td className="px-6 py-4 text-sm text-gray-700">Recording time</td>
                    <td className="px-6 py-4 text-center text-sm text-gray-700">10 hours/mo</td>
                    <td className="px-6 py-4 text-center text-sm text-gray-700 bg-primary/5">50 hours/mo</td>
                  </tr>
                  <tr>
                    <td className="px-6 py-4 text-sm text-gray-700">AI transcription</td>
                    <td className="px-6 py-4 text-center"><FaCheck className="text-green-500 mx-auto" /></td>
                    <td className="px-6 py-4 text-center bg-primary/5"><FaCheck className="text-green-500 mx-auto" /></td>
                  </tr>
                  <tr>
                    <td className="px-6 py-4 text-sm text-gray-700">Summary formats</td>
                    <td className="px-6 py-4 text-center text-sm text-gray-700">4 formats</td>
                    <td className="px-6 py-4 text-center text-sm text-gray-700 bg-primary/5">4 formats</td>
                  </tr>
                  <tr>
                    <td className="px-6 py-4 text-sm text-gray-700">Save to dashboard</td>
                    <td className="px-6 py-4 text-center"><FaCheck className="text-green-500 mx-auto" /></td>
                    <td className="px-6 py-4 text-center bg-primary/5"><FaCheck className="text-green-500 mx-auto" /></td>
                  </tr>
                  <tr>
                    <td className="px-6 py-4 text-sm text-gray-700">Audio retention</td>
                    <td className="px-6 py-4 text-center text-sm text-gray-400">-</td>
                    <td className="px-6 py-4 text-center text-sm text-gray-700 bg-primary/5">10 days</td>
                  </tr>
                  <tr>
                    <td className="px-6 py-4 text-sm text-gray-700">Regenerate summaries</td>
                    <td className="px-6 py-4 text-center text-sm text-gray-400">-</td>
                    <td className="px-6 py-4 text-center bg-primary/5"><FaCheck className="text-green-500 mx-auto" /></td>
                  </tr>
                  <tr>
                    <td className="px-6 py-4 text-sm text-gray-700">Export Word/PDF</td>
                    <td className="px-6 py-4 text-center"><FaCheck className="text-green-500 mx-auto" /></td>
                    <td className="px-6 py-4 text-center bg-primary/5"><FaCheck className="text-green-500 mx-auto" /></td>
                  </tr>
                </tbody>
              </table>
            </div>
          </div>
        </div>
      </main>

      <Footer />
    </div>
  );
};

export default SubscriptionPage;
