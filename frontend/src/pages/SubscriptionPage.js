import React from 'react';
import Navbar from '../components/Navbar';
import Footer from '../components/Footer';
import { FaCheck } from 'react-icons/fa';

const SubscriptionPage = () => {
  const handleSubscribe = (plan) => {
    alert(`Subscription feature coming soon! Selected plan: ${plan}`);
    // TODO: Integrate with Stripe
  };

  return (
    <div className="flex flex-col min-h-screen">
      <Navbar />

      <main className="flex-1 bg-gray-50 py-12">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="text-center mb-12">
            <h1 className="text-4xl font-bold text-gray-800 mb-4">Choose Your Plan</h1>
            <p className="text-xl text-gray-600">
              Unlock unlimited transcription and AI-powered summaries
            </p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
            {/* Free Plan */}
            <div className="bg-white rounded-lg shadow-lg p-8">
              <h3 className="text-2xl font-bold text-gray-800 mb-4">Free</h3>
              <div className="text-4xl font-bold text-gray-900 mb-6">
                $0<span className="text-lg text-gray-500">/month</span>
              </div>
              <ul className="space-y-3 mb-8">
                <li className="flex items-center">
                  <FaCheck className="text-green-500 mr-2" />
                  <span>10 minutes per recording</span>
                </li>
                <li className="flex items-center">
                  <FaCheck className="text-green-500 mr-2" />
                  <span>Basic transcription</span>
                </li>
                <li className="flex items-center">
                  <FaCheck className="text-green-500 mr-2" />
                  <span>AI summaries</span>
                </li>
                <li className="flex items-center">
                  <FaCheck className="text-green-500 mr-2" />
                  <span>Download Word/PDF</span>
                </li>
              </ul>
              <button
                disabled
                className="w-full bg-gray-300 text-gray-600 font-semibold py-3 px-6 rounded-lg cursor-not-allowed"
              >
                Current Plan
              </button>
            </div>

            {/* Pro Plan */}
            <div className="bg-gradient-to-br from-primary to-secondary rounded-lg shadow-xl p-8 transform scale-105">
              <div className="bg-yellow-400 text-gray-900 text-xs font-bold px-3 py-1 rounded-full inline-block mb-4">
                MOST POPULAR
              </div>
              <h3 className="text-2xl font-bold text-white mb-4">Pro</h3>
              <div className="text-4xl font-bold text-white mb-6">
                $19<span className="text-lg text-gray-200">/month</span>
              </div>
              <ul className="space-y-3 mb-8 text-white">
                <li className="flex items-center">
                  <FaCheck className="text-yellow-300 mr-2" />
                  <span>10 hours per month</span>
                </li>
                <li className="flex items-center">
                  <FaCheck className="text-yellow-300 mr-2" />
                  <span>Advanced transcription</span>
                </li>
                <li className="flex items-center">
                  <FaCheck className="text-yellow-300 mr-2" />
                  <span>Unlimited AI summaries</span>
                </li>
                <li className="flex items-center">
                  <FaCheck className="text-yellow-300 mr-2" />
                  <span>Save to dashboard</span>
                </li>
                <li className="flex items-center">
                  <FaCheck className="text-yellow-300 mr-2" />
                  <span>Priority support</span>
                </li>
              </ul>
              <button
                onClick={() => handleSubscribe('Pro')}
                className="w-full bg-white text-primary hover:bg-gray-100 font-semibold py-3 px-6 rounded-lg transition duration-200"
              >
                Subscribe Now
              </button>
            </div>

            {/* Enterprise Plan */}
            <div className="bg-white rounded-lg shadow-lg p-8">
              <h3 className="text-2xl font-bold text-gray-800 mb-4">Enterprise</h3>
              <div className="text-4xl font-bold text-gray-900 mb-6">
                Custom
              </div>
              <ul className="space-y-3 mb-8">
                <li className="flex items-center">
                  <FaCheck className="text-green-500 mr-2" />
                  <span>Unlimited hours</span>
                </li>
                <li className="flex items-center">
                  <FaCheck className="text-green-500 mr-2" />
                  <span>Team collaboration</span>
                </li>
                <li className="flex items-center">
                  <FaCheck className="text-green-500 mr-2" />
                  <span>Custom AI models</span>
                </li>
                <li className="flex items-center">
                  <FaCheck className="text-green-500 mr-2" />
                  <span>API access</span>
                </li>
                <li className="flex items-center">
                  <FaCheck className="text-green-500 mr-2" />
                  <span>Dedicated support</span>
                </li>
              </ul>
              <button
                onClick={() => handleSubscribe('Enterprise')}
                className="w-full bg-gray-800 hover:bg-gray-900 text-white font-semibold py-3 px-6 rounded-lg transition duration-200"
              >
                Contact Sales
              </button>
            </div>
          </div>
        </div>
      </main>

      <Footer />
    </div>
  );
};

export default SubscriptionPage;
