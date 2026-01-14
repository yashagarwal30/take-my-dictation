import { useState, useRef, useEffect } from 'react';
import { FaCheckCircle, FaEnvelope } from 'react-icons/fa';

const EmailVerification = ({ email, onVerified, onResend }) => {
  const [code, setCode] = useState(['', '', '', '', '', '']);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [resendCooldown, setResendCooldown] = useState(0);
  const [timeRemaining, setTimeRemaining] = useState(900); // 15 minutes in seconds
  const inputRefs = useRef([]);

  // Countdown timer for code expiration
  useEffect(() => {
    if (timeRemaining <= 0) return;

    const timer = setInterval(() => {
      setTimeRemaining((prev) => Math.max(0, prev - 1));
    }, 1000);

    return () => clearInterval(timer);
  }, [timeRemaining]);

  // Resend cooldown timer
  useEffect(() => {
    if (resendCooldown <= 0) return;

    const timer = setInterval(() => {
      setResendCooldown((prev) => Math.max(0, prev - 1));
    }, 1000);

    return () => clearInterval(timer);
  }, [resendCooldown]);

  const handleChange = (index, value) => {
    // Only allow digits
    if (!/^\d*$/.test(value)) return;

    const newCode = [...code];
    newCode[index] = value.slice(-1); // Only take last digit
    setCode(newCode);

    // Auto-advance to next input
    if (value && index < 5) {
      inputRefs.current[index + 1]?.focus();
    }

    // Auto-submit when all digits are entered
    if (newCode.every((digit) => digit !== '') && index === 5) {
      handleVerify(newCode.join(''));
    }
  };

  const handleKeyDown = (index, e) => {
    // Handle backspace
    if (e.key === 'Backspace' && !code[index] && index > 0) {
      inputRefs.current[index - 1]?.focus();
    }
  };

  const handlePaste = (e) => {
    e.preventDefault();
    const pastedData = e.clipboardData.getData('text').replace(/\D/g, '');
    const newCode = pastedData.slice(0, 6).split('');

    // Fill remaining digits with empty strings
    while (newCode.length < 6) {
      newCode.push('');
    }

    setCode(newCode);

    // Focus on the last filled input or first empty one
    const nextIndex = Math.min(newCode.findIndex((d) => !d), 5);
    inputRefs.current[nextIndex >= 0 ? nextIndex : 5]?.focus();

    // Auto-verify if complete
    if (newCode.every((digit) => digit !== '')) {
      handleVerify(newCode.join(''));
    }
  };

  const handleVerify = async (verificationCode) => {
    setLoading(true);
    setError(null);

    try {
      await onVerified(verificationCode || code.join(''));
    } catch (err) {
      setError(err.response?.data?.detail || 'Invalid verification code. Please try again.');
      setCode(['', '', '', '', '', '']);
      inputRefs.current[0]?.focus();
    } finally {
      setLoading(false);
    }
  };

  const handleResend = async () => {
    if (resendCooldown > 0) return;

    setError(null);
    setLoading(true);

    try {
      await onResend();
      setResendCooldown(60); // 60 second cooldown
      setTimeRemaining(900); // Reset to 15 minutes
      setCode(['', '', '', '', '', '']);
      inputRefs.current[0]?.focus();
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to resend code. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  const formatTime = (seconds) => {
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins}:${secs.toString().padStart(2, '0')}`;
  };

  return (
    <div className="max-w-md mx-auto">
      <div className="bg-white rounded-lg shadow-lg p-8">
        <div className="text-center mb-6">
          <div className="inline-flex items-center justify-center w-16 h-16 bg-primary/10 rounded-full mb-4">
            <FaEnvelope className="text-3xl text-primary" />
          </div>
          <h2 className="text-2xl font-bold text-gray-800 mb-2">Check Your Email</h2>
          <p className="text-gray-600">
            We sent a 6-digit verification code to
          </p>
          <p className="text-primary font-semibold">{email}</p>
        </div>

        {error && (
          <div className="mb-4 bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded">
            {error}
          </div>
        )}

        <div className="mb-6">
          <label className="block text-sm font-medium text-gray-700 mb-3 text-center">
            Enter Verification Code
          </label>
          <div className="flex justify-center space-x-2" onPaste={handlePaste}>
            {code.map((digit, index) => (
              <input
                key={index}
                ref={(el) => (inputRefs.current[index] = el)}
                type="text"
                inputMode="numeric"
                maxLength="1"
                value={digit}
                onChange={(e) => handleChange(index, e.target.value)}
                onKeyDown={(e) => handleKeyDown(index, e)}
                disabled={loading}
                className="w-12 h-14 text-center text-2xl font-bold border-2 border-gray-300 rounded-lg focus:border-primary focus:ring-2 focus:ring-primary/20 focus:outline-none disabled:bg-gray-100 disabled:cursor-not-allowed"
                autoFocus={index === 0}
              />
            ))}
          </div>
        </div>

        {timeRemaining > 0 ? (
          <p className="text-center text-sm text-gray-600 mb-4">
            Code expires in <span className="font-semibold text-primary">{formatTime(timeRemaining)}</span>
          </p>
        ) : (
          <p className="text-center text-sm text-red-600 mb-4 font-semibold">
            Code expired. Please request a new one.
          </p>
        )}

        <div className="text-center">
          <p className="text-sm text-gray-600 mb-2">Didn't receive the code?</p>
          <button
            onClick={handleResend}
            disabled={loading || resendCooldown > 0}
            className="text-primary hover:underline font-semibold disabled:text-gray-400 disabled:no-underline disabled:cursor-not-allowed"
          >
            {resendCooldown > 0
              ? `Resend in ${resendCooldown}s`
              : 'Resend Code'}
          </button>
        </div>

        {loading && (
          <div className="mt-6 flex items-center justify-center">
            <div className="inline-block animate-spin rounded-full h-6 w-6 border-b-2 border-primary mr-2"></div>
            <span className="text-gray-700">Verifying...</span>
          </div>
        )}
      </div>

      <div className="mt-6 bg-blue-50 border border-blue-200 rounded-lg p-4">
        <div className="flex items-start">
          <FaCheckCircle className="text-blue-500 mt-1 mr-3 flex-shrink-0" />
          <div className="text-sm text-blue-800">
            <p className="font-semibold mb-1">Email Verification Tips:</p>
            <ul className="list-disc list-inside space-y-1">
              <li>Check your spam/junk folder if you don't see the email</li>
              <li>The code is valid for 15 minutes</li>
              <li>You can paste the code from your email</li>
            </ul>
          </div>
        </div>
      </div>
    </div>
  );
};

export default EmailVerification;
