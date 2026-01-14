"""
Production-ready transcription service with adaptive audio processing pipeline.
Handles everything from audio preprocessing to final transcript.
"""
from sqlalchemy.ext.asyncio import AsyncSession
import os
from typing import Dict, Optional

from app.core.config import settings
from app.models.transcription import Transcription
from app.services.audio_processor import AudioProcessor
from app.services.whisper_transcriber import WhisperTranscriber
from app.services.audio_enhancer import AudioEnhancer
from app.services.production_whisper_service import ProductionWhisperService, TranscriptionQuality


class TranscriptionService:
    """
    Complete transcription pipeline.
    Handles everything from audio preprocessing to final transcript with adaptive processing.
    """

    def __init__(self, use_production_service: bool = True):
        """
        Initialize transcription service with processor, transcriber, and enhancer.

        Args:
            use_production_service: If True, uses ProductionWhisperService with multi-temperature retry.
                                   If False, uses the previous adaptive service.
        """
        self.use_production_service = use_production_service
        self.processor = AudioProcessor()
        self.transcriber = WhisperTranscriber(settings.OPENAI_API_KEY)
        self.enhancer = AudioEnhancer()

        if use_production_service:
            self.production_service = ProductionWhisperService(settings.OPENAI_API_KEY)

    async def transcribe_audio(
        self,
        audio_file_path: str,
        recording_id: str,
        db: AsyncSession,
        cleanup: bool = True
    ) -> Transcription:
        """
        Complete transcription pipeline with adaptive processing.

        Args:
            audio_file_path: Path to uploaded audio file
            recording_id: Recording ID for database
            db: Database session
            cleanup: Whether to delete temporary processed files

        Returns:
            Transcription model instance

        Raises:
            Exception: If transcription fails at any stage
        """
        from sqlalchemy import select

        # Check if transcription already exists for this recording
        result = await db.execute(
            select(Transcription).filter(Transcription.recording_id == recording_id)
        )
        existing = result.scalar_one_or_none()

        if existing:
            print(f"ℹ️  Transcription already exists for recording {recording_id}, returning existing")
            return existing

        # If production service is enabled, use it instead
        if self.use_production_service:
            return await self.transcribe_audio_production(audio_file_path, recording_id, db)

        # Otherwise use the original enhanced pipeline
        temp_processed = None

        try:
            # Step 1: Analyze input audio
            print("🔍 Analyzing audio...")
            audio_metadata = self.processor.analyze_audio(audio_file_path)

            # Log audio characteristics
            print(f"   - Duration: {audio_metadata['duration_seconds']:.2f}s")
            print(f"   - Sample rate: {audio_metadata['sample_rate']}Hz")
            print(f"   - Channels: {audio_metadata['channels']}")
            print(f"   - Volume (dBFS): {audio_metadata['dBFS']:.2f}dB")

            # Validate duration
            if audio_metadata['duration_seconds'] < 1:
                raise ValueError("Audio too short (< 1 second)")

            if audio_metadata['duration_seconds'] > 7200:  # 2 hours
                raise ValueError("Audio too long (> 2 hours). Please split into smaller files.")

            # Step 2: Enhanced audio preprocessing pipeline
            print("⚙️  Preprocessing audio...")
            temp_processed = f"{os.path.splitext(audio_file_path)[0]}_processed.mp3"

            # Try enhanced preprocessing with noise reduction
            try:
                print("🎛️  Applying audio enhancement (noise reduction, normalization)...")
                enhancement_result = await self.enhancer.enhance_for_whisper_async(
                    audio_file_path,
                    temp_processed
                )

                if enhancement_result['success']:
                    print(f"   ✅ Enhancement successful")
                    print(f"   - Original volume: {enhancement_result['original_dBFS']:.2f}dB")
                else:
                    # Fall back to basic preprocessing if enhancement fails
                    print(f"   ⚠️  Enhancement failed, using basic preprocessing...")
                    preprocessing_result = await self.processor.preprocess_audio_async(
                        audio_file_path,
                        temp_processed
                    )
                    if not preprocessing_result['success']:
                        raise Exception(f"Audio preprocessing failed: {preprocessing_result.get('error')}")
                    print(f"   - Normalized: {preprocessing_result['normalized']}")
                    print(f"   - Original volume: {preprocessing_result['original_dBFS']:.2f}dB")

            except Exception as e:
                # Fall back to basic preprocessing
                print(f"   ⚠️  Enhancement error: {str(e)}, falling back to basic preprocessing...")
                preprocessing_result = await self.processor.preprocess_audio_async(
                    audio_file_path,
                    temp_processed
                )
                if not preprocessing_result['success']:
                    raise Exception(f"Audio preprocessing failed: {preprocessing_result.get('error')}")
                print(f"   - Normalized: {preprocessing_result['normalized']}")
                print(f"   - Original volume: {preprocessing_result['original_dBFS']:.2f}dB")

            # Step 3: Transcribe with Whisper using adaptive configuration
            print("🎙️  Transcribing with Whisper...")
            transcription_result = await self.transcriber.transcribe(
                temp_processed,
                audio_metadata
            )

            # Step 4: Log results
            print(f"✅ Transcription completed:")
            print(f"   - Language: {transcription_result['language']}")
            print(f"   - Confidence: {transcription_result['confidence']:.2f}")
            print(f"   - Attempts: {transcription_result['attempts']}")
            print(f"   - Temperature used: {transcription_result['temperature_used']}")
            print(f"   - Text length: {len(transcription_result['text'])} chars")
            print(f"   - Preview: {transcription_result['text'][:100]}...")

            # Step 5: Warn if low confidence
            if transcription_result['confidence'] < 0.3:
                print(f"⚠️  WARNING: Low confidence transcription ({transcription_result['confidence']:.2f})")

            # Step 6: Create transcription record
            transcription = Transcription(
                recording_id=recording_id,
                text=transcription_result['text'],
                language=transcription_result['language'],
                confidence=transcription_result['confidence'],
                provider="whisper"
            )

            db.add(transcription)

            try:
                await db.commit()
                await db.refresh(transcription)
                return transcription
            except Exception as db_error:
                # Handle duplicate key error gracefully
                if "duplicate key" in str(db_error).lower() or "unique constraint" in str(db_error).lower():
                    print(f"⚠️  Duplicate detected during commit, fetching existing transcription")
                    await db.rollback()
                    # Fetch and return the existing transcription
                    result_check = await db.execute(
                        select(Transcription).filter(Transcription.recording_id == recording_id)
                    )
                    existing = result_check.scalar_one_or_none()
                    if existing:
                        print(f"✅ Returning existing transcription")
                        return existing
                # Re-raise if it's a different error
                raise

        except Exception as e:
            print(f"❌ Transcription error: {str(e)}")
            raise Exception(f"Failed to transcribe audio: {str(e)}")

        finally:
            # Cleanup temporary files
            if cleanup and temp_processed and os.path.exists(temp_processed):
                try:
                    os.remove(temp_processed)
                    print(f"🗑️  Cleaned up temporary file: {temp_processed}")
                except Exception as e:
                    print(f"⚠️  Failed to cleanup temp file: {e}")

    async def transcribe_audio_production(
        self,
        audio_file_path: str,
        recording_id: str,
        db: AsyncSession
    ) -> Transcription:
        """
        Transcribe audio using the production-ready multi-temperature retry service.

        This method uses minimal preprocessing and tries multiple temperature values
        to find the best transcription result.

        Args:
            audio_file_path: Path to uploaded audio file
            recording_id: Recording ID for database
            db: Database session

        Returns:
            Transcription model instance

        Raises:
            Exception: If transcription fails at any stage
        """
        from sqlalchemy import select

        try:
            # Check if transcription already exists for this recording
            result = await db.execute(
                select(Transcription).filter(Transcription.recording_id == recording_id)
            )
            existing = result.scalar_one_or_none()

            if existing:
                print(f"ℹ️  Transcription already exists for recording {recording_id}, returning existing")
                return existing

            print(f"\n{'='*60}")
            print(f"PRODUCTION TRANSCRIPTION SERVICE")
            print(f"{'='*60}")

            # Use production service with multi-temperature retry
            result = await self.production_service.transcribe(
                audio_path=audio_file_path,
                language=None,  # Auto-detect
                max_retries=5
            )

            if not result.success:
                raise Exception(f"Transcription failed: {result.error}")

            # Log quality metrics
            print(f"\n📊 Quality Metrics:")
            print(f"   - Quality Level: {result.quality.value}")
            print(f"   - Confidence Score: {result.confidence_score:.2f}")
            print(f"   - Processing Time: {result.processing_time_seconds:.1f}s")
            print(f"   - Temperature Used: {result.temperature_used}")
            print(f"   - Attempts: {result.attempts}")

            if result.warnings:
                print(f"\n⚠️  Warnings:")
                for warning in result.warnings:
                    print(f"   - {warning}")

            # Create transcription record
            transcription = Transcription(
                recording_id=recording_id,
                text=result.transcript,
                language=result.language,
                confidence=result.confidence_score,
                provider="whisper-production"
            )

            db.add(transcription)

            try:
                await db.commit()
                await db.refresh(transcription)
                print(f"\n✅ Transcription saved to database")
                print(f"{'='*60}\n")
                return transcription
            except Exception as db_error:
                # Handle duplicate key error gracefully
                if "duplicate key" in str(db_error).lower() or "unique constraint" in str(db_error).lower():
                    print(f"⚠️  Duplicate detected during commit, fetching existing transcription")
                    await db.rollback()
                    # Fetch and return the existing transcription
                    result_check = await db.execute(
                        select(Transcription).filter(Transcription.recording_id == recording_id)
                    )
                    existing = result_check.scalar_one_or_none()
                    if existing:
                        print(f"✅ Returning existing transcription")
                        return existing
                # Re-raise if it's a different error
                raise

        except Exception as e:
            print(f"❌ Production transcription error: {str(e)}")
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
            # Preprocess audio first for better results
            print("🔍 Analyzing and preprocessing audio for timestamp transcription...")
            audio_metadata = self.processor.analyze_audio(audio_file_path)

            temp_processed = f"{os.path.splitext(audio_file_path)[0]}_processed_timestamps.mp3"
            preprocessing_result = await self.processor.preprocess_audio_async(
                audio_file_path,
                temp_processed
            )

            if not preprocessing_result['success']:
                raise Exception(f"Audio preprocessing failed: {preprocessing_result.get('error')}")

            # Use processed audio for transcription
            from openai import AsyncOpenAI
            import aiofiles
            from io import BytesIO

            client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)

            async with aiofiles.open(temp_processed, 'rb') as audio_file:
                audio_data = await audio_file.read()

            audio_buffer = BytesIO(audio_data)
            audio_buffer.name = temp_processed

            # Get detailed response with timestamps
            transcript_response = await client.audio.transcriptions.create(
                model="whisper-1",
                file=audio_buffer,
                language=language,
                response_format="verbose_json",
                timestamp_granularities=["word"]
            )

            # Cleanup
            if os.path.exists(temp_processed):
                os.remove(temp_processed)

            return {
                "text": transcript_response.text,
                "language": getattr(transcript_response, 'language', language),
                "words": getattr(transcript_response, 'words', [])
            }

        except Exception as e:
            print(f"❌ Transcription with timestamps error: {str(e)}")
            raise Exception(f"Failed to transcribe with timestamps: {str(e)}")

    async def get_transcription_stats(self, audio_file_path: str) -> Dict:
        """
        Get audio analysis and predicted transcription settings without transcribing.

        Useful for showing users what settings will be used.

        Args:
            audio_file_path: Path to audio file

        Returns:
            Dictionary with audio stats and predicted settings
        """
        try:
            audio_metadata = self.processor.analyze_audio(audio_file_path)
            temperature = self.transcriber._determine_temperature(
                audio_metadata['duration_seconds']
            )

            return {
                'audio_stats': audio_metadata,
                'predicted_temperature': temperature,
                'will_normalize': audio_metadata['dBFS'] < -20 or audio_metadata['dBFS'] > -3,
                'estimated_processing_time': audio_metadata['duration_seconds'] * 0.25  # Rough estimate
            }

        except Exception as e:
            raise Exception(f"Failed to analyze audio: {str(e)}")
