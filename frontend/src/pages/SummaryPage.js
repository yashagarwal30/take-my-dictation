import { useEffect, useState, useCallback } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import Navbar from '../components/Navbar';
import Footer from '../components/Footer';
import { apiService } from '../utils/api';
import { FaFileWord, FaFilePdf, FaFileAlt, FaListUl, FaClipboardList, FaBolt, FaCrown } from 'react-icons/fa';

const SummaryPage = () => {
  const navigate = useNavigate();
  const location = useLocation();
  const { recordingId } = location.state || {};

  const [transcription, setTranscription] = useState('');
  const [summary, setSummary] = useState('');
  const [loading, setLoading] = useState(true);
  const [generatingSummary, setGeneratingSummary] = useState(false);
  const [error, setError] = useState(null);
  const [isTrial, setIsTrial] = useState(false);

  useEffect(() => {
    // Check if user is in trial mode
    const trialMode = localStorage.getItem('isTrial') === 'true';
    setIsTrial(trialMode);
  }, []);

  const fetchData = useCallback(async () => {
    try {
      setLoading(true);

      // Fetch transcription
      const transcriptionResponse = await apiService.getTranscription(recordingId);
      setTranscription(transcriptionResponse.data.text);

      // Try to fetch summary if it exists (optional - don't fail if it doesn't exist)
      try {
        const summaryResponse = await apiService.getSummary(recordingId);
        setSummary(summaryResponse.data.summary_text);
      } catch (summaryErr) {
        // Summary doesn't exist yet - that's OK, user will generate it
        console.log('No summary yet, user will generate one');
        setSummary('');
      }

      setLoading(false);
    } catch (err) {
      console.error('Error fetching data:', err);
      setError('Failed to load transcription.');
      setLoading(false);
    }
  }, [recordingId]);

  useEffect(() => {
    if (!recordingId) {
      navigate('/record');
      return;
    }

    fetchData();
  }, [recordingId, navigate, fetchData]);

  const handleGenerateSummary = async (formatType) => {
    setGeneratingSummary(true);
    setError(null);

    try {
      let format = 'quick_summary';

      switch (formatType) {
        case 'meeting':
          format = 'meeting_notes';
          break;
        case 'product':
          format = 'product_spec';
          break;
        case 'mom':
          format = 'mom';
          break;
        case 'quick':
          format = 'quick_summary';
          break;
        default:
          format = 'quick_summary';
      }

      const response = await apiService.generateSummary(recordingId, format, null);
      setSummary(response.data.summary_text);
      setGeneratingSummary(false);
    } catch (err) {
      console.error('Error generating summary:', err);
      setError('Failed to generate summary. Please try again.');
      setGeneratingSummary(false);
    }
  };

  const handleDownload = async (format) => {
    try {
      let response;
      let filename;
      let mimeType;

      if (format === 'word') {
        response = await apiService.exportWord(recordingId);
        filename = `transcript_${recordingId}.docx`;
        mimeType = 'application/vnd.openxmlformats-officedocument.wordprocessingml.document';
      } else if (format === 'pdf') {
        response = await apiService.exportPdf(recordingId);
        filename = `transcript_${recordingId}.pdf`;
        mimeType = 'application/pdf';
      } else {
        // Text format (fallback)
        const content = `TRANSCRIPTION:\n\n${transcription}\n\n\nSUMMARY:\n\n${summary}`;
        const blob = new Blob([content], { type: 'text/plain' });
        const url = URL.createObjectURL(blob);
        const element = document.createElement('a');
        element.href = url;
        element.download = `transcript_${recordingId}.txt`;
        document.body.appendChild(element);
        element.click();
        document.body.removeChild(element);
        URL.revokeObjectURL(url);
        return;
      }

      // Create blob and download
      const blob = new Blob([response.data], { type: mimeType });
      const url = URL.createObjectURL(blob);
      const element = document.createElement('a');
      element.href = url;
      element.download = filename;
      document.body.appendChild(element);
      element.click();
      document.body.removeChild(element);
      URL.revokeObjectURL(url);
    } catch (err) {
      console.error('Download error:', err);
      setError('Failed to download file. Please try again.');
    }
  };

  if (loading) {
    return (
      <div className="flex flex-col min-h-screen">
        <Navbar />
        <main className="flex-1 flex items-center justify-center">
          <div className="text-center">
            <div className="inline-block animate-spin rounded-full h-12 w-12 border-b-2 border-primary mb-4"></div>
            <p className="text-lg text-gray-700">Loading your transcription and summary...</p>
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
          {/* Trial Upgrade CTA */}
          {isTrial && (
            <div className="mb-6 bg-gradient-to-r from-purple-600 to-indigo-600 rounded-lg shadow-xl p-8 text-white">
              <div className="flex items-center justify-between">
                <div className="flex-1">
                  <div className="flex items-center space-x-3 mb-3">
                    <FaCrown className="text-4xl text-yellow-300" />
                    <h2 className="text-3xl font-bold">Upgrade to Save Your Summaries</h2>
                  </div>
                  <p className="text-lg text-purple-100 mb-4">
                    Subscribe to save summaries to your dashboard and get unlimited recording time
                  </p>
                  <ul className="space-y-2 text-purple-100">
                    <li className="flex items-center">
                      <span className="mr-2">✓</span>
                      <span>Save unlimited summaries to dashboard</span>
                    </li>
                    <li className="flex items-center">
                      <span className="mr-2">✓</span>
                      <span>10 hours/month recording time (Basic) or 50 hours/month (Pro)</span>
                    </li>
                    <li className="flex items-center">
                      <span className="mr-2">✓</span>
                      <span>Multiple summary formats</span>
                    </li>
                    <li className="flex items-center">
                      <span className="mr-2">✓</span>
                      <span>Export to Word and PDF</span>
                    </li>
                  </ul>
                </div>
                <div className="ml-8">
                  <button
                    onClick={() => navigate('/subscribe')}
                    className="bg-yellow-400 hover:bg-yellow-300 text-gray-900 font-bold py-4 px-8 rounded-lg text-xl transition duration-200 shadow-lg transform hover:scale-105"
                  >
                    View Plans
                  </button>
                  <p className="text-center text-sm text-purple-200 mt-2">Starting at $9.99/month</p>
                </div>
              </div>
            </div>
          )}

          {error && (
            <div className="mb-6 bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded">
              {error}
            </div>
          )}

          {/* Summary Format Buttons */}
          <div className="bg-white rounded-lg shadow-lg p-6 mb-6">
            <h2 className="text-2xl font-bold mb-4 text-gray-800">Generate Summary Format</h2>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
              <button
                onClick={() => handleGenerateSummary('meeting')}
                disabled={generatingSummary}
                className="flex items-center justify-center space-x-2 bg-primary hover:bg-primary-dark text-white font-semibold py-3 px-4 rounded-lg transition duration-200 disabled:opacity-50"
              >
                <FaListUl />
                <span>Meeting Notes</span>
              </button>

              <button
                onClick={() => handleGenerateSummary('product')}
                disabled={generatingSummary}
                className="flex items-center justify-center space-x-2 bg-secondary hover:bg-purple-700 text-white font-semibold py-3 px-4 rounded-lg transition duration-200 disabled:opacity-50"
              >
                <FaFileAlt />
                <span>Product Spec</span>
              </button>

              <button
                onClick={() => handleGenerateSummary('mom')}
                disabled={generatingSummary}
                className="flex items-center justify-center space-x-2 bg-accent hover:bg-green-600 text-white font-semibold py-3 px-4 rounded-lg transition duration-200 disabled:opacity-50"
              >
                <FaClipboardList />
                <span>Minutes of Meeting</span>
              </button>

              <button
                onClick={() => handleGenerateSummary('quick')}
                disabled={generatingSummary}
                className="flex items-center justify-center space-x-2 bg-yellow-500 hover:bg-yellow-600 text-white font-semibold py-3 px-4 rounded-lg transition duration-200 disabled:opacity-50"
              >
                <FaBolt />
                <span>Quick Summary</span>
              </button>
            </div>

            {generatingSummary && (
              <div className="mt-4 text-center">
                <div className="inline-block animate-spin rounded-full h-6 w-6 border-b-2 border-primary mr-2"></div>
                <span className="text-gray-700">Generating summary...</span>
              </div>
            )}
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {/* Transcription */}
            <div className="bg-white rounded-lg shadow-lg p-6">
              <h2 className="text-2xl font-bold mb-4 text-gray-800">Full Transcription</h2>
              <div className="bg-gray-50 rounded p-4 max-h-96 overflow-y-auto">
                <p className="text-gray-700 whitespace-pre-wrap">{transcription}</p>
              </div>
            </div>

            {/* Summary */}
            <div className="bg-white rounded-lg shadow-lg p-6">
              <h2 className="text-2xl font-bold mb-4 text-gray-800">AI-Generated Summary</h2>
              <div className="bg-gray-50 rounded p-4 max-h-96 overflow-y-auto">
                {summary ? (
                  <p className="text-gray-700 whitespace-pre-wrap">{summary}</p>
                ) : (
                  <p className="text-gray-400 italic text-center py-8">
                    Click a summary format above to generate an AI-powered summary
                  </p>
                )}
              </div>
            </div>
          </div>

          {/* Download Buttons */}
          <div className="mt-6 bg-white rounded-lg shadow-lg p-6">
            <h2 className="text-2xl font-bold mb-4 text-gray-800">Download Summary</h2>
            <div className="flex flex-wrap gap-4">
              <button
                onClick={() => handleDownload('word')}
                className="flex items-center space-x-2 bg-blue-600 hover:bg-blue-700 text-white font-semibold py-3 px-6 rounded-lg transition duration-200"
              >
                <FaFileWord />
                <span>Download Word</span>
              </button>

              <button
                onClick={() => handleDownload('pdf')}
                className="flex items-center space-x-2 bg-red-600 hover:bg-red-700 text-white font-semibold py-3 px-6 rounded-lg transition duration-200"
              >
                <FaFilePdf />
                <span>Download PDF</span>
              </button>

              <button
                onClick={() => navigate('/record')}
                className="flex items-center space-x-2 bg-accent hover:bg-green-600 text-white font-semibold py-3 px-6 rounded-lg transition duration-200"
              >
                <span>New Recording</span>
              </button>
            </div>
          </div>
        </div>
      </main>

      <Footer />
    </div>
  );
};

export default SummaryPage;
