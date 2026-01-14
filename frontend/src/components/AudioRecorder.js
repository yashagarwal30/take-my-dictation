import React, { useState, useRef, useEffect } from 'react';
import { FaMicrophone, FaStop, FaPause, FaPlay } from 'react-icons/fa';
import AudioWaveform from './AudioWaveform';

const AudioRecorder = ({ onRecordingComplete, maxDuration = 600 }) => {
  const [isRecording, setIsRecording] = useState(false);
  const [isPaused, setIsPaused] = useState(false);
  const [recordingTime, setRecordingTime] = useState(0);
  const [audioBlob, setAudioBlob] = useState(null);

  const mediaRecorderRef = useRef(null);
  const chunksRef = useRef([]);
  const timerRef = useRef(null);

  useEffect(() => {
    return () => {
      if (timerRef.current) {
        clearInterval(timerRef.current);
      }
    };
  }, []);

  const startRecording = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const mediaRecorder = new MediaRecorder(stream);
      mediaRecorderRef.current = mediaRecorder;
      chunksRef.current = [];

      mediaRecorder.ondataavailable = (event) => {
        if (event.data.size > 0) {
          chunksRef.current.push(event.data);
        }
      };

      mediaRecorder.onstop = () => {
        const blob = new Blob(chunksRef.current, { type: 'audio/webm' });
        setAudioBlob(blob);
        stream.getTracks().forEach(track => track.stop());
      };

      mediaRecorder.start();
      setIsRecording(true);
      setRecordingTime(0);

      // Start timer
      timerRef.current = setInterval(() => {
        setRecordingTime((prevTime) => {
          const newTime = prevTime + 1;
          // Auto-stop at max duration
          if (newTime >= maxDuration) {
            stopRecording();
            return maxDuration;
          }
          return newTime;
        });
      }, 1000);
    } catch (error) {
      console.error('Error accessing microphone:', error);
      alert('Unable to access microphone. Please check your permissions.');
    }
  };

  const pauseRecording = () => {
    if (mediaRecorderRef.current && isRecording) {
      mediaRecorderRef.current.pause();
      setIsPaused(true);
      if (timerRef.current) {
        clearInterval(timerRef.current);
      }
    }
  };

  const resumeRecording = () => {
    if (mediaRecorderRef.current && isPaused) {
      mediaRecorderRef.current.resume();
      setIsPaused(false);

      // Resume timer
      timerRef.current = setInterval(() => {
        setRecordingTime((prevTime) => {
          const newTime = prevTime + 1;
          if (newTime >= maxDuration) {
            stopRecording();
            return maxDuration;
          }
          return newTime;
        });
      }, 1000);
    }
  };

  const stopRecording = () => {
    if (mediaRecorderRef.current) {
      mediaRecorderRef.current.stop();
      setIsRecording(false);
      setIsPaused(false);
      if (timerRef.current) {
        clearInterval(timerRef.current);
      }
    }
  };

  const handleDone = () => {
    if (audioBlob && onRecordingComplete) {
      onRecordingComplete(audioBlob, recordingTime);
    }
  };

  const formatTime = (seconds) => {
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
  };

  return (
    <div className="flex flex-col items-center space-y-6">
      {/* Timer Display */}
      <div className="text-4xl font-bold text-gray-800">
        {formatTime(recordingTime)}
        <span className="text-sm text-gray-500 ml-2">
          / {formatTime(maxDuration)}
        </span>
      </div>

      {/* Waveform Visualization */}
      {isRecording && !isPaused && <AudioWaveform />}

      {/* Recording Controls */}
      <div className="flex items-center space-x-4">
        {!isRecording && !audioBlob && (
          <button
            onClick={startRecording}
            className="bg-primary hover:bg-primary-dark text-white font-semibold py-4 px-8 rounded-full transition duration-200 flex items-center space-x-2"
          >
            <FaMicrophone size={24} />
            <span>Start Recording</span>
          </button>
        )}

        {isRecording && (
          <>
            {!isPaused ? (
              <button
                onClick={pauseRecording}
                className="bg-yellow-500 hover:bg-yellow-600 text-white font-semibold py-4 px-8 rounded-full transition duration-200 flex items-center space-x-2"
              >
                <FaPause size={24} />
                <span>Pause</span>
              </button>
            ) : (
              <button
                onClick={resumeRecording}
                className="bg-green-500 hover:bg-green-600 text-white font-semibold py-4 px-8 rounded-full transition duration-200 flex items-center space-x-2"
              >
                <FaPlay size={24} />
                <span>Resume</span>
              </button>
            )}

            <button
              onClick={stopRecording}
              className="bg-red-500 hover:bg-red-600 text-white font-semibold py-4 px-8 rounded-full transition duration-200 flex items-center space-x-2"
            >
              <FaStop size={24} />
              <span>Stop</span>
            </button>
          </>
        )}

        {audioBlob && !isRecording && (
          <button
            onClick={handleDone}
            className="bg-accent hover:bg-green-600 text-white font-semibold py-4 px-8 rounded-full transition duration-200"
          >
            Continue to Transcription
          </button>
        )}
      </div>

      {/* Status Messages */}
      {isPaused && (
        <p className="text-yellow-600 font-medium">Recording paused. Click Resume to continue.</p>
      )}
      {recordingTime >= maxDuration && (
        <p className="text-red-600 font-medium">Maximum recording duration reached!</p>
      )}
    </div>
  );
};

export default AudioRecorder;
