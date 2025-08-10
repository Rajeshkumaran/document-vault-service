"""Insights Service for document insights generation and storage."""

import logging
import json
from datetime import datetime
from typing import Optional
from fastapi import HTTPException
from google.cloud.exceptions import GoogleCloudError

from app.database import get_firestore_client
from app.schemas.document import DocumentInsightsResponse
from app.services.llm_service import get_llm_service

logger = logging.getLogger("app.insights_service")


class InsightsService:
    """Service for handling document insights generation and storage."""
    
    def __init__(self):
        self.firestore_client = get_firestore_client()
        self.llm_service = get_llm_service()

    async def generate_document_insights(self, summary_text: str, filename: str) -> str:
        """Generate insights for a document summary using LLM service."""
        try:
            logger.info("Generating insights for document with filename=%s", filename)
            
            if not summary_text or not summary_text.strip():
                logger.warning("No summary text provided for insights generation")
                return "{}"
            
            insights_json = self.llm_service.extract_insights(summary_text, filename)
            logger.info("Successfully generated insights for document")
            return insights_json
            
        except Exception as e:
            logger.exception("Error generating document insights")
            # Return a fallback insights structure instead of raising
            fallback_insights = {
                "document_type": "unknown",
                "key_insights": {
                    "financial_data": {"amounts": [], "dates": []},
                    "coverage_details": [],
                    "critical_information": [f"Error generating insights: {str(e)}"]
                },
                "confidence_score": 0.0
            }
            return json.dumps(fallback_insights)

    async def store_document_insights(self, document_id: str, insights_json: str) -> DocumentInsightsResponse:
        """Store document insights in Firebase."""
        try:
            logger.info("Storing insights for document_id=%s", document_id)
            
            insights_data = {
                "document_id": document_id,
                "insights_data": insights_json,
                "created_at": datetime.utcnow(),
                "updated_at": datetime.utcnow()
            }
            
            # Store in the document_insights collection
            import asyncio
            loop = asyncio.get_running_loop()
            insights_ref = self.firestore_client.collection("document_insights").document(document_id)
            await loop.run_in_executor(None, insights_ref.set, insights_data)
            
            logger.info("Successfully stored insights for document_id=%s", document_id)
            return DocumentInsightsResponse(**insights_data)
            
        except GoogleCloudError as e:
            logger.exception("Google Cloud error storing document insights")
            raise HTTPException(status_code=502, detail=f"Firestore error: {e}")
        except Exception as e:
            logger.exception("Unexpected error storing document insights")
            raise HTTPException(status_code=500, detail=f"Failed to store document insights: {e}")

    async def get_stored_document_insights(self, document_id: str) -> Optional[DocumentInsightsResponse]:
        """Retrieve stored document insights from Firebase."""
        try:
            logger.info("Retrieving stored insights for document_id=%s", document_id)
            
            import asyncio
            loop = asyncio.get_running_loop()
            insights_ref = self.firestore_client.collection("document_insights").document(document_id)
            insights_doc = await loop.run_in_executor(None, insights_ref.get)
            
            if not insights_doc.exists:
                logger.info("No stored insights found for document_id=%s", document_id)
                return None
            
            insights_data = insights_doc.to_dict()
            logger.info("Found stored insights for document_id=%s", document_id)
            return DocumentInsightsResponse(**insights_data)
            
        except GoogleCloudError as e:
            logger.exception("Google Cloud error retrieving document insights")
            raise HTTPException(status_code=502, detail=f"Firestore error: {e}")
        except Exception as e:
            logger.exception("Unexpected error retrieving document insights")
            raise HTTPException(status_code=500, detail=f"Failed to retrieve document insights: {e}")

    async def get_or_generate_insights(self, document_id: str, summary_text: str, filename: str) -> str:
        """Get existing insights or generate new ones from summary if not exists."""
        try:
            # First try to get stored insights
            stored_insights = await self.get_stored_document_insights(document_id)
            if stored_insights:
                logger.info("Using stored insights for document_id=%s", document_id)
                return stored_insights.insights_data
            
            # Generate new insights from summary
            logger.info("No stored insights found, generating new ones for document_id=%s", document_id)
            insights_json = await self.generate_document_insights(summary_text, filename)
            
            if insights_json and insights_json != "{}":
                # Store the generated insights for future use
                try:
                    await self.store_document_insights(document_id, insights_json)
                    logger.info("Successfully stored generated insights for future use")
                except Exception as e:
                    logger.warning("Failed to store generated insights: %s", e)
            
            return insights_json
            
        except Exception as e:
            logger.exception("Error in get_or_generate_insights")
            fallback_insights = {
                "document_type": "unknown",
                "key_insights": {
                    "financial_data": {"amounts": [], "dates": []},
                    "coverage_details": [],
                    "critical_information": [f"Error processing insights: {str(e)}"]
                },
                "confidence_score": 0.0
            }
            return json.dumps(fallback_insights)

    async def update_document_insights(self, document_id: str, new_insights_json: str) -> DocumentInsightsResponse:
        """Update existing document insights."""
        try:
            logger.info("Updating insights for document_id=%s", document_id)
            
            insights_data = {
                "document_id": document_id,
                "insights_data": new_insights_json,
                "updated_at": datetime.utcnow()
            }
            
            # Check if insights exist first
            existing_insights = await self.get_stored_document_insights(document_id)
            if existing_insights:
                # Update existing
                insights_data["created_at"] = existing_insights.created_at
                import asyncio
                loop = asyncio.get_running_loop()
                insights_ref = self.firestore_client.collection("document_insights").document(document_id)
                await loop.run_in_executor(None, insights_ref.update, insights_data)
                logger.info("Successfully updated existing insights for document_id=%s", document_id)
            else:
                # Create new if doesn't exist
                insights_data["created_at"] = datetime.utcnow()
                import asyncio
                loop = asyncio.get_running_loop()
                insights_ref = self.firestore_client.collection("document_insights").document(document_id)
                await loop.run_in_executor(None, insights_ref.set, insights_data)
                logger.info("Successfully created new insights for document_id=%s", document_id)
            
            return DocumentInsightsResponse(**insights_data)
            
        except GoogleCloudError as e:
            logger.exception("Google Cloud error updating document insights")
            raise HTTPException(status_code=502, detail=f"Firestore error: {e}")
        except Exception as e:
            logger.exception("Unexpected error updating document insights")
            raise HTTPException(status_code=500, detail=f"Failed to update document insights: {e}")

    async def delete_document_insights(self, document_id: str) -> bool:
        """Delete document insights."""
        try:
            logger.info("Deleting insights for document_id=%s", document_id)
            
            import asyncio
            loop = asyncio.get_running_loop()
            insights_ref = self.firestore_client.collection("document_insights").document(document_id)
            await loop.run_in_executor(None, insights_ref.delete)
            
            logger.info("Successfully deleted insights for document_id=%s", document_id)
            return True
            
        except GoogleCloudError as e:
            logger.exception("Google Cloud error deleting document insights")
            raise HTTPException(status_code=502, detail=f"Firestore error: {e}")
        except Exception as e:
            logger.exception("Unexpected error deleting document insights")
            raise HTTPException(status_code=500, detail=f"Failed to delete document insights: {e}")


# Convenience function to get insights service instance
def get_insights_service() -> InsightsService:
    """Get an instance of the InsightsService."""
    return InsightsService()
