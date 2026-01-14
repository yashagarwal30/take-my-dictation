import React from 'react';
import { useNavigate } from 'react-router-dom';
import Navbar from '../components/Navbar';
import Footer from '../components/Footer';
import { FaMicrophone, FaFileAlt, FaRocket, FaClock } from 'react-icons/fa';

const LandingPage = () => {
  const navigate = useNavigate();

  const handleGetStarted = () => {
    navigate('/record');
  };

  return (
    <div className="flex flex-col min-h-screen">
      <Navbar />

      {/* Hero Section */}
      <section className="flex-1 bg-gradient-to-br from-primary to-secondary text-white py-20">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 text-center">
          <h1 className="text-5xl md:text-6xl font-bold mb-6">
            Transform Your Voice into Actionable Insights
          </h1>
          <p className="text-xl md:text-2xl mb-8 text-gray-100">
            Record, transcribe, and get AI-powered summaries in seconds
          </p>
          <button
            onClick={handleGetStarted}
            className="bg-white text-primary hover:bg-gray-100 font-bold py-4 px-8 rounded-lg text-xl transition duration-200 shadow-lg"
          >
            Start Recording Now
          </button>
          <p className="mt-4 text-gray-200">
            No sign-up required. Start for free.
          </p>
        </div>
      </section>

      {/* Features Section */}
      <section className="py-16 bg-white">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <h2 className="text-4xl font-bold text-center mb-12 text-gray-800">
            How It Works
          </h2>

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-8">
            {/* Feature 1 */}
            <div className="bg-gray-50 rounded-lg p-6 text-center hover:shadow-lg transition">
              <div className="flex justify-center mb-4">
                <FaMicrophone className="text-primary text-5xl" />
              </div>
              <h3 className="text-xl font-semibold mb-2 text-gray-800">Record Audio</h3>
              <p className="text-gray-600">
                Start recording instantly. Pause, resume, or stop anytime.
              </p>
            </div>

            {/* Feature 2 */}
            <div className="bg-gray-50 rounded-lg p-6 text-center hover:shadow-lg transition">
              <div className="flex justify-center mb-4">
                <FaFileAlt className="text-secondary text-5xl" />
              </div>
              <h3 className="text-xl font-semibold mb-2 text-gray-800">Get Transcript</h3>
              <p className="text-gray-600">
                AI transcribes your audio with high accuracy using OpenAI Whisper.
              </p>
            </div>

            {/* Feature 3 */}
            <div className="bg-gray-50 rounded-lg p-6 text-center hover:shadow-lg transition">
              <div className="flex justify-center mb-4">
                <FaRocket className="text-accent text-5xl" />
              </div>
              <h3 className="text-xl font-semibold mb-2 text-gray-800">AI Summary</h3>
              <p className="text-gray-600">
                Get intelligent summaries with key points and action items.
              </p>
            </div>

            {/* Feature 4 */}
            <div className="bg-gray-50 rounded-lg p-6 text-center hover:shadow-lg transition">
              <div className="flex justify-center mb-4">
                <FaClock className="text-primary text-5xl" />
              </div>
              <h3 className="text-xl font-semibold mb-2 text-gray-800">Save Time</h3>
              <p className="text-gray-600">
                Export to Word or PDF. No more manual note-taking.
              </p>
            </div>
          </div>
        </div>
      </section>

      {/* CTA Section */}
      <section className="py-16 bg-gray-100">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 text-center">
          <h2 className="text-4xl font-bold mb-6 text-gray-800">
            Ready to Get Started?
          </h2>
          <p className="text-xl text-gray-600 mb-8">
            Join thousands of users who are saving time with AI-powered transcription.
          </p>
          <button
            onClick={handleGetStarted}
            className="bg-primary hover:bg-primary-dark text-white font-bold py-4 px-8 rounded-lg text-xl transition duration-200 shadow-lg"
          >
            Start Your First Recording
          </button>
        </div>
      </section>

      <Footer />
    </div>
  );
};

export default LandingPage;
