from datetime import datetime
from typing import Optional
import logging
import json
from google.cloud import storage
import io
from app.config import settings
import pdfplumber

    
logger = logging.getLogger("app.utils.common")

def normalize_datetime(dt):
    if hasattr(dt, "replace"):  # works for both datetime and DatetimeWithNanoseconds
        return dt.replace(tzinfo=None)  # remove tzinfo if needed
    return dt


def clean_json_response(response_text: str) -> str:
    """Clean JSON response by removing markdown formatting and returning valid JSON.
    
    Args:
        response_text: Raw response text that may contain markdown formatting
        
    Returns:
        Cleaned JSON string, or empty JSON object "{}" if invalid
    """
    if not response_text:
        return "{}"
    
    cleaned = response_text.strip()
    
    # Remove markdown code block formatting
    if cleaned.startswith('```json'):
        cleaned = cleaned[7:]  # Remove ```json
        if cleaned.endswith('```'):
            cleaned = cleaned[:-3]  # Remove trailing ```
    elif cleaned.startswith('```'):
        cleaned = cleaned[3:]  # Remove ```
        if cleaned.endswith('```'):
            cleaned = cleaned[:-3]  # Remove trailing ```
    
    # Remove any extra whitespace or newlines at the start/end
    cleaned = cleaned.strip()
    
    # If the response is empty after cleaning, return empty JSON
    if not cleaned:
        return "{}"
    
    # Validate that it's valid JSON
    try:
        json.loads(cleaned)  # This will raise JSONDecodeError if invalid
        return cleaned
    except json.JSONDecodeError:
        logger.warning("Cleaned response is not valid JSON: %s", repr(cleaned[:100]))
        return "{}"


from urllib.parse import urlparse, unquote

def extract_blob_name(storage_path: str) -> Optional[str]:
    try:
        parsed = urlparse(storage_path)
        path_no_slash = parsed.path.lstrip('/')
        parts = path_no_slash.split('/', 1)

        bucket_names = {settings.FIREBASE_STORAGE_BUCKET}

        # Case 1 & 2: bucket in path
        if len(parts) == 2 and (parts[0] in bucket_names):
            return unquote(parts[1].split('?')[0])

        # Case 3: bucket in domain, object in path
        if parsed.netloc in bucket_names and path_no_slash:
            return unquote(path_no_slash.split('?')[0])

        # Fallback: last path segment only
        return unquote(parts[-1].split('?')[0])
    except Exception:
        logger.exception("Failed to parse blob name from storage path '%s'", storage_path)
        return None

def download_blob_text_with_parsing(storage_client: storage.Client, blob_name: str) -> Optional[str]:
    if not blob_name:
        return None

    bucket_name = settings.FIREBASE_STORAGE_BUCKET or getattr(settings, "GCS_BUCKET", None)
    if not bucket_name:
        logger.info("No bucket name configured; skipping blob download")
        return None

    try:
        bucket = storage_client.bucket(bucket_name)
        blob = bucket.blob(blob_name)
        blob.reload()  # get metadata

        content_type = blob.content_type or ""
        logger.info("Downloading blob '%s' with content_type='%s'", blob_name, content_type)

        file_bytes = blob.download_as_bytes()

        # For textual content types, decode directly
        if "text" in content_type or content_type in ("application/json", "application/xml"):
            try:
                return file_bytes.decode("utf-8")
            except UnicodeDecodeError:
                return file_bytes.decode("latin-1", errors="replace")

        # PDF parsing
        elif content_type == "application/pdf" or blob_name.lower().endswith(".pdf"):
            text_parts = []
            with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
                for page in pdf.pages:
                    text_parts.append(page.extract_text() or "")
            return "\n".join(text_parts).strip() or None

        else:
            logger.info("Unsupported content type or extension for blob '%s'", blob_name)
            return None

    except Exception as e:
        logger.debug("Could not download or parse blob '%s': %s", blob_name, e)
        return None