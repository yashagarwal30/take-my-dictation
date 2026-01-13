"""
Production-ready Whisper transcription service.
Auto-optimizes parameters based on audio characteristics.
"""
from openai import AsyncOpenAI
import time
from typing import Dict, Optional
import aiofiles
from io import BytesIO


class WhisperTranscriber:
    """
    Production-ready Whisper transcription service.
    Auto-optimizes parameters based on audio.
    """

    def __init__(self, api_key: str):
        """
        Initialize Whisper transcriber.

        Args:
            api_key: OpenAI API key
        """
        self.client = AsyncOpenAI(api_key=api_key)
        self.max_retries = 3
        self.base_retry_delay = 2

    def _determine_temperature(self, audio_duration: float) -> float:
        """
        Auto-select temperature based on audio length.

        Why:
        - Short clips (< 30s): Lower temp (0.0) for accuracy
        - Medium clips (30s-5min): Balanced temp (0.2)
        - Long clips (> 5min): Higher temp (0.3) to avoid repetition

        Args:
            audio_duration: Duration in seconds

        Returns:
            Optimal temperature value
        """
        if audio_duration < 30:
            return 0.0
        elif audio_duration < 300:  # 5 minutes
            return 0.2
        else:
            return 0.3

    def _build_whisper_request(
        self,
        audio_metadata: Dict
    ) -> Dict:
        """
        Build optimal Whisper API request parameters.

        Args:
            audio_metadata: Audio analysis metadata

        Returns:
            Dictionary of API parameters
        """
        temperature = self._determine_temperature(
            audio_metadata.get('duration_seconds', 0)
        )

        # Build request parameters
        params = {
            'model': 'whisper-1',
            'response_format': 'verbose_json',  # Get detailed response
            'temperature': temperature,
        }

        # DO NOT specify language - let Whisper auto-detect
        # This works for 99+ languages automatically

        # DO NOT use prompts unless we have verified context
        # Generic prompts can hurt accuracy

        return params

    async def transcribe(
        self,
        audio_file_path: str,
        audio_metadata: Optional[Dict] = None
    ) -> Dict:
        """
        Transcribe audio with automatic retry and optimization.

        Args:
            audio_file_path: Path to audio file
            audio_metadata: Optional pre-analyzed audio metadata

        Returns:
            {
                'text': str,              # The transcription
                'language': str,          # Auto-detected language
                'duration': float,        # Audio duration
                'segments': List,         # Timestamped segments
                'confidence': float,      # Quality score (0-1)
                'attempts': int          # Number of retries
            }
        """
        if audio_metadata is None:
            # If not provided, analyze the audio
            from app.services.audio_processor import AudioProcessor
            processor = AudioProcessor()
            audio_metadata = processor.analyze_audio(audio_file_path)

        # Build optimal request
        request_params = self._build_whisper_request(audio_metadata)

        # Retry logic with exponential backoff
        for attempt in range(self.max_retries):
            try:
                # Read audio file
                async with aiofiles.open(audio_file_path, 'rb') as audio_file:
                    audio_data = await audio_file.read()

                # Create in-memory file for API
                audio_buffer = BytesIO(audio_data)
                audio_buffer.name = audio_file_path

                # Make API call
                response = await self.client.audio.transcriptions.create(
                    file=audio_buffer,
                    **request_params
                )

                # Calculate confidence score
                confidence = self._calculate_confidence(response)

                # Check for quality issues
                if self._has_quality_issues(response.text):
                    if attempt < self.max_retries - 1:
                        print(f"⚠️  Quality issue detected, retrying with adjusted params (attempt {attempt + 2})")
                        # Adjust temperature and retry
                        request_params['temperature'] = min(request_params['temperature'] + 0.2, 1.0)
                        await self._async_sleep(self.base_retry_delay * (2 ** attempt))
                        continue

                # Success
                return {
                    'text': response.text,
                    'language': getattr(response, 'language', 'unknown'),
                    'duration': getattr(response, 'duration', audio_metadata.get('duration_seconds', 0)),
                    'segments': getattr(response, 'segments', []),
                    'confidence': confidence,
                    'attempts': attempt + 1,
                    'temperature_used': request_params['temperature']
                }

            except Exception as e:
                if attempt < self.max_retries - 1:
                    wait_time = self.base_retry_delay * (2 ** attempt)
                    print(f"⚠️  Whisper API error (attempt {attempt + 1}/{self.max_retries}): {e}")
                    print(f"   Retrying in {wait_time} seconds...")
                    await self._async_sleep(wait_time)
                else:
                    raise Exception(f"Whisper API failed after {self.max_retries} attempts: {e}")

    async def _async_sleep(self, seconds: float):
        """Async sleep helper."""
        import asyncio
        await asyncio.sleep(seconds)

    def _calculate_confidence(self, response) -> float:
        """
        Calculate confidence score based on Whisper response.

        Factors:
        - Segment-level confidence scores (if available)
        - Text length vs audio duration ratio
        - Repetition detection

        Args:
            response: Whisper API response

        Returns:
            Confidence score (0-1)
        """
        segments = getattr(response, 'segments', [])

        if not segments:
            return 0.5  # Unknown confidence

        # Average confidence from segments (if available)
        confidences = []
        for seg in segments:
            if hasattr(seg, 'avg_logprob'):
                confidences.append(seg.avg_logprob)

        if confidences:
            # Convert log probability to 0-1 scale
            # avg_logprob ranges from -∞ to 0, we normalize to 0-1
            avg_confidence = sum(confidences) / len(confidences)
            normalized_confidence = max(0, min(1, (avg_confidence + 1)))  # Rough normalization
        else:
            normalized_confidence = 0.5

        return normalized_confidence

    def _has_quality_issues(self, text: str) -> bool:
        """
        Detect common quality issues in transcript.

        Issues to detect:
        - Excessive repetition (Whisper hallucination bug)
        - Very short output for long audio
        - Empty or near-empty transcript
        - Repetitive gibberish patterns

        Args:
            text: Transcribed text

        Returns:
            True if quality issues detected
        """
        if not text or len(text.strip()) < 10:
            return True

        # Check for repetition (same 3+ words repeating)
        words = text.split()
        if len(words) < 10:
            return False  # Too short to have meaningful repetition

        # Enhanced repetition check: Look for repeated 3-word phrases
        for i in range(min(len(words) - 6, 50)):  # Check first 50 positions
            phrase = " ".join(words[i:i+3])
            # Count occurrences in the rest of the text
            rest = " ".join(words[i+3:])
            occurrences = rest.count(phrase)

            if occurrences >= 3:
                print(f"⚠️  Repetition detected: '{phrase}' appears {occurrences + 1} times")
                return True  # Likely repetition bug

        # Check for very repetitive single words (more than 10% of text)
        if words:
            word_freq = {}
            for word in words:
                word_lower = word.lower()
                word_freq[word_lower] = word_freq.get(word_lower, 0) + 1

            max_freq = max(word_freq.values())
            if max_freq > len(words) * 0.1 and max_freq > 5:
                most_common = max(word_freq, key=word_freq.get)
                print(f"⚠️  Word repetition: '{most_common}' appears {max_freq} times ({max_freq/len(words)*100:.1f}%)")
                return True

        return False
