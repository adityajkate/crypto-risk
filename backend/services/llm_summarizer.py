"""LLM-based summarization service for cryptocurrency news articles."""

import asyncio
import os
import json
import logging
import re
from enum import Enum
from typing import List, Dict, Any, Optional
from google import genai

logger = logging.getLogger(__name__)

DEFAULT_LLM_CONFIDENCE = 50

SUMMARY_RESPONSE_SCHEMA = {
    "type": "object",
    "properties": {
        "summary": {"type": "string"},
        "sentiment": {"type": "string"},
        "confidence": {"type": "integer"},
        "key_insights": {"type": "array", "items": {"type": "string"}},
        "price_impact": {"type": "string"},
        "reasoning": {"type": "string"},
        "risk_factors": {"type": "array", "items": {"type": "string"}},
    },
    "required": [
        "summary",
        "sentiment",
        "confidence",
        "key_insights",
        "price_impact",
        "reasoning",
        "risk_factors",
    ],
}


class LLMSummarizer:
    """Service for generating intelligent summaries of crypto news using LLMs."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = "gemini-2.5-flash",
    ):
        """
        Initialize the LLM summarizer.

        Args:
            api_key: Google API key (defaults to GOOGLE_API_KEY env var)
            model: Gemini model to use
        """
        # Load from environment variable
        self.api_key = api_key or os.getenv("GOOGLE_API_KEY")
        self.model = model

        logger.debug(f"Initializing LLM Summarizer with Google Gemini...")
        logger.debug(
            f"API Key from env: {self.api_key[:20] if self.api_key else 'NONE'}..."
        )
        logger.debug(f"Model: {self.model}")

        if not self.api_key:
            logger.debug("ERROR: No API key found!")
            logger.warning(
                "GOOGLE_API_KEY not set - LLM summarization will be disabled"
            )
            logger.warning(
                "Add GOOGLE_API_KEY to your .env file to enable LLM summaries"
            )
            self.client = None
        else:
            # Log API key status (masked for security)
            key_preview = (
                f"{self.api_key[:10]}...{self.api_key[-4:]}"
                if len(self.api_key) > 14
                else "***"
            )
            logger.debug(f"API Key loaded: {key_preview}")
            logger.info(f"LLM Summarizer initialized successfully")
            logger.info(f"Model: {self.model}")
            logger.info(f"API Key loaded: {key_preview}")

            try:
                self.client = genai.Client(api_key=self.api_key)
                logger.debug("Google Gemini client created successfully!")
                logger.info("Google Gemini client created successfully")
            except Exception as e:
                logger.debug(f"ERROR creating client: {e}")
                logger.error(f"Failed to create Google Gemini client: {e}")
                self.client = None

    def _prepare_articles_text(
        self, articles: List[Dict[str, Any]], max_articles: int = 20
    ) -> str:
        """
        Prepare articles for LLM processing.

        Args:
            articles: List of article dictionaries
            max_articles: Maximum number of articles to include (default: 20)

        Returns:
            Formatted text containing article information
        """
        # Limit to most recent articles
        articles_subset = articles[:max_articles]

        formatted_articles = []
        for idx, article in enumerate(articles_subset, 1):
            title = article.get("title", "No title")
            source = article.get("source", "Unknown")
            full_content = article.get("full_content", article.get("summary", ""))

            # Truncate content to 2000 chars per article to stay within token limits
            content = full_content[:2000] if full_content else ""

            formatted_articles.append(
                f"Article {idx}:\n"
                f"Title: {title}\n"
                f"Source: {source}\n"
                f"Content: {content}\n"
            )

        return "\n---\n".join(formatted_articles)

    def _extract_response_text(self, response: Any) -> str:
        """Extract text from a Gemini response object."""
        try:
            text = response.text
            if text:
                return text.strip()
        except Exception:
            pass

        text_parts: List[str] = []
        for candidate in getattr(response, "candidates", []) or []:
            content = getattr(candidate, "content", None)
            for part in getattr(content, "parts", []) or []:
                part_text = getattr(part, "text", None)
                if part_text:
                    text_parts.append(part_text)

        return "\n".join(text_parts).strip()

    def _generate_content(self, prompt: str, coin: str) -> tuple[str, Any]:
        """Call Gemini API - NO FALLBACKS, fail fast."""
        try:
            logger.info(f"Calling Google Gemini API with model {self.model} for {coin}")
            response = self.client.models.generate_content(
                model=self.model,
                contents=prompt,
                config=genai.types.GenerateContentConfig(
                    temperature=0.3,
                    max_output_tokens=4096,  # Increased from 2048 to prevent truncation
                    response_mime_type="application/json",
                    response_json_schema=SUMMARY_RESPONSE_SCHEMA,
                ),
            )
            return self.model, response
        except Exception as exc:
            error_message = f"{self.model}: {type(exc).__name__}: {exc}"
            logger.error(f"Gemini request failed for {coin}: {error_message}")
            raise RuntimeError(error_message)

    def _parse_json_response(self, content: str) -> Dict[str, Any]:
        """Parse the first valid JSON object from a Gemini response."""
        decoder = json.JSONDecoder()
        candidates: List[str] = []
        cleaned = content.strip()
        fence_stripped = re.sub(r"^```(?:json)?\s*|\s*```$", "", cleaned, flags=re.IGNORECASE)

        for candidate in (cleaned, fence_stripped):
            if candidate:
                candidates.append(candidate)
            json_start = candidate.find("{")
            if json_start >= 0:
                candidates.append(candidate[json_start:])

                # Try to find the end of JSON object
                json_end = candidate.rfind("}")
                if json_end > json_start:
                    candidates.append(candidate[json_start:json_end + 1])

        parse_errors: List[str] = []
        for candidate in dict.fromkeys(candidates):
            try:
                parsed, _ = decoder.raw_decode(candidate)
                if isinstance(parsed, str):
                    parsed = json.loads(parsed)
                if isinstance(parsed, dict):
                    return parsed
            except json.JSONDecodeError as exc:
                parse_errors.append(f"{exc.msg} at char {exc.pos}")

                # Try to repair truncated JSON by closing unclosed strings and objects
                try:
                    repaired = self._attempt_json_repair(candidate, exc)
                    if repaired:
                        parsed = json.loads(repaired)
                        if isinstance(parsed, dict):
                            logger.warning(f"Successfully repaired truncated JSON response")
                            return parsed
                except Exception:
                    pass

        raise ValueError(
            "Gemini response did not contain a parsable JSON object"
            + (f" ({'; '.join(parse_errors[:3])})" if parse_errors else "")
        )

    def _attempt_json_repair(self, content: str, error: json.JSONDecodeError) -> Optional[str]:
        """Attempt to repair truncated or malformed JSON."""
        try:
            # If error is "Unterminated string", try to close the string
            if "Unterminated string" in error.msg:
                # Find the position of the error
                pos = error.pos

                # Try to find the last complete field before the error
                # Look backwards from error position to find the last complete value
                truncated = content[:pos]

                # Find the last comma or opening brace
                last_comma = truncated.rfind(',')
                last_brace = truncated.rfind('{')

                # If we have a comma, truncate there and close the object
                if last_comma > last_brace:
                    repaired = truncated[:last_comma] + '}'
                else:
                    # Otherwise just close at the error position
                    repaired = truncated + '"}'

                return repaired

            # If missing closing brace, try to add it
            if "Expecting" in error.msg:
                # Count open and close braces
                open_braces = content.count("{")
                close_braces = content.count("}")
                if open_braces > close_braces:
                    # Add missing closing braces
                    repaired = content + ("}" * (open_braces - close_braces))
                    return repaired
        except Exception:
            pass

        return None

    def _extract_structured_response(self, response: Any) -> Optional[Dict[str, Any]]:
        """Prefer the SDK-parsed payload when Gemini returns structured output."""
        parsed = getattr(response, "parsed", None)
        if parsed is None:
            return None

        if hasattr(parsed, "model_dump"):
            parsed = parsed.model_dump()

        if isinstance(parsed, Enum):
            parsed = parsed.value

        if isinstance(parsed, dict):
            return parsed

        if isinstance(parsed, str):
            return self._parse_json_response(parsed)

        return None

    def _normalize_string_list(self, value: Any) -> List[str]:
        """Coerce a Gemini field into a clean list of strings."""
        if value is None:
            return []

        if isinstance(value, str):
            items = [value]
        elif isinstance(value, (list, tuple, set)):
            items = list(value)
        else:
            items = [value]

        normalized: List[str] = []
        for item in items:
            text = str(item).strip()
            if text:
                normalized.append(text)

        return normalized

    def _normalize_confidence(self, value: Any) -> int:
        """Accept 0-1, 0-100, or percent-string confidence values."""
        if value is None or isinstance(value, bool):
            return DEFAULT_LLM_CONFIDENCE

        try:
            if isinstance(value, str):
                numeric = float(value.strip().rstrip("%"))
            else:
                numeric = float(value)
        except (TypeError, ValueError):
            return DEFAULT_LLM_CONFIDENCE

        if 0 <= numeric <= 1:
            numeric *= 100

        return max(0, min(100, int(round(numeric))))

    def _normalize_summary_payload(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Fill minor schema gaps without discarding an otherwise useful summary."""
        if not isinstance(payload, dict):
            raise ValueError("Gemini response was not a JSON object")

        summary = str(payload.get("summary", "")).strip()
        if not summary:
            raise ValueError("Gemini response was missing required field: summary")

        sentiment = str(payload.get("sentiment", "Neutral")).strip() or "Neutral"
        price_impact = str(payload.get("price_impact", "None")).strip() or "None"
        reasoning = (
            str(payload.get("reasoning", "Generated from recent articles")).strip()
            or "Generated from recent articles"
        )

        return {
            **payload,
            "summary": summary,
            "sentiment": sentiment,
            "confidence": self._normalize_confidence(
                payload.get("confidence", DEFAULT_LLM_CONFIDENCE)
            ),
            "key_insights": self._normalize_string_list(
                payload.get("key_insights", payload.get("key_topics"))
            ),
            "price_impact": price_impact,
            "reasoning": reasoning,
            "risk_factors": self._normalize_string_list(payload.get("risk_factors")),
        }

    def _create_prompt(self, articles_text: str, coin: str) -> str:
        """
        Create the prompt for the LLM.

        Args:
            articles_text: Formatted articles text
            coin: Cryptocurrency identifier

        Returns:
            Complete prompt string
        """
        return f"""You are a cryptocurrency market analyst. Analyze the following news articles about {coin.upper()} and provide a comprehensive summary.

{articles_text}

Based on these articles, provide a JSON response with the following structure:
{{
  "summary": "A concise 1-2 paragraph summary of key developments",
  "sentiment": "One of: Bullish, Bearish, Mixed-Bullish, Mixed-Bearish, or Neutral",
  "confidence": 85,
  "key_insights": ["insight1", "insight2", "insight3"],
  "price_impact": "One of: High, Medium, Low, or None",
  "reasoning": "Brief explanation (max 100 words)",
  "risk_factors": ["risk1", "risk2"]
}}

Guidelines:
- Be concise and objective
- Keep summary under 300 words
- Keep reasoning under 100 words
- Limit to 3-5 key insights
- Limit to 2-4 risk factors
- Focus on market-moving information only

CRITICAL: Return ONLY valid, complete JSON. Keep all text fields concise to avoid truncation."""

    def summarize_articles(
        self, articles: List[Dict[str, Any]], coin: str
    ) -> Dict[str, Any]:
        """
        Generate an intelligent summary of articles using LLM (synchronous).

        Args:
            articles: List of article dictionaries
            coin: Cryptocurrency identifier

        Returns:
            Dictionary containing summary, sentiment, insights, and risk factors
        """
        # Check if LLM is available
        if not self.client:
            logger.debug(f"Client is None - summary unavailable for {coin}")
            logger.warning(f"LLM client not initialized - summary unavailable for {coin}")
            return self._unavailable_summary(
                coin,
                error="GOOGLE_API_KEY not configured or Gemini client unavailable",
            )

        if not articles:
            logger.debug(f"No articles provided for {coin}")
            logger.info(f"No articles provided for {coin}")
            return {
                "summary": f"No recent news data available for {coin}.",
                "sentiment": "Neutral",
                "confidence": 0,
                "key_insights": [],
                "price_impact": "None",
                "reasoning": "No articles to analyze",
                "risk_factors": [],
                "used_fallback": False,
                "summary_source": "no_data",
                "model_used": None,
                "llm_error": None,
            }

        try:
            content = ""
            result = None
            # Prepare articles text
            articles_text = self._prepare_articles_text(articles)
            logger.debug(
                f"Prepared {len(articles)} articles for {coin} ({len(articles_text)} chars)"
            )
            logger.info(
                f"Prepared {len(articles)} articles for LLM analysis ({len(articles_text)} chars)"
            )

            # Create prompt
            prompt = self._create_prompt(articles_text, coin)

            # Call LLM
            model_used, response = self._generate_content(prompt, coin)

            # Parse response
            content = self._extract_response_text(response)
            if content:
                logger.debug(f"Received LLM response ({len(content)} chars)")
                logger.info(f"Received LLM response ({len(content)} chars)")

            structured_result = self._extract_structured_response(response)
            if structured_result is not None:
                result = self._normalize_summary_payload(structured_result)
                logger.info("Using Gemini structured response payload")
            elif result is None:
                if not content:
                    logger.error("Gemini returned an empty response body")
                    return self._unavailable_summary(
                        coin,
                        error="Gemini returned an empty response",
                    )

                result = self._normalize_summary_payload(
                    self._parse_json_response(content)
                )

            logger.debug(
                f"Successfully generated LLM summary for {coin} - Sentiment: {result.get('sentiment')}"
            )
            logger.info(
                f"Successfully generated LLM summary for {coin} - Sentiment: {result.get('sentiment')}, Confidence: {result.get('confidence')}%"
            )
            result["used_fallback"] = False
            result["summary_source"] = "llm"
            result["model_used"] = model_used
            result["llm_error"] = None
            return result

        except (json.JSONDecodeError, ValueError) as e:
            logger.error(f"Failed to parse LLM response as JSON: {e}")
            logger.error(f"Raw Gemini content (first 500 chars): {content[:500] if content else 'EMPTY'}")
            logger.error(f"Raw Gemini content (last 200 chars): {content[-200:] if content and len(content) > 200 else 'N/A'}")
            return self._unavailable_summary(
                coin,
                error=f"Failed to parse Gemini JSON response: {e}",
            )

        except Exception as e:
            logger.debug(f"Error calling LLM for {coin}: {type(e).__name__}: {e}")
            logger.error(f"Error calling LLM for {coin}: {type(e).__name__}: {e}")
            return self._unavailable_summary(
                coin,
                error=f"{type(e).__name__}: {e}",
            )

    async def summarize_articles_async(
        self, articles: List[Dict[str, Any]], coin: str
    ) -> Dict[str, Any]:
        """
        Async wrapper for summarize_articles.
        Runs the synchronous LLM call in a thread to avoid blocking the event loop.

        Args:
            articles: List of article dictionaries
            coin: Cryptocurrency identifier

        Returns:
            Dictionary containing summary, sentiment, insights, and risk factors
        """
        return await asyncio.to_thread(self.summarize_articles, articles, coin)

    def _unavailable_summary(
        self,
        coin: str,
        error: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Return an explicit unavailable state instead of fabricating a fallback summary."""
        logger.info(f"AI summary unavailable for {coin}")
        return {
            "summary": "AI summary unavailable for this coin right now.",
            "sentiment": "Neutral",
            "confidence": 0,
            "key_insights": [],
            "price_impact": "None",
            "reasoning": "No synthetic fallback summary was generated.",
            "risk_factors": [],
            "used_fallback": False,
            "summary_source": "unavailable",
            "model_used": None,
            "llm_error": error,
        }


# Global instance
_summarizer_instance = None


def get_summarizer(api_key: Optional[str] = None) -> LLMSummarizer:
    """Get or create the global LLM summarizer instance."""
    global _summarizer_instance

    if _summarizer_instance is None:
        if api_key is None:
            try:
                from backend.api.config import settings

                api_key = settings.google_api_key
            except Exception:
                api_key = None

        _summarizer_instance = LLMSummarizer(api_key=api_key)

    return _summarizer_instance
