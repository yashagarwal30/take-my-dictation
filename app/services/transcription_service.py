"""
Transcription service.
Integrates with OpenAI Whisper API for speech-to-text.
"""
from openai import AsyncOpenAI
from sqlalchemy.ext.asyncio import AsyncSession
import aiofiles
from typing import Optional

from app.core.config import settings
from app.models.transcription import Transcription


def has_repetition_bug(text: str, min_repetitions: int = 3) -> bool:
    """
    Detect if transcript has repetition bug.

    Returns True if same phrase repeats 3+ times consecutively.
    """
    # Split into words
    words = text.split()

    # Check for phrase repetitions (2-5 word phrases)
    for phrase_length in range(2, 6):
        for i in range(len(words) - phrase_length * min_repetitions):
            phrase = " ".join(words[i:i + phrase_length])

            # Check if this phrase repeats immediately after
            repeat_count = 1
            j = i + phrase_length

            while j < len(words) - phrase_length:
                next_phrase = " ".join(words[j:j + phrase_length])
                if next_phrase == phrase:
                    repeat_count += 1
                    j += phrase_length
                else:
                    break

            if repeat_count >= min_repetitions:
                print(f"⚠️  Repetition detected: '{phrase}' repeated {repeat_count} times")
                return True

    return False


class TranscriptionService:
    """Service for audio transcription using OpenAI Whisper."""

    def __init__(self):
        """Initialize OpenAI client."""
        self.client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)

    async def transcribe_audio(
        self,
        audio_file_path: str,
        recording_id: str,
        db: AsyncSession,
        language: str = None,
        prompt: str = None
    ) -> Transcription:
        """
        Transcribe audio file using OpenAI Whisper API with improved quality.

        Args:
            audio_file_path: Path to audio file
            recording_id: Recording ID
            db: Database session
            language: Optional language code (e.g., 'en', 'es', 'hi')
            prompt: Optional prompt to guide transcription (up to 224 tokens)

        Returns:
            Transcription model instance

        Raises:
            Exception: If transcription fails
        """
        try:
            # Open audio file
            async with aiofiles.open(audio_file_path, 'rb') as audio_file:
                audio_data = await audio_file.read()

            # Create in-memory file for API with proper filename
            from io import BytesIO
            import os
            audio_buffer = BytesIO(audio_data)
            # Set proper filename with extension for better format detection
            filename = os.path.basename(audio_file_path)
            audio_buffer.name = filename

            # Prepare API parameters
            api_params = {
                "model": "whisper-1",
                "file": audio_buffer,
                "response_format": "verbose_json",
                "temperature": 0.2  # Prevents repetition bug while maintaining accuracy
            }

            # Add language if specified (helps with non-English)
            if language:
                api_params["language"] = language

            # Add prompt if specified (helps guide transcription)
            if prompt:
                api_params["prompt"] = prompt

            # Call Whisper API with improved parameters
            transcript_response = await self.client.audio.transcriptions.create(**api_params)

            # Extract data
            text = transcript_response.text
            detected_language = getattr(transcript_response, 'language', language or 'unknown')
            duration = getattr(transcript_response, 'duration', None)

            # Check for repetition bug and retry with higher temperature if needed
            if has_repetition_bug(text):
                print(f"⚠️  Repetition bug detected! Retrying with temperature=0.4...")

                # Reset buffer position
                audio_buffer.seek(0)
                api_params["temperature"] = 0.4

                transcript_response = await self.client.audio.transcriptions.create(**api_params)
                text = transcript_response.text

                # If still has repetition, try once more with even higher temperature
                if has_repetition_bug(text):
                    print(f"⚠️  Still has repetition! Final retry with temperature=0.6...")
                    audio_buffer.seek(0)
                    api_params["temperature"] = 0.6

                    transcript_response = await self.client.audio.transcriptions.create(**api_params)
                    text = transcript_response.text
                    detected_language = getattr(transcript_response, 'language', language or 'unknown')
                    duration = getattr(transcript_response, 'duration', None)

            # Log transcription details for debugging
            print(f"✅ Transcription completed:")
            print(f"   - Language: {detected_language}")
            print(f"   - Duration: {duration}s" if duration else "   - Duration: unknown")
            print(f"   - Text length: {len(text)} chars")
            print(f"   - Preview: {text[:100]}..." if len(text) > 100 else f"   - Text: {text}")

            # Final check and warning
            if has_repetition_bug(text):
                print(f"⚠️  WARNING: Transcription still contains repetition after retries!")

            # Create transcription record
            transcription = Transcription(
                recording_id=recording_id,
                text=text,
                language=detected_language,
                confidence=None,  # Whisper doesn't provide confidence scores
                provider="whisper"
            )

            db.add(transcription)
            await db.commit()

            return transcription

        except Exception as e:
            print(f"❌ Transcription error: {str(e)}")
            raise Exception(f"Failed to transcribe audio: {str(e)}")

    async def transcribe_with_timestamps(
        self,
        audio_file_path: str,
        language: str = None
    ) -> dict:
        """
        Transcribe audio with word-level timestamps.

        Args:
            audio_file_path: Path to audio file
            language: Optional language code

        Returns:
            Dictionary with text and timestamps

        Raises:
            Exception: If transcription fails
        """
        try:
            async with aiofiles.open(audio_file_path, 'rb') as audio_file:
                audio_data = await audio_file.read()

            from io import BytesIO
            audio_buffer = BytesIO(audio_data)
            audio_buffer.name = audio_file_path

            # Get detailed response with timestamps
            transcript_response = await self.client.audio.transcriptions.create(
                model="whisper-1",
                file=audio_buffer,
                language=language,
                response_format="verbose_json",
                timestamp_granularities=["word"]
            )

            return {
                "text": transcript_response.text,
                "language": getattr(transcript_response, 'language', language),
                "words": getattr(transcript_response, 'words', [])
            }

        except Exception as e:
            print(f"Transcription with timestamps error: {str(e)}")
            raise Exception(f"Failed to transcribe with timestamps: {str(e)}")
