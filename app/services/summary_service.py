"""
Summary service.
Generates AI-powered summaries using Anthropic Claude API.
"""
from anthropic import AsyncAnthropic
from sqlalchemy.ext.asyncio import AsyncSession
import json
from typing import Optional

from app.core.config import settings
from app.models.summary import Summary


class SummaryService:
    """Service for AI summary generation using Claude."""

    def __init__(self):
        """Initialize Anthropic client."""
        self.client = AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY)
        self.model = "claude-3-haiku-20240307"

    async def generate_summary(
        self,
        transcription_text: str,
        recording_id: str,
        transcription_id: str,
        db: AsyncSession,
        custom_prompt: Optional[str] = None
    ) -> Summary:
        """
        Generate AI summary from transcription text.

        Args:
            transcription_text: Full transcription text
            recording_id: Recording ID
            transcription_id: Transcription ID
            db: Database session
            custom_prompt: Optional custom instructions

        Returns:
            Summary model instance

        Raises:
            Exception: If summary generation fails
        """
        try:
            # Build prompt with language awareness and comprehensive summarization
            system_prompt = """You are an expert at analyzing audio transcriptions and creating comprehensive, actionable summaries.

IMPORTANT INSTRUCTIONS:
1. First, assess the quality of the transcription. If the text appears garbled, nonsensical, or poorly transcribed, mention this in your summary.
2. Only include information that is actually present in the transcript. Do NOT hallucinate or make up content.
3. If the transcript is in a non-English language, provide the summary in that same language.
4. Create a COMPREHENSIVE summary that captures ALL important information - do not limit yourself to 2-3 sentences. Include as much detail as needed to preserve all key information.
5. Extract ALL key points mentioned in the transcript - not just 3-5. Every important point should be captured.
6. Identify ALL action items or tasks mentioned throughout the transcript.
7. Categorize the content (e.g., meeting_notes, lecture, personal_memo, interview, brainstorming, discussion, planning)

Return your response as JSON with this structure:
{
  "summary": "Comprehensive summary covering all major topics and details discussed. Include multiple paragraphs if needed to capture everything important.",
  "key_points": ["point 1", "point 2", "point 3", "... as many points as needed"],
  "action_items": ["action 1", "action 2", "... all action items mentioned"],
  "category": "meeting_notes"
}

QUALITY NOTE: If the transcript is unclear or poorly transcribed, indicate this clearly:
{
  "summary": "The transcription quality appears to be poor and the content is unclear. The text contains [describe issues]. A re-recording or better audio quality may be needed.",
  "key_points": ["Transcription quality issue detected"],
  "action_items": ["Consider re-recording with better audio quality"],
  "category": "unknown"
}"""

            user_prompt = f"Transcription:\n\n{transcription_text}"

            if custom_prompt:
                user_prompt += f"\n\nAdditional instructions: {custom_prompt}"

            # Call Claude API with higher token limit for comprehensive summaries
            message = await self.client.messages.create(
                model=self.model,
                max_tokens=4096,  # Increased to allow comprehensive summaries
                temperature=0.3,
                system=system_prompt,
                messages=[
                    {"role": "user", "content": user_prompt}
                ]
            )

            # Parse response
            response_text = message.content[0].text

            # Try to extract JSON from response
            try:
                # Sometimes Claude wraps JSON in markdown code blocks
                if "```json" in response_text:
                    json_str = response_text.split("```json")[1].split("```")[0].strip()
                elif "```" in response_text:
                    json_str = response_text.split("```")[1].split("```")[0].strip()
                else:
                    json_str = response_text

                result = json.loads(json_str)
            except json.JSONDecodeError:
                # Fallback if JSON parsing fails
                result = {
                    "summary": response_text[:500],
                    "key_points": [],
                    "action_items": [],
                    "category": "unknown"
                }

            # Create summary record
            summary = Summary(
                recording_id=recording_id,
                transcription_id=transcription_id,
                summary_text=result.get("summary", ""),
                key_points=result.get("key_points", []),
                action_items=result.get("action_items", []),
                category=result.get("category"),
                model_used=self.model
            )

            db.add(summary)
            await db.commit()

            return summary

        except Exception as e:
            print(f"Summary generation error: {str(e)}")
            raise Exception(f"Failed to generate summary: {str(e)}")

    async def regenerate_summary(
        self,
        summary: Summary,
        transcription_text: str,
        db: AsyncSession,
        custom_prompt: Optional[str] = None
    ) -> Summary:
        """
        Regenerate an existing summary.

        Args:
            summary: Existing summary to update
            transcription_text: Transcription text
            db: Database session
            custom_prompt: Optional custom instructions

        Returns:
            Updated summary

        Raises:
            Exception: If regeneration fails
        """
        try:
            # Generate new summary using same method
            system_prompt = """You are an expert at analyzing audio transcriptions and creating concise, actionable summaries.

Your task is to:
1. Provide a brief summary (2-3 sentences)
2. Extract 3-5 key points
3. Identify any action items or tasks mentioned
4. Categorize the content (e.g., meeting_notes, lecture, personal_memo, interview, brainstorming)

Return your response as JSON with this structure:
{
  "summary": "Brief 2-3 sentence summary",
  "key_points": ["point 1", "point 2", "point 3"],
  "action_items": ["action 1", "action 2"],
  "category": "meeting_notes"
}"""

            user_prompt = f"Transcription:\n\n{transcription_text}"

            if custom_prompt:
                user_prompt += f"\n\nAdditional instructions: {custom_prompt}"

            # Call Claude API with higher token limit for comprehensive summaries
            message = await self.client.messages.create(
                model=self.model,
                max_tokens=4096,  # Increased to allow comprehensive summaries
                temperature=0.3,
                system=system_prompt,
                messages=[
                    {"role": "user", "content": user_prompt}
                ]
            )

            # Parse response
            response_text = message.content[0].text

            try:
                if "```json" in response_text:
                    json_str = response_text.split("```json")[1].split("```")[0].strip()
                elif "```" in response_text:
                    json_str = response_text.split("```")[1].split("```")[0].strip()
                else:
                    json_str = response_text

                result = json.loads(json_str)
            except json.JSONDecodeError:
                result = {
                    "summary": response_text[:500],
                    "key_points": [],
                    "action_items": [],
                    "category": "unknown"
                }

            # Update existing summary
            summary.summary_text = result.get("summary", "")
            summary.key_points = result.get("key_points", [])
            summary.action_items = result.get("action_items", [])
            summary.category = result.get("category")
            summary.model_used = self.model

            await db.commit()

            return summary

        except Exception as e:
            print(f"Summary regeneration error: {str(e)}")
            raise Exception(f"Failed to regenerate summary: {str(e)}")
