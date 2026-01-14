import React from 'react';

const AudioWaveform = () => {
  // Simple animated waveform visualization
  const bars = Array.from({ length: 40 }, (_, i) => i);

  return (
    <div className="flex items-center justify-center space-x-1 h-32">
      {bars.map((bar) => (
        <div
          key={bar}
          className="w-1 bg-primary rounded-full animate-pulse"
          style={{
            height: `${Math.random() * 80 + 20}%`,
            animationDelay: `${Math.random() * 0.5}s`,
            animationDuration: `${Math.random() * 0.5 + 0.3}s`,
          }}
        />
      ))}
    </div>
  );
};

export default AudioWaveform;
