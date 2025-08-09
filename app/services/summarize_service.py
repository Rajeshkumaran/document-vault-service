"""Summarize Service for document summarization and storage."""

import logging
from datetime import datetime
from typing import Optional
from fastapi import HTTPException
from google.cloud.exceptions import GoogleCloudError

from app.database import get_firestore_client
from app.schemas.document import DocumentSummaryCreate, DocumentSummaryResponse
from app.models.document import DocumentSummary
from app.services.llm_service import get_llm_service

logger = logging.getLogger("app.summarize_service")


class SummarizeService:
    """Service for handling document summarization and summary storage."""
    
    def __init__(self):
        self.firestore_client = get_firestore_client()
        self.llm_service = get_llm_service()

    async def store_document_summary(self, document_id: str, summary_text: str) -> DocumentSummaryResponse:
        """Store a document summary in Firebase."""
        try:
            logger.info("Storing summary for document_id=%s", document_id)
            
            summary_data = {
                "document_id": document_id,
                "summary_text": summary_text,
                "created_at": datetime.utcnow(),
                "updated_at": datetime.utcnow()
            }
            
            # Store in the document_summaries collection
            import asyncio
            loop = asyncio.get_running_loop()
            summary_ref = self.firestore_client.collection("document_summaries").document(document_id)
            await loop.run_in_executor(None, summary_ref.set, summary_data)
            
            logger.info("Successfully stored summary for document_id=%s", document_id)
            return DocumentSummaryResponse(**summary_data)
            
        except GoogleCloudError as e:
            logger.exception("Google Cloud error storing document summary")
            raise HTTPException(status_code=502, detail=f"Firestore error: {e}")
        except Exception as e:
            logger.exception("Unexpected error storing document summary")
            raise HTTPException(status_code=500, detail=f"Failed to store document summary: {e}")

    async def get_stored_document_summary(self, document_id: str) -> Optional[DocumentSummaryResponse]:
        """Retrieve a stored document summary from Firebase."""
        try:
            logger.info("Retrieving stored summary for document_id=%s", document_id)
            
            import asyncio
            loop = asyncio.get_running_loop()
            summary_ref = self.firestore_client.collection("document_summaries").document(document_id)
            summary_doc = await loop.run_in_executor(None, summary_ref.get)
            
            if not summary_doc.exists:
                logger.info("No stored summary found for document_id=%s", document_id)
                return None
            
            summary_data = summary_doc.to_dict()
            logger.info("Found stored summary for document_id=%s", document_id)
            return DocumentSummaryResponse(**summary_data)
            
        except GoogleCloudError as e:
            logger.exception("Google Cloud error retrieving document summary")
            raise HTTPException(status_code=502, detail=f"Firestore error: {e}")
        except Exception as e:
            logger.exception("Unexpected error retrieving document summary")
            raise HTTPException(status_code=500, detail=f"Failed to retrieve document summary: {e}")

    async def generate_document_summary(self, text_content: str, filename: str) -> str:
        """Generate a summary for document content using LLM service."""
        try:
            logger.info("Generating summary for document with filename=%s", filename)
            
            if not text_content or not text_content.strip():
                logger.warning("No text content provided for summarization")
                return ""
            
            summary_text = self.llm_service.summarize(text_content, filename)
            logger.info("Successfully generated summary for document")
            return summary_text
            
        except Exception as e:
            logger.exception("Error generating document summary")
            # Don't raise HTTPException here, let the caller decide how to handle it
            return f"Error generating summary: {str(e)}"

    async def get_or_generate_summary(self, document_id: str, text_content: str, filename: str) -> str:
        """Get existing summary or generate new one if not exists."""
        try:
            # First try to get stored summary
            stored_summary = await self.get_stored_document_summary(document_id)
            if stored_summary:
                logger.info("Using stored summary for document_id=%s", document_id)
                return stored_summary.summary_text
            
            # Generate new summary
            logger.info("No stored summary found, generating new one for document_id=%s", document_id)
            summary_text = await self.generate_document_summary(text_content, filename)
            
            if summary_text:
                # Store the generated summary for future use
                try:
                    await self.store_document_summary(document_id, summary_text)
                    logger.info("Successfully stored generated summary for future use")
                except Exception as e:
                    logger.warning("Failed to store generated summary: %s", e)
            
            return summary_text
            
        except Exception as e:
            logger.exception("Error in get_or_generate_summary")
            return f"Error processing summary: {str(e)}"

    async def update_document_summary(self, document_id: str, new_summary_text: str) -> DocumentSummaryResponse:
        """Update an existing document summary."""
        try:
            logger.info("Updating summary for document_id=%s", document_id)
            
            summary_data = {
                "document_id": document_id,
                "summary_text": new_summary_text,
                "updated_at": datetime.utcnow()
            }
            
            # Check if summary exists first
            existing_summary = await self.get_stored_document_summary(document_id)
            if existing_summary:
                # Update existing
                summary_data["created_at"] = existing_summary.created_at
                import asyncio
                loop = asyncio.get_running_loop()
                summary_ref = self.firestore_client.collection("document_summaries").document(document_id)
                await loop.run_in_executor(None, summary_ref.update, summary_data)
                logger.info("Successfully updated existing summary for document_id=%s", document_id)
            else:
                # Create new if doesn't exist
                summary_data["created_at"] = datetime.utcnow()
                import asyncio
                loop = asyncio.get_running_loop()
                summary_ref = self.firestore_client.collection("document_summaries").document(document_id)
                await loop.run_in_executor(None, summary_ref.set, summary_data)
                logger.info("Successfully created new summary for document_id=%s", document_id)
            
            return DocumentSummaryResponse(**summary_data)
            
        except GoogleCloudError as e:
            logger.exception("Google Cloud error updating document summary")
            raise HTTPException(status_code=502, detail=f"Firestore error: {e}")
        except Exception as e:
            logger.exception("Unexpected error updating document summary")
            raise HTTPException(status_code=500, detail=f"Failed to update document summary: {e}")

    async def delete_document_summary(self, document_id: str) -> bool:
        """Delete a document summary."""
        try:
            logger.info("Deleting summary for document_id=%s", document_id)
            
            import asyncio
            loop = asyncio.get_running_loop()
            summary_ref = self.firestore_client.collection("document_summaries").document(document_id)
            await loop.run_in_executor(None, summary_ref.delete)
            
            logger.info("Successfully deleted summary for document_id=%s", document_id)
            return True
            
        except GoogleCloudError as e:
            logger.exception("Google Cloud error deleting document summary")
            raise HTTPException(status_code=502, detail=f"Firestore error: {e}")
        except Exception as e:
            logger.exception("Unexpected error deleting document summary")
            raise HTTPException(status_code=500, detail=f"Failed to delete document summary: {e}")
