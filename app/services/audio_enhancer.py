"""
Audio enhancement service for optimal Whisper transcription.
Includes noise reduction, normalization, and dynamic range compression.
"""
from pydub import AudioSegment
from pydub.effects import normalize, compress_dynamic_range
import subprocess
import os
import tempfile
from typing import Dict


class AudioEnhancer:
    """
    Enhance audio for optimal Whisper transcription.
    Applies noise reduction, normalization, and compression.
    """

    @staticmethod
    def enhance_for_whisper(input_file: str, output_file: str) -> Dict:
        """
        Full enhancement pipeline:
        1. Noise reduction (ffmpeg)
        2. Volume normalization
        3. Dynamic range compression
        4. Optimal format conversion

        Args:
            input_file: Path to input audio file
            output_file: Path for enhanced output file

        Returns:
            Dictionary with enhancement metadata
        """
        temp_denoised = None

        try:
            # Create temp file for intermediate step
            temp_denoised = tempfile.NamedTemporaryFile(
                suffix='.wav', delete=False
            ).name

            # STEP 1: Noise reduction with ffmpeg
            # - highpass=f=80: Remove rumble below 80Hz
            # - lowpass=f=8000: Remove hiss above 8kHz
            # - afftdn: Adaptive noise reduction
            denoise_command = [
                'ffmpeg',
                '-i', input_file,
                '-af', 'highpass=f=80,lowpass=f=8000,afftdn=nf=-20',
                '-ar', '16000',  # Whisper's native sample rate
                '-ac', '1',      # Mono
                temp_denoised,
                '-y',            # Overwrite
                '-loglevel', 'error'
            ]

            print(f"🔊 Applying noise reduction and filters...")
            subprocess.run(
                denoise_command,
                check=True,
                capture_output=True
            )

            # STEP 2: Load and normalize
            print(f"📊 Normalizing audio volume...")
            audio = AudioSegment.from_file(temp_denoised)
            original_dbfs = audio.dBFS
            audio = normalize(audio)

            # STEP 3: Compress dynamic range
            # Makes quiet parts louder, loud parts quieter
            print(f"⚙️  Compressing dynamic range...")
            audio = compress_dynamic_range(
                audio,
                threshold=-20.0,
                ratio=4.0,
                attack=5.0,
                release=50.0
            )

            # STEP 4: Export in optimal format
            print(f"💾 Exporting enhanced audio...")
            audio.export(
                output_file,
                format="mp3",
                bitrate="128k",
                parameters=["-q:a", "0"]
            )

            print(f"✅ Audio enhancement complete!")
            print(f"   - Original volume: {original_dbfs:.2f}dB")
            print(f"   - Output: {output_file}")

            return {
                'success': True,
                'original_dbfs': original_dbfs,
                'output_file': output_file
            }

        except subprocess.CalledProcessError as e:
            error_msg = e.stderr.decode() if e.stderr else str(e)
            print(f"❌ FFmpeg error: {error_msg}")
            return {
                'success': False,
                'error': f"ffmpeg error: {error_msg}"
            }
        except Exception as e:
            print(f"❌ Enhancement error: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }
        finally:
            # Cleanup temp file
            if temp_denoised and os.path.exists(temp_denoised):
                try:
                    os.remove(temp_denoised)
                except Exception:
                    pass

    @staticmethod
    async def enhance_for_whisper_async(input_file: str, output_file: str) -> Dict:
        """
        Async wrapper for enhance_for_whisper.

        Args:
            input_file: Path to input audio file
            output_file: Path for enhanced output file

        Returns:
            Dictionary with enhancement metadata
        """
        # Audio processing is CPU-bound, so we run it synchronously
        # For true async, you'd use asyncio.to_thread() in Python 3.9+
        return AudioEnhancer.enhance_for_whisper(input_file, output_file)
