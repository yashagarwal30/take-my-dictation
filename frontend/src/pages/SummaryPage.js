import { useEffect, useState, useCallback } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import Navbar from '../components/Navbar';
import Footer from '../components/Footer';
import { apiService } from '../utils/api';
import { FaFileWord, FaFilePdf, FaFileAlt, FaListUl, FaClipboardList, FaBolt } from 'react-icons/fa';

const SummaryPage = () => {
  const navigate = useNavigate();
  const location = useLocation();
  const { recordingId } = location.state || {};

  const [transcription, setTranscription] = useState('');
  const [summary, setSummary] = useState('');
  const [loading, setLoading] = useState(true);
  const [generatingSummary, setGeneratingSummary] = useState(false);
  const [error, setError] = useState(null);

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
      let customPrompt = null;

      switch (formatType) {
        case 'meeting':
          customPrompt = 'Generate a meeting notes format with attendees, discussion points, decisions, and action items.';
          break;
        case 'product':
          customPrompt = 'Generate a product specification document with problem statement, requirements, user stories, and technical considerations.';
          break;
        case 'mom':
          customPrompt = 'Generate minutes of meeting with agenda items, key discussions, decisions made, action items with owners, and next steps.';
          break;
        case 'quick':
          customPrompt = 'Generate a quick summary with just the main points in bullet format. Keep it concise.';
          break;
        default:
          customPrompt = null;
      }

      const response = await apiService.generateSummary(recordingId, customPrompt);
      setSummary(response.data.summary_text);
      setGeneratingSummary(false);
    } catch (err) {
      console.error('Error generating summary:', err);
      setError('Failed to generate summary. Please try again.');
      setGeneratingSummary(false);
    }
  };

  const handleDownload = () => {
    // This would need backend support for Word/PDF export
    // For now, we'll download as text
    const element = document.createElement('a');
    const content = `TRANSCRIPTION:\n\n${transcription}\n\n\nSUMMARY:\n\n${summary}`;
    const file = new Blob([content], { type: 'text/plain' });
    element.href = URL.createObjectURL(file);
    element.download = `summary_${recordingId}.txt`;
    document.body.appendChild(element);
    element.click();
    document.body.removeChild(element);
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
