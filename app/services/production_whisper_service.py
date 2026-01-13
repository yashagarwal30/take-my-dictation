"""
Production-Ready Whisper Transcription Service

This is a GENERIC solution designed to work with ANY audio input:
- Phone recordings (iPhone, Android)
- Computer microphones
- Professional recording equipment
- Various formats (m4a, mp3, wav, webm, ogg, flac)
- Any language (auto-detected)
- Any duration (seconds to hours)

Key Features:
1. MINIMAL preprocessing (less is more with Whisper)
2. Automatic repetition detection and recovery
3. Multi-temperature retry strategy
4. Graceful degradation
5. Detailed diagnostics

Version: 2.0 - Production Ready
Date: January 2026
"""

import os
import time
import tempfile
from typing import Dict, Optional, Tuple
from dataclasses import dataclass
from enum import Enum

from openai import AsyncOpenAI
from pydub import AudioSegment


class TranscriptionQuality(Enum):
    """Quality levels for transcription results"""
    EXCELLENT = "excellent"  # Clean, no issues
    GOOD = "good"           # Minor issues, usable
    FAIR = "fair"           # Some problems, needs review
    POOR = "poor"           # Significant issues
    FAILED = "failed"       # Could not transcribe


@dataclass
class TranscriptionResult:
    """Structured result from transcription"""
    transcript: Optional[str]
    language: Optional[str]
    quality: TranscriptionQuality
    confidence_score: float  # 0.0 to 1.0
    duration_seconds: float
    processing_time_seconds: float
    temperature_used: float
    attempts: int
    warnings: list
    error: Optional[str]

    @property
    def success(self) -> bool:
        return self.transcript is not None and self.quality != TranscriptionQuality.FAILED


