import React, { useState, useContext, useEffect } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import Navbar from '../components/Navbar';
import Footer from '../components/Footer';
import { UserContext } from '../context/UserContext';
import { apiService } from '../utils/api';
import { FaCheck } from 'react-icons/fa';

const SubscriptionPage = () => {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const { user } = useContext(UserContext);
  const [loading, setLoading] = useState(null);
  const [error, setError] = useState(null);
  const [success, setSuccess] = useState(false);
  const [billingInterval, setBillingInterval] = useState('monthly'); // 'monthly' or 'annual'

  useEffect(() => {
    // Check for successful payment
    if (searchParams.get('success') === 'true') {
      setSuccess(true);
    } else if (searchParams.get('canceled') === 'true') {
      setError('Payment was canceled. Please try again.');
    }
  }, [searchParams]);

  const handleSubscribe = async (plan) => {
    if (!user) {
      navigate('/login');
      return;
    }

    setLoading(plan);
    setError(null);

    try {
      const response = await apiService.createCheckoutSession(plan.toLowerCase(), billingInterval);
      // Redirect to Stripe checkout
      window.location.href = response.data.url;
    } catch (err) {
      console.error('Subscription error:', err);
      setError(err.response?.data?.detail || 'Failed to create checkout session. Please try again.');
      setLoading(null);
    }
  };

  const getPrice = (plan) => {
    const prices = {
      basic: { monthly: 9.99, annual: 99 },
      pro: { monthly: 19.99, annual: 199 }
    };
    return prices[plan][billingInterval];
  };

  const getAnnualSavings = (plan) => {
    const prices = {
      basic: { monthly: 9.99, annual: 99 },
      pro: { monthly: 19.99, annual: 199 }
    };
    const monthlyTotal = prices[plan].monthly * 12;
    const annualPrice = prices[plan].annual;
    const savings = monthlyTotal - annualPrice;
    const savingsPercent = Math.round((savings / monthlyTotal) * 100);
    return { amount: savings.toFixed(2), percent: savingsPercent };
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

          <div className="grid grid-cols-1 md:grid-cols-2 gap-8 max-w-5xl mx-auto">
            {/* Basic Plan */}
            <div className="bg-white rounded-lg shadow-lg p-8 border-2 border-gray-200">
              <h3 className="text-2xl font-bold text-gray-800 mb-4">Basic</h3>
              <div className="mb-6">
                <div className="text-5xl font-bold text-gray-900">
                  ${getPrice('basic')}<span className="text-lg text-gray-500">/{billingInterval === 'monthly' ? 'mo' : 'yr'}</span>
                </div>
                {billingInterval === 'annual' && (
                  <p className="text-sm text-green-600 font-semibold mt-2">
                    Save ${getAnnualSavings('basic').amount} per year
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
                className="w-full bg-primary hover:bg-primary-dark text-white font-semibold py-3 px-6 rounded-lg transition duration-200 disabled:opacity-50"
              >
                {loading === 'basic' ? 'Processing...' : 'Get Basic'}
              </button>
            </div>

            {/* Pro Plan */}
            <div className="bg-gradient-to-br from-primary to-secondary rounded-lg shadow-xl p-8 transform md:scale-105 border-2 border-primary">
              <div className="bg-yellow-400 text-gray-900 text-xs font-bold px-3 py-1 rounded-full inline-block mb-4">
                MOST POPULAR
              </div>
              <h3 className="text-2xl font-bold text-white mb-4">Pro</h3>
              <div className="mb-6">
                <div className="text-5xl font-bold text-white">
                  ${getPrice('pro')}<span className="text-lg text-gray-200">/{billingInterval === 'monthly' ? 'mo' : 'yr'}</span>
                </div>
                {billingInterval === 'annual' && (
                  <p className="text-sm text-yellow-300 font-semibold mt-2">
                    Save ${getAnnualSavings('pro').amount} per year
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
                className="w-full bg-white text-primary hover:bg-gray-100 font-semibold py-3 px-6 rounded-lg transition duration-200 disabled:opacity-50"
              >
                {loading === 'pro' ? 'Processing...' : 'Get Pro'}
              </button>
            </div>
          </div>

          {/* Feature Comparison Table */}
          <div className="mt-16 max-w-5xl mx-auto">
            <h2 className="text-3xl font-bold text-center mb-8 text-gray-800">Compare Plans</h2>
            <div className="bg-white rounded-lg shadow-lg overflow-hidden">
              <table className="w-full">
                <thead className="bg-gray-50">
                  <tr>
                    <th className="px-6 py-4 text-left text-sm font-semibold text-gray-700">Feature</th>
                    <th className="px-6 py-4 text-center text-sm font-semibold text-gray-700">Trial</th>
                    <th className="px-6 py-4 text-center text-sm font-semibold text-gray-700">Basic</th>
                    <th className="px-6 py-4 text-center text-sm font-semibold text-gray-700 bg-primary/10">Pro</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-200">
                  <tr>
                    <td className="px-6 py-4 text-sm text-gray-700">Recording time</td>
                    <td className="px-6 py-4 text-center text-sm text-gray-700">10 minutes</td>
                    <td className="px-6 py-4 text-center text-sm text-gray-700">10 hours/mo</td>
                    <td className="px-6 py-4 text-center text-sm text-gray-700 bg-primary/5">50 hours/mo</td>
                  </tr>
                  <tr>
                    <td className="px-6 py-4 text-sm text-gray-700">AI transcription</td>
                    <td className="px-6 py-4 text-center"><FaCheck className="text-green-500 mx-auto" /></td>
                    <td className="px-6 py-4 text-center"><FaCheck className="text-green-500 mx-auto" /></td>
                    <td className="px-6 py-4 text-center bg-primary/5"><FaCheck className="text-green-500 mx-auto" /></td>
                  </tr>
                  <tr>
                    <td className="px-6 py-4 text-sm text-gray-700">Summary formats</td>
                    <td className="px-6 py-4 text-center text-sm text-gray-700">4 formats</td>
                    <td className="px-6 py-4 text-center text-sm text-gray-700">4 formats</td>
                    <td className="px-6 py-4 text-center text-sm text-gray-700 bg-primary/5">4 formats</td>
                  </tr>
                  <tr>
                    <td className="px-6 py-4 text-sm text-gray-700">Save to dashboard</td>
                    <td className="px-6 py-4 text-center text-sm text-gray-400">-</td>
                    <td className="px-6 py-4 text-center"><FaCheck className="text-green-500 mx-auto" /></td>
                    <td className="px-6 py-4 text-center bg-primary/5"><FaCheck className="text-green-500 mx-auto" /></td>
                  </tr>
                  <tr>
                    <td className="px-6 py-4 text-sm text-gray-700">Audio retention</td>
                    <td className="px-6 py-4 text-center text-sm text-gray-400">-</td>
                    <td className="px-6 py-4 text-center text-sm text-gray-400">-</td>
                    <td className="px-6 py-4 text-center text-sm text-gray-700 bg-primary/5">10 days</td>
                  </tr>
                  <tr>
                    <td className="px-6 py-4 text-sm text-gray-700">Regenerate summaries</td>
                    <td className="px-6 py-4 text-center text-sm text-gray-400">-</td>
                    <td className="px-6 py-4 text-center text-sm text-gray-400">-</td>
                    <td className="px-6 py-4 text-center bg-primary/5"><FaCheck className="text-green-500 mx-auto" /></td>
                  </tr>
                  <tr>
                    <td className="px-6 py-4 text-sm text-gray-700">Export Word/PDF</td>
                    <td className="px-6 py-4 text-center"><FaCheck className="text-green-500 mx-auto" /></td>
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
