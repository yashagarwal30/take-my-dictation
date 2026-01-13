"""
Universal audio preprocessor for Whisper API.
Works with any audio format, quality, or language.
"""
from pydub import AudioSegment
from pydub.effects import normalize
import os
from typing import Dict


class AudioProcessor:
    """
    Universal audio preprocessor for Whisper API.
    Works with any audio format, quality, or language.
    """

    # Whisper's optimal settings (based on OpenAI research)
    OPTIMAL_SAMPLE_RATE = 16000  # 16kHz
    OPTIMAL_CHANNELS = 1         # Mono
    OPTIMAL_FORMAT = "mp3"
    OPTIMAL_BITRATE = "128k"     # Good balance of quality & size

    @staticmethod
    def analyze_audio(file_path: str) -> Dict:
        """
        Analyze audio to determine preprocessing needs.

        Args:
            file_path: Path to audio file

        Returns:
            Dictionary with audio metadata
        """
        audio = AudioSegment.from_file(file_path)

        return {
            'duration_ms': len(audio),
            'duration_seconds': len(audio) / 1000.0,
            'sample_rate': audio.frame_rate,
            'channels': audio.channels,
            'sample_width': audio.sample_width,
            'frame_count': audio.frame_count(),
            'rms': audio.rms,  # Root mean square (volume indicator)
            'dBFS': audio.dBFS,  # Decibels relative to full scale
        }

    @staticmethod
    def preprocess_audio(input_path: str, output_path: str) -> Dict:
        """
        Universal preprocessing pipeline.

        Steps:
        1. Convert to WAV (uncompressed, for processing)
        2. Apply intelligent normalization
        3. Convert to optimal format for Whisper

        Args:
            input_path: Path to input audio file
            output_path: Path for processed output file

        Returns:
            Processing metadata
        """
        try:
            # Step 1: Load audio (handles ANY format)
            audio = AudioSegment.from_file(input_path)

            # Step 2: Analyze to decide preprocessing intensity
            original_dBFS = audio.dBFS

            # Step 3: Normalize volume intelligently
            # Only normalize if too quiet (< -20 dB) or too loud (> -3 dB)
            if original_dBFS < -20 or original_dBFS > -3:
                audio = normalize(audio)
                normalized = True
            else:
                normalized = False

            # Step 4: Convert to mono (Whisper works better with mono)
            if audio.channels > 1:
                audio = audio.set_channels(1)

            # Step 5: Resample to Whisper's native rate
            if audio.frame_rate != AudioProcessor.OPTIMAL_SAMPLE_RATE:
                audio = audio.set_frame_rate(AudioProcessor.OPTIMAL_SAMPLE_RATE)

            # Step 6: Export with optimal settings
            audio.export(
                output_path,
                format=AudioProcessor.OPTIMAL_FORMAT,
                bitrate=AudioProcessor.OPTIMAL_BITRATE,
                parameters=["-q:a", "0"]  # Highest quality encoding
            )

            return {
                'success': True,
                'original_dBFS': original_dBFS,
                'normalized': normalized,
                'output_path': output_path
            }

        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }

    @staticmethod
    async def preprocess_audio_async(input_path: str, output_path: str) -> Dict:
        """
        Async wrapper for preprocess_audio.

        Args:
            input_path: Path to input audio file
            output_path: Path for processed output file

        Returns:
            Processing metadata
        """
        # pydub operations are CPU-bound, so we run them in sync mode
        # For true async, you'd use asyncio.to_thread() but for now this works
        return AudioProcessor.preprocess_audio(input_path, output_path)