class AudioPreprocessor:
    """
    MINIMAL audio preprocessing for Whisper.

    Philosophy: Whisper was trained on diverse, real-world audio.
    Over-processing often HURTS accuracy. We only do what's necessary.
    """

    # Whisper's supported formats (no conversion needed)
    WHISPER_NATIVE_FORMATS = {'mp3', 'mp4', 'm4a', 'wav', 'webm', 'mpeg', 'mpga'}

    # Whisper's internal sample rate
    WHISPER_SAMPLE_RATE = 16000

    # Maximum file size for Whisper API (25MB)
    MAX_FILE_SIZE_MB = 25

    @classmethod
    async def prepare_audio(cls, input_path: str, output_path: Optional[str] = None) -> Tuple[str, Dict]:
        """
        Prepare audio for Whisper with MINIMAL processing.

        Only processes if:
        1. File is too large (needs compression)
        2. Format is not supported by Whisper
        3. Audio is extremely quiet (needs normalization)

        Returns:
            (output_path, metadata_dict)
        """
        metadata = {
            'original_path': input_path,
            'was_processed': False,
            'processing_steps': []
        }

        # Check if file exists
        if not os.path.exists(input_path):
            raise FileNotFoundError(f"Audio file not found: {input_path}")

        file_size_mb = os.path.getsize(input_path) / (1024 * 1024)
        file_ext = input_path.rsplit('.', 1)[-1].lower() if '.' in input_path else ''

        metadata['original_size_mb'] = round(file_size_mb, 2)
        metadata['original_format'] = file_ext

        # Decision: Do we need to process?
        needs_processing = False

        # Reason 1: File too large
        if file_size_mb > cls.MAX_FILE_SIZE_MB:
            needs_processing = True
            metadata['processing_steps'].append('compress_size')

        # Reason 2: Unsupported format
        if file_ext not in cls.WHISPER_NATIVE_FORMATS:
            needs_processing = True
            metadata['processing_steps'].append('convert_format')

        # If no processing needed, return original
        if not needs_processing:
            metadata['was_processed'] = False
            print(f"📄 Audio file OK - no preprocessing needed")
            return input_path, metadata

        # Process the audio
        if output_path is None:
            output_path = tempfile.NamedTemporaryFile(suffix='.mp3', delete=False).name

        try:
            print(f"⚙️  Minimal preprocessing (Whisper-optimized)...")
            audio = AudioSegment.from_file(input_path)
            metadata['duration_seconds'] = len(audio) / 1000.0
            metadata['original_channels'] = audio.channels
            metadata['original_sample_rate'] = audio.frame_rate
            metadata['original_dbfs'] = round(audio.dBFS, 1)

            # Only normalize if EXTREMELY quiet (< -30 dBFS)
            # This is conservative - most audio doesn't need this
            if audio.dBFS < -30:
                from pydub.effects import normalize
                audio = normalize(audio)
                metadata['processing_steps'].append('normalize_volume')
                metadata['normalized_from_dbfs'] = metadata['original_dbfs']
                print(f"   - Normalized extremely quiet audio ({metadata['original_dbfs']}dB → louder)")

            # Convert to mono if stereo (saves space, Whisper works better)
            if audio.channels > 1:
                audio = audio.set_channels(1)
                metadata['processing_steps'].append('convert_to_mono')
                print(f"   - Converted to mono")

            # Calculate target bitrate based on file size
            duration_seconds = len(audio) / 1000.0
            if file_size_mb > cls.MAX_FILE_SIZE_MB:
                # Target 20MB to be safe (in bits)
                target_size_bits = 20 * 1024 * 1024 * 8
                target_bitrate = int(target_size_bits / duration_seconds / 1000)
                # Clamp between 64k and 128k
                target_bitrate = max(64, min(128, target_bitrate))
                bitrate = f"{target_bitrate}k"
                print(f"   - Compressing to {bitrate} (file was {file_size_mb:.1f}MB)")
            else:
                # Default to 128k for quality
                bitrate = "128k"

            metadata['output_bitrate'] = bitrate

            # Export
            audio.export(output_path, format="mp3", bitrate=bitrate)

            metadata['was_processed'] = True
            metadata['output_size_mb'] = round(os.path.getsize(output_path) / (1024 * 1024), 2)

            print(f"   ✅ Preprocessing complete: {metadata['output_size_mb']}MB")

            return output_path, metadata

        except Exception as e:
            metadata['error'] = str(e)
            print(f"   ⚠️  Preprocessing failed: {e}")
            # Return original on failure - let Whisper try anyway
            return input_path, metadata


class RepetitionDetector:
    """
    Detect the Whisper repetition bug.

    This bug manifests as:
    - Phrases repeating 3+ times
    - Text getting "stuck" in a loop
    - Transcript ending mid-word with repetition
    """

    @staticmethod
    def detect(text: str) -> Tuple[bool, Optional[str]]:
        """
        Detect repetition in transcript.

        Returns:
            (has_repetition: bool, repeated_phrase: Optional[str])
        """
        if not text or len(text) < 50:
            return False, None

        words = text.split()

        # Too short to have meaningful repetition
        if len(words) < 12:
            return False, None

        # Strategy 1: Look for repeated N-grams (N=3,4,5)
        for n in [4, 3, 5]:
            for i in range(len(words) - n * 3):
                phrase = ' '.join(words[i:i+n])
                remaining = ' '.join(words[i+n:])
                count = remaining.count(phrase)
                if count >= 2:  # Original + 2 more = 3 total
                    return True, phrase[:50]

        # Strategy 2: Check last 25% for loops
        last_quarter = text[int(len(text) * 0.75):]
        if len(last_quarter) > 40:
            # Check for any 15+ char substring repeating
            for i in range(0, min(len(last_quarter) - 30, 100), 5):
                chunk = last_quarter[i:i+15]
                if last_quarter.count(chunk) >= 3:
                    return True, chunk

        # Strategy 3: Check if transcript ends abruptly with partial repeat
        if len(text) > 100:
            last_50 = text[-50:]
            prev_100 = text[-150:-50]
            # If last 50 chars appear earlier, might be stuck
            for length in [30, 40, 50]:
                if length <= len(last_50):
                    chunk = last_50[:length]
                    if chunk in prev_100:
                        # Could be repetition - flag it
                        return True, chunk[:30]

        return False, None

    @staticmethod
    def calculate_quality_score(text: str) -> float:
        """
        Calculate a quality score (0.0 to 1.0) for the transcript.

        Factors:
        - Repetition (major penalty)
        - Word diversity
        - Reasonable length
        """
        if not text:
            return 0.0

        score = 1.0

        # Check repetition (heavy penalty)
        has_rep, _ = RepetitionDetector.detect(text)
        if has_rep:
            score -= 0.5

        # Check word diversity
        words = text.split()
        if len(words) > 10:
            unique_ratio = len(set(words)) / len(words)
            if unique_ratio < 0.3:  # Very repetitive vocabulary
                score -= 0.3
            elif unique_ratio < 0.5:
                score -= 0.1

        # Check for garbled characters (common in bad transcripts)
        # This is language-agnostic - looks for unusual patterns
        unusual_chars = sum(1 for c in text if ord(c) > 0xFFFF)
        if unusual_chars > len(text) * 0.1:
            score -= 0.2

        return max(0.0, min(1.0, score))


