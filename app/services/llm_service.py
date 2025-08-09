"""LLM Service integrating with Anthropic Claude for summarization.

Only responsibility (per request): provide a summarization method.

Environment:
  ANTHROPIC_API_KEY must be set for real Claude calls.

If the anthropic package or API key is missing, a lightweight
fallback summarizer (rule-based) is used so the app can still run.
"""

from __future__ import annotations

from fileinput import filename
import os
import logging
from typing import Optional
from app.config import settings

logger = logging.getLogger("app.llm_service")
import anthropic  # type: ignore


system_prompt = """
You are an efficient summarization assistant for insurance-related documents.
Produce a concise, factual, and well-structured summary in Markdown format, containing:
	1.	Title (if clearly derivable from the document)
	2.	TL;DR — one sentence capturing the essence of the document
    3.  When complex data (e.g., financials, timelines, statistics) is present, format it as a Markdown table using the provided table data. 
Preserve column and row names exactly as in the source.
	4.	Key Points — bullet list of main facts, terms, and conditions
	5.	Action Items — bullet list of any required actions (if applicable)

Rules:
	•	Only output valid Markdown elements (e.g., headings, bullet lists, numbered lists, tables, links, images).
	•	Do not include <script> tags or any other executable or dangerous code.
	•	Keep language factual; do not hallucinate or assume missing details.
	•	Maintain original meaning; avoid altering legal or contractual terms.
	•	Use clear, reader-friendly formatting for quick scanning.
"""
class LLMService:
	"""Service wrapper for LLM interactions (currently: summarization via Claude)."""

	def __init__(self, api_key: Optional[str] = None, model: str = "claude-sonnet-4-20250514"):
		self.api_key = api_key or settings.ANTHROPIC_API_KEY
		self.model = model
		logger.info("Initializing LLMService (model=%s, api_key_set=%s)", self.model, os.environ.get("ANTHROPIC_API_KEY"))
  
		if self.api_key and not anthropic:
			logger.warning(
				"ANTHROPIC_API_KEY provided but 'anthropic' package not installed. Using fallback summarizer." \
			)
		if not self.api_key:
			logger.info("No ANTHROPIC_API_KEY set. Using fallback summarizer.")
		logger.debug("Anthropic SDK available=%s", bool(anthropic))
		self._client = anthropic.Anthropic(api_key=self.api_key) if (self.api_key and anthropic) else None

	def summarize(self, text: str, filename: Optional[str] = None, max_output_tokens: int = 1024) -> str:
		"""Generate a summary for the provided text.

		Args:
			text: Raw document text content.
			filename: Optional filename for context.
			max_output_tokens: Upper bound for summary length (Claude tokens).

		Returns:
			Summary string.
		"""
		cleaned = (text or "").strip()

		logger.info("Summarizing text with length=%d", len(cleaned))

		if not cleaned:
			return ""  # Nothing to summarize

		if not self._client:
			logger.info("No LLM client available; using fallback summarizer")
			return self._fallback_summary(cleaned, filename)


		user_prompt = self._build_user_prompt(cleaned, filename)

		try:
			logger.info("Calling Claude model=%s for summarization (chars=%d)", self.model, len(cleaned))
			resp = self._client.messages.create(
				model=self.model,
				max_tokens=max_output_tokens,
				temperature=0.3,
				system=system_prompt,
				messages=[{"role": "user", "content": user_prompt}],
			)
			# anthropic SDK v1: resp.content is a list of content blocks
			if hasattr(resp, "content") and resp.content:
				# Join all text segments
				parts = []
				logger.info("Calling Claude model=%s for summarization (chars=%d), found content blocks", self.model, len(cleaned))

				for block in resp.content:
					# Block may be dict-like or object; handle both
					text_part = getattr(block, "text", None) or (block.get("text") if isinstance(block, dict) else None)
					if text_part:
						parts.append(text_part)
				summary_text = "\n".join(parts).strip()
			else:
				summary_text = ""  # Unexpected shape
			return summary_text
		except Exception as e:  # pragma: no cover - network path
			logger.exception("Claude summarization failed, falling back: %s", e)
			return self._fallback_summary(cleaned, filename)

	# ------------------------- Internal Helpers ------------------------- #
	def _build_user_prompt(self, text: str, filename: Optional[str]) -> str:
		prefix = f"Filename: {filename}\n" if filename else ""
		# Truncate extremely long texts (simple safeguard)
		max_chars = 20000
		truncated = text[:max_chars]
		if len(text) > max_chars:
			truncated += "\n[TRUNCATED]"
		return (
			f"{prefix}Please summarize the following document.\n\n" \
			f"--- DOCUMENT START ---\n{truncated}\n--- DOCUMENT END ---"
		)

	def _fallback_summary(self, text: str, filename: Optional[str]) -> str:
		"""Heuristic fallback summarizer (no external calls)."""
        # Todo
		return


# Lazy singleton pattern so logs occur after logging config & only when first used
_llm_service_instance: Optional[LLMService] = None

def get_llm_service() -> LLMService:
	global _llm_service_instance
	if _llm_service_instance is None:
		_llm_service_instance = LLMService()
	return _llm_service_instance


