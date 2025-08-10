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
from app.utils.common import clean_json_response

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

insights_system_prompt = """
You are an expert insurance document analyzer that extracts valuable insights from document summaries.
Your task is to identify and extract key business-critical information based on the document type.

For Insurance Premium documents, extract:
- Premium amount and currency
- Coverage types and limits
- Policy period (start/end dates)
- Deductibles
- Key benefits and exclusions

For Claims documents, extract:
- Claim amount and status
- Incident date and type
- Coverage involved
- Settlement details

For Policy documents, extract:
- Policy number and type
- Premium details
- Coverage limits
- Terms and conditions highlights

For Financial documents, extract:
- Key financial figures
- Payment schedules
- Important dates

IMPORTANT: Return ONLY the JSON object without any markdown formatting, code blocks, or additional text.
Do NOT wrap the response in ```json or ``` blocks.

Format your response as structured JSON with the following schema:
{
  "document_type": "string",
  "key_insights": {
    "financial_data": {
      "amounts": [{"label": "string", "value": "number", "currency": "string"}],
      "dates": [{"label": "string", "date": "YYYY-MM-DD"}]
    },
    "coverage_details": ["string"],
    "critical_information": ["string"]
  },
  "confidence_score": "number between 0-1"
}

Rules:
- Only extract information that is explicitly mentioned in the summary
- Do not hallucinate or assume missing details
- Use confidence_score to indicate how certain you are about the extracted data
- If specific information is not available, use null values
- Maintain accuracy over completeness
- Return ONLY the JSON object, no markdown formatting
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

	def extract_insights(self, summary_text: str, filename: Optional[str] = None, max_output_tokens: int = 2048) -> str:
		"""Extract key insights from a document summary.

		Args:
			summary_text: The document summary text.
			filename: Optional filename for context.
			max_output_tokens: Upper bound for insights response length (Claude tokens).

		Returns:
			JSON string containing structured insights.
		"""
		cleaned_summary = (summary_text or "").strip()

		logger.info("Extracting insights from summary with length=%d", len(cleaned_summary))

		if not cleaned_summary:
			return "{}"  # Empty insights for empty summary

		if not self._client:
			logger.info("No LLM client available; using fallback insights extractor")
			return self._fallback_insights(cleaned_summary, filename)

		user_prompt = self._build_insights_prompt(cleaned_summary, filename)

		try:
			logger.info("Calling Claude model=%s for insights extraction", self.model)
			resp = self._client.messages.create(
				model=self.model,
				max_tokens=max_output_tokens,
				temperature=0.1,  # Lower temperature for more consistent structured output
				system=insights_system_prompt,
				messages=[{"role": "user", "content": user_prompt}],
			)
			
			if hasattr(resp, "content") and resp.content:
				parts = []
				logger.info("Calling Claude model=%s for insights extraction, found content blocks", self.model)

				for block in resp.content:
					text_part = getattr(block, "text", None) or (block.get("text") if isinstance(block, dict) else None)
					if text_part:
						parts.append(text_part)
				insights_text = "\n".join(parts).strip()
				
				# Clean up any markdown formatting that might be present
				insights_text = clean_json_response(insights_text)
			else:
				insights_text = "{}"  # Fallback to empty JSON
				
			return insights_text
		except Exception as e:  # pragma: no cover - network path
			logger.exception("Claude insights extraction failed, falling back: %s", e)
			return self._fallback_insights(cleaned_summary, filename)

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

	def _build_insights_prompt(self, summary_text: str, filename: Optional[str]) -> str:
		prefix = f"Filename: {filename}\n" if filename else ""
		# Truncate summary if too long
		max_chars = 10000
		truncated = summary_text[:max_chars]
		if len(summary_text) > max_chars:
			truncated += "\n[TRUNCATED]"
		return (
			f"{prefix}Please extract key insights from the following document summary.\n\n" \
			f"--- SUMMARY START ---\n{truncated}\n--- SUMMARY END ---\n\n" \
			f"Extract valuable information like premium amounts, coverage details, policy terms, " \
			f"important dates, and other business-critical data. Return the response in the specified JSON format."
		)

	def _fallback_summary(self, text: str, filename: Optional[str]) -> str:
		"""Heuristic fallback summarizer (no external calls)."""
		# Simple fallback: truncate and add basic info
		max_chars = 500
		truncated = text[:max_chars]
		if len(text) > max_chars:
			truncated += "..."
		
		title = filename or "Document"
		return f"# {title}\n\n**TL;DR**: Document content preview (AI summarization unavailable)\n\n## Content Preview\n{truncated}"
	
	def _fallback_insights(self, summary_text: str, filename: Optional[str]) -> str:
		"""Fallback insights extractor using simple heuristics."""
		import re
		import json
		
		# Basic pattern matching for common insurance terms
		insights = {
			"document_type": "unknown",
			"key_insights": {
				"financial_data": {
					"amounts": [],
					"dates": []
				},
				"coverage_details": [],
				"critical_information": []
			},
			"confidence_score": 0.3
		}
		
		# Try to detect document type from filename or content
		if filename:
			filename_lower = filename.lower()
			if any(term in filename_lower for term in ["premium", "policy", "insurance"]):
				insights["document_type"] = "insurance_policy"
			elif any(term in filename_lower for term in ["claim", "settlement"]):
				insights["document_type"] = "insurance_claim"
		
		# Look for monetary amounts
		money_patterns = [
			r'[\$₹€£¥]\s*[\d,]+(?:\.\d{2})?',
			r'(?:premium|amount|sum|cost|price)[\s:]*[\$₹€£¥]?\s*[\d,]+(?:\.\d{2})?'
		]
		
		for pattern in money_patterns:
			matches = re.findall(pattern, summary_text, re.IGNORECASE)
			for match in matches:
				insights["key_insights"]["financial_data"]["amounts"].append({
					"label": "Amount found",
					"value": match,
					"currency": "unknown"
				})
		
		# Look for dates
		date_patterns = [
			r'\d{1,2}[-/]\d{1,2}[-/]\d{4}',
			r'\d{4}[-/]\d{1,2}[-/]\d{1,2}'
		]
		
		for pattern in date_patterns:
			matches = re.findall(pattern, summary_text)
			for match in matches:
				insights["key_insights"]["financial_data"]["dates"].append({
					"label": "Date found",
					"date": match
				})
		
		# Add some basic critical information
		if any(term in summary_text.lower() for term in ["premium", "coverage", "policy"]):
			insights["key_insights"]["critical_information"].append("Insurance-related document detected")
		
		return json.dumps(insights, indent=None)  # Return compact JSON without indentation


# Lazy singleton pattern so logs occur after logging config & only when first used
_llm_service_instance: Optional[LLMService] = None

def get_llm_service() -> LLMService:
	global _llm_service_instance
	if _llm_service_instance is None:
		_llm_service_instance = LLMService()
	return _llm_service_instance