class ProductionWhisperService:
    """
    Production-ready Whisper transcription service.

    Features:
    - Automatic preprocessing (only when needed)
    - Multi-temperature retry strategy
    - Repetition detection and recovery
    - Detailed result metadata
    - Works with any audio format/language
    """

    # Temperature progression for retries
    # Start balanced, then try extremes
    TEMPERATURE_SEQUENCE = [0.2, 0.0, 0.4, 0.3, 0.6]

    def __init__(self, api_key: str):
        """
        Initialize the service.

        Args:
            api_key: OpenAI API key
        """
        self.client = AsyncOpenAI(api_key=api_key)
        self.preprocessor = AudioPreprocessor()

    async def transcribe(
        self,
        audio_path: str,
        language: Optional[str] = None,
        max_retries: int = 5
    ) -> TranscriptionResult:
        """
        Transcribe audio file.

        Args:
            audio_path: Path to audio file (any format)
            language: Optional ISO language code (e.g., 'en', 'hi', 'es')
                     If None, Whisper auto-detects (recommended)
            max_retries: Maximum transcription attempts

        Returns:
            TranscriptionResult with transcript and metadata
        """
        start_time = time.time()
        warnings = []
        processed_path = None

        try:
            print(f"\n🎙️  Starting production transcription...")

            # Step 1: Preprocess audio (minimal)
            processed_path, prep_metadata = await self.preprocessor.prepare_audio(audio_path)

            if prep_metadata.get('was_processed'):
                warnings.append(f"Audio preprocessed: {', '.join(prep_metadata.get('processing_steps', []))}")

            duration = prep_metadata.get('duration_seconds', 0)
            if duration == 0:
                # Get duration from processed file
                try:
                    audio = AudioSegment.from_file(processed_path)
                    duration = len(audio) / 1000.0
                except:
                    duration = 60  # Default assumption

            print(f"   Duration: {duration:.1f}s")

            # Step 2: Try transcription with different temperatures
            best_result = None
            best_score = 0.0
            attempts = 0

            temperatures_to_try = self.TEMPERATURE_SEQUENCE[:max_retries]

            print(f"🔄 Multi-temperature retry strategy: {temperatures_to_try}")

            for temp in temperatures_to_try:
                attempts += 1

                try:
                    print(f"   Attempt {attempts}/{len(temperatures_to_try)} (temp={temp})...")

                    result = await self._call_whisper(
                        processed_path,
                        temperature=temp,
                        language=language
                    )

                    if result is None:
                        continue

                    transcript, detected_lang = result

                    # Check quality
                    has_repetition, repeated = RepetitionDetector.detect(transcript)
                    quality_score = RepetitionDetector.calculate_quality_score(transcript)

                    print(f"      Quality: {quality_score:.2f}, Repetition: {has_repetition}")

                    # Track best result
                    if quality_score > best_score:
                        best_score = quality_score
                        best_result = {
                            'transcript': transcript,
                            'language': detected_lang,
                            'temperature': temp,
                            'quality_score': quality_score,
                            'has_repetition': has_repetition
                        }

                    # If good enough, stop trying
                    if quality_score >= 0.8 and not has_repetition:
                        print(f"      ✅ Excellent quality achieved, stopping retries")
                        break

                    # If we found repetition, try next temperature
                    if has_repetition:
                        warnings.append(f"Repetition detected at temp={temp}, retrying...")
                        print(f"      ⚠️  Repetition detected: '{repeated[:40]}...'")
                        continue

                except Exception as e:
                    warnings.append(f"API error at temp={temp}: {str(e)[:50]}")
                    print(f"      ❌ Error: {str(e)[:50]}")
                    time.sleep(1)
                    continue

            # Step 3: Determine final quality
            if best_result is None:
                return TranscriptionResult(
                    transcript=None,
                    language=None,
                    quality=TranscriptionQuality.FAILED,
                    confidence_score=0.0,
                    duration_seconds=duration,
                    processing_time_seconds=time.time() - start_time,
                    temperature_used=0.0,
                    attempts=attempts,
                    warnings=warnings,
                    error="All transcription attempts failed"
                )

            # Determine quality level
            if best_score >= 0.9 and not best_result['has_repetition']:
                quality = TranscriptionQuality.EXCELLENT
            elif best_score >= 0.7 and not best_result['has_repetition']:
                quality = TranscriptionQuality.GOOD
            elif best_score >= 0.5:
                quality = TranscriptionQuality.FAIR
                warnings.append("Transcript quality is fair - manual review recommended")
            else:
                quality = TranscriptionQuality.POOR
                warnings.append("Transcript quality is poor - audio may need re-recording")

            if best_result['has_repetition']:
                warnings.append("Warning: Some repetition detected in best result")

            print(f"\n✅ Transcription complete!")
            print(f"   Language: {best_result['language']}")
            print(f"   Quality: {quality.value} (score: {best_score:.2f})")
            print(f"   Temperature used: {best_result['temperature']}")
            print(f"   Attempts: {attempts}")
            print(f"   Time: {time.time() - start_time:.1f}s")

            return TranscriptionResult(
                transcript=best_result['transcript'],
                language=best_result['language'],
                quality=quality,
                confidence_score=best_score,
                duration_seconds=duration,
                processing_time_seconds=time.time() - start_time,
                temperature_used=best_result['temperature'],
                attempts=attempts,
                warnings=warnings,
                error=None
            )

        except Exception as e:
            print(f"❌ Transcription failed: {str(e)}")
            return TranscriptionResult(
                transcript=None,
                language=None,
                quality=TranscriptionQuality.FAILED,
                confidence_score=0.0,
                duration_seconds=0,
                processing_time_seconds=time.time() - start_time,
                temperature_used=0.0,
                attempts=0,
                warnings=warnings,
                error=str(e)
            )

        finally:
            # Cleanup temp file if created
            if processed_path and processed_path != audio_path:
                try:
                    os.remove(processed_path)
                except:
                    pass

    async def _call_whisper(
        self,
        audio_path: str,
        temperature: float,
        language: Optional[str]
    ) -> Optional[Tuple[str, str]]:
        """
        Make a single Whisper API call.

        Returns:
            (transcript, language) or None on failure
        """
        import aiofiles
        from io import BytesIO

        async with aiofiles.open(audio_path, 'rb') as audio_file:
            audio_data = await audio_file.read()

        # Create in-memory file for API
        audio_buffer = BytesIO(audio_data)
        audio_buffer.name = audio_path

        # Build parameters
        params = {
            'model': 'whisper-1',
            'file': audio_buffer,
            'response_format': 'verbose_json',
            'temperature': temperature
        }

        # Only set language if explicitly requested
        # Auto-detection is usually better
        if language:
            params['language'] = language

        response = await self.client.audio.transcriptions.create(**params)

        return response.text, response.language
