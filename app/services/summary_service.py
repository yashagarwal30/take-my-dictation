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

CRITICAL RULES:
1. ONLY use information present in the transcript - do NOT hallucinate or make up details
2. If the transcript has errors, is garbled, or unclear, explicitly state this in your summary
3. If the transcript is in a non-English language, provide the summary in English but preserve key terms
4. Always complete your response - NEVER stop mid-sentence or mid-paragraph
5. Be thorough and comprehensive - capture ALL important information

QUALITY ASSESSMENT:
- First, assess the transcription quality
- If the text is mostly gibberish or nonsensical, acknowledge this clearly
- If parts are unclear, mark them as [unclear in transcript]

COMPREHENSIVE OUTPUT:
- Summary: Include as much detail as needed (multiple paragraphs if necessary)
- Key Points: Extract ALL significant points (not just 3-5, but everything important)
- Action Items: Identify ALL tasks/actions mentioned
- Category: Classify the content type

Return your response as JSON with this structure:
{
  "summary": "Comprehensive, detailed summary. Include multiple paragraphs if needed to cover all information. ALWAYS complete your thoughts - never stop mid-sentence.",
  "key_points": ["All significant points from the transcript - as many as needed"],
  "action_items": ["All action items and tasks mentioned"],
  "category": "meeting_notes|lecture|interview|discussion|planning|memo|brainstorming|other"
}

EXAMPLE - If transcript quality is poor:
{
  "summary": "⚠️ WARNING: The transcription quality is very poor. The audio appears to contain [describe language/content] but most of the text is garbled or nonsensical. Key recognizable terms: [list any clear words/phrases]. Recommendation: Re-record with better audio quality in a quiet environment, or use a higher quality microphone.",
  "key_points": ["Transcription quality is poor", "Content is mostly unclear", "Re-recording recommended"],
  "action_items": ["Re-record with better audio quality", "Use quiet environment", "Consider better microphone"],
  "category": "poor_quality"
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
                # Fallback if JSON parsing fails - DO NOT TRUNCATE
                print(f"⚠️  Warning: Failed to parse JSON response, using full text as summary")
                result = {
                    "summary": response_text,  # Full text, not truncated
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
            system_prompt = """You are an expert at analyzing audio transcriptions and creating comprehensive, actionable summaries.

CRITICAL RULES:
1. ONLY use information present in the transcript - do NOT hallucinate or make up details
2. If the transcript has errors, is garbled, or unclear, explicitly state this
3. If the transcript is in a non-English language, provide the summary in English but preserve key terms
4. Always complete your response - NEVER stop mid-sentence or mid-paragraph
5. Be thorough and comprehensive - capture ALL important information

Return your response as JSON with this structure:
{
  "summary": "Comprehensive, detailed summary. Include multiple paragraphs if needed. ALWAYS complete your thoughts.",
  "key_points": ["All significant points from the transcript - as many as needed"],
  "action_items": ["All action items and tasks mentioned"],
  "category": "meeting_notes|lecture|interview|discussion|planning|memo|brainstorming|other"
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
                # Fallback if JSON parsing fails - DO NOT TRUNCATE
                print(f"⚠️  Warning: Failed to parse JSON response in regenerate, using full text")
                result = {
                    "summary": response_text,  # Full text, not truncated
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
