"""
Summary service.
Generates AI-powered summaries using Anthropic Claude API.
"""
from anthropic import AsyncAnthropic
from sqlalchemy.ext.asyncio import AsyncSession
import json
from typing import Optional

from app.core.config import settings
from app.models.summary import Summary, SummaryFormat


class SummaryService:
    """Service for AI summary generation using Claude."""

    def __init__(self):
        """Initialize Anthropic client."""
        self.client = AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY)
        self.model = "claude-3-haiku-20240307"

    def _get_format_specific_prompt(self, format: SummaryFormat) -> str:
        """
        Get format-specific system prompt for summary generation.

        Args:
            format: The desired summary format

        Returns:
            Format-specific system prompt
        """
        base_rules = """CRITICAL RULES:
1. ONLY use information present in the transcript - do NOT hallucinate or make up details
2. If the transcript has errors, is garbled, or unclear, explicitly state this in your summary
3. If the transcript is in a non-English language, provide the summary in English but preserve key terms
4. Always complete your response - NEVER stop mid-sentence or mid-paragraph
5. Be thorough and comprehensive - capture ALL important information"""

        if format == SummaryFormat.MEETING_NOTES:
            return f"""You are an expert at analyzing meeting transcripts and creating comprehensive meeting notes.

{base_rules}

FORMAT REQUIREMENTS - MEETING NOTES:
Structure your response with the following sections:
1. **Meeting Overview**: Brief description of the meeting purpose and context
2. **Attendees/Participants**: Who was present (if mentioned or identifiable)
3. **Discussion Points**: Detailed breakdown of topics discussed, organized by topic
4. **Key Decisions**: Important decisions made during the meeting
5. **Action Items**: Tasks assigned with owners (if mentioned) and deadlines
6. **Next Steps**: What happens next, follow-up meetings, etc.

Return your response as JSON with this structure:
{{
  "summary": "Comprehensive meeting notes following the format above. Use clear section headings and bullet points where appropriate.",
  "key_points": ["All significant discussion points and decisions"],
  "action_items": ["Task description - Owner (if mentioned) - Deadline (if mentioned)"],
  "category": "meeting_notes"
}}"""

        elif format == SummaryFormat.PRODUCT_SPEC:
            return f"""You are an expert at analyzing product discussions and creating structured product specifications.

{base_rules}

FORMAT REQUIREMENTS - PRODUCT SPECIFICATION:
Structure your response with the following sections:
1. **Problem Statement**: What problem is being solved? What pain points exist?
2. **Proposed Solution**: High-level description of the solution
3. **User Stories**: Who will use this? What are their goals? (Format: "As a [user], I want [goal] so that [benefit]")
4. **Requirements**:
   - Functional Requirements: What the product must do
   - Non-Functional Requirements: Performance, security, scalability, etc.
5. **Success Metrics**: How will success be measured?
6. **Open Questions**: What needs further clarification or research?

Return your response as JSON with this structure:
{{
  "summary": "Comprehensive product specification following the format above. Be specific and actionable.",
  "key_points": ["Critical requirements and constraints"],
  "action_items": ["Tasks needed to move forward with this product"],
  "category": "product_spec"
}}"""

        elif format == SummaryFormat.MOM:
            return f"""You are an expert at creating formal Minutes of Meeting (MOM) documents.

{base_rules}

FORMAT REQUIREMENTS - MINUTES OF MEETING (MOM):
Create a formal, professional MOM with:
1. **Meeting Details**: Date, time, location/platform, duration
2. **Attendees**: List of participants with roles/titles (if mentioned)
3. **Agenda Items**: Numbered list of topics discussed
4. **Discussion Summary**: For each agenda item, provide:
   - Key points raised
   - Opinions/concerns expressed
   - Decisions made
5. **Resolutions**: Formal decisions and approvals
6. **Action Items**: Tasks with assignees and deadlines (table format if possible)
7. **Next Meeting**: Date/time of next meeting (if mentioned)

Use formal, professional language appropriate for official records.

Return your response as JSON with this structure:
{{
  "summary": "Formal minutes of meeting following the format above. Use professional tone and clear structure.",
  "key_points": ["Key decisions and resolutions"],
  "action_items": ["Action item with assignee and deadline"],
  "category": "mom"
}}"""

        else:  # QUICK_SUMMARY (default)
            return f"""You are an expert at creating concise, high-impact summaries of transcriptions.

{base_rules}

FORMAT REQUIREMENTS - QUICK SUMMARY:
Create a brief, focused summary that:
1. Captures the essence in 2-4 paragraphs maximum
2. Highlights only the most important points
3. Identifies critical action items
4. Provides context for what was discussed

Focus on clarity and brevity while ensuring no critical information is lost.

Return your response as JSON with this structure:
{{
  "summary": "Concise overview that gets straight to the point. 2-4 paragraphs maximum.",
  "key_points": ["Top 5-7 most important points only"],
  "action_items": ["Critical action items only"],
  "category": "quick_summary"
}}"""

    async def generate_summary(
        self,
        transcription_text: str,
        recording_id: str,
        transcription_id: str,
        db: AsyncSession,
        format: SummaryFormat = SummaryFormat.QUICK_SUMMARY,
        custom_prompt: Optional[str] = None
    ) -> Summary:
        """
        Generate AI summary from transcription text.

        Args:
            transcription_text: Full transcription text
            recording_id: Recording ID
            transcription_id: Transcription ID
            db: Database session
            format: Summary format (MEETING_NOTES, PRODUCT_SPEC, MOM, QUICK_SUMMARY)
            custom_prompt: Optional custom instructions

        Returns:
            Summary model instance

        Raises:
            Exception: If summary generation fails
        """
        try:
            # Get format-specific system prompt
            system_prompt = self._get_format_specific_prompt(format)

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
                format=format,
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
        format: Optional[SummaryFormat] = None,
        custom_prompt: Optional[str] = None
    ) -> Summary:
        """
        Regenerate an existing summary.

        Args:
            summary: Existing summary to update
            transcription_text: Transcription text
            db: Database session
            format: Optional new format (uses existing format if not provided)
            custom_prompt: Optional custom instructions

        Returns:
            Updated summary

        Raises:
            Exception: If regeneration fails
        """
        try:
            # Use provided format or keep existing format
            summary_format = format if format is not None else summary.format

            # Get format-specific system prompt
            system_prompt = self._get_format_specific_prompt(summary_format)

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
            summary.format = summary_format
            summary.model_used = self.model

            await db.commit()

            return summary

        except Exception as e:
            print(f"Summary regeneration error: {str(e)}")
            raise Exception(f"Failed to regenerate summary: {str(e)}")
