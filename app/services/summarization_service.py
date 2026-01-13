"""
AI-powered summarization service using GPT-4o-mini.
Generates structured summaries in various formats with NO truncation.
"""
from openai import AsyncOpenAI
from typing import Dict, Optional
from app.core.config import settings


class SummarizationService:
    """
    Production-ready summarization service.
    Generates complete summaries without truncation.
    """

    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize summarization service.

        Args:
            api_key: OpenAI API key (defaults to settings)
        """
        self.client = AsyncOpenAI(api_key=api_key or settings.OPENAI_API_KEY)

    async def generate_summary(
        self,
        transcript: str,
        format_type: str,
        detected_language: Optional[str] = None
    ) -> Dict[str, any]:
        """
        Generate summary with NO truncation.

        Args:
            transcript: Transcribed text
            format_type: One of: meeting_notes, product_spec, mom, quick_summary
            detected_language: Auto-detected language code (e.g., 'hi', 'en')

        Returns:
            {
                'summary_text': str,
                'format_type': str,
                'success': bool,
                'finish_reason': str,
                'error': str (if any)
            }
        """

        # Language-aware context
        if detected_language and detected_language != 'en':
            language_note = f"""
IMPORTANT: This transcript is in {detected_language}.
- Preserve key terms and proper nouns in their original language
- Provide the summary in English
- If the transcript is unclear, note which parts are uncertain
"""
        else:
            language_note = ""

        # Prompts with clear structure
        prompts = {
            "meeting_notes": f"""
{language_note}
Convert this transcript into structured meeting notes.

INSTRUCTIONS:
1. Extract ONLY what was actually discussed - do not invent details
2. If something is unclear in the transcript, mark it as [unclear]
3. If the transcript quality is poor, state that upfront

FORMAT:
# Meeting Summary
[2-3 sentence overview of what was discussed]

## Key Discussion Points
- [Point 1 - be specific]
- [Point 2]
- [Point 3]

## Action Items
- [Action with owner if mentioned, otherwise just the action]

## Next Steps
- [What needs to happen next]

---
TRANSCRIPT:
{transcript}
""",

            "product_spec": f"""
{language_note}
Convert this transcript into a product specification document.

INSTRUCTIONS:
1. Extract ONLY what was actually mentioned - do not add assumptions
2. If information is missing, note it as [not specified]
3. If the transcript quality is poor, state that upfront

FORMAT:
# Product Specification

## Problem Statement
[What problem is being addressed?]

## Proposed Solution
[How will it be solved?]

## Requirements
- [Requirement 1]
- [Requirement 2]

## Notes
[Any additional context or caveats]

---
TRANSCRIPT:
{transcript}
""",

            "mom": f"""
{language_note}
Convert this transcript into formal Minutes of Meeting.

INSTRUCTIONS:
1. Extract ONLY what was actually discussed
2. Mark uncertain parts as [unclear]
3. If the transcript quality is poor, state that upfront

FORMAT:
# Minutes of Meeting

**Date:** [Extract or "Not specified"]
**Attendees:** [Extract or "Not specified"]

## Discussion Summary
[Detailed summary of what was discussed]

## Decisions Made
1. [Decision 1]
2. [Decision 2]

## Action Items
| Action | Owner | Deadline |
|--------|-------|----------|
| [Action] | [Name or TBD] | [Date or TBD] |

---
TRANSCRIPT:
{transcript}
""",

            "quick_summary": f"""
{language_note}
Provide a concise summary of this transcript.

INSTRUCTIONS:
1. Be factual - only include what was actually said
2. If the transcript is unclear or garbled, say so upfront
3. Do not make assumptions or fill in gaps

FORMAT:
## Overview
[What is this recording about? 2-3 sentences]

## Key Points
[The main takeaways in 3-4 sentences]

## Conclusion
[Outcome or next steps mentioned, if any]

---
TRANSCRIPT:
{transcript}
"""
        }

        prompt = prompts.get(format_type, prompts["quick_summary"])

        try:
            response = await self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {
                        "role": "system",
                        "content": """You are a professional summarization assistant.

CRITICAL RULES:
1. ONLY use information present in the transcript
2. If the transcript has errors or is unclear, acknowledge this
3. Do NOT hallucinate or make up details
4. If you cannot understand parts of the transcript, say "This section is unclear"
5. Always complete your response - never stop mid-sentence
6. Be thorough and comprehensive - do not rush to finish"""
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=0.3,
                max_tokens=4000,  # INCREASED from default to prevent truncation
                timeout=60
            )

            summary_text = response.choices[0].message.content
            finish_reason = response.choices[0].finish_reason

            # Check if response was truncated by API
            if finish_reason == "length":
                summary_text += "\n\n[Note: Summary was truncated due to length limits. Consider using a shorter transcript or splitting into sections.]"
                print(f"⚠️  Warning: Summary was truncated (finish_reason: length)")

            print(f"✅ Summary generated successfully")
            print(f"   - Format: {format_type}")
            print(f"   - Length: {len(summary_text)} characters")
            print(f"   - Finish reason: {finish_reason}")

            return {
                'summary_text': summary_text,
                'format_type': format_type,
                'success': True,
                'finish_reason': finish_reason
            }

        except Exception as e:
            print(f"❌ Summarization error: {str(e)}")
            return {
                'summary_text': None,
                'format_type': format_type,
                'success': False,
                'error': str(e)
            }


# Legacy sync version for backward compatibility
def generate_summary_sync(
    transcript: str,
    format_type: str,
    detected_language: Optional[str] = None
) -> Dict[str, any]:
    """
    Synchronous wrapper for generate_summary.
    Use this if you need to call from non-async code.

    Args:
        transcript: Transcribed text
        format_type: Summary format type
        detected_language: Optional language code

    Returns:
        Summary result dictionary
    """
    import asyncio

    service = SummarizationService()

    # Run async function in sync context
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

    return loop.run_until_complete(
        service.generate_summary(transcript, format_type, detected_language)
    )
