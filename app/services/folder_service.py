from typing import Optional
import uuid
import logging
import asyncio
from datetime import datetime
from fastapi import HTTPException
from app.database import get_firestore_client
from google.cloud.exceptions import GoogleCloudError

logger = logging.getLogger("app.folder_service")


class FolderService:
    def __init__(self):
        self.firestore_client = get_firestore_client()

    async def create_folder(self, folder_name: str, parent_folder_id: Optional[str] = None) -> str:
        """Create a new folder in Firestore and return its ID."""
        try:
            folder_id = str(uuid.uuid4())
            current_time = datetime.utcnow()
            
            folder_data = {
                "name": folder_name,
                "parent_id": parent_folder_id,
                "created_at": current_time,
                "is_active": True,
                "id": folder_id
            }
            
            logger.debug("Creating folder with data: %s", folder_data)
            folder_ref = self.firestore_client.collection("folders").document(folder_id)
            
            # Use asyncio to run the synchronous Firestore operation
            loop = asyncio.get_running_loop()
            await loop.run_in_executor(None, folder_ref.set, folder_data)
            
            logger.info("Created folder '%s' with ID: %s", folder_name, folder_id)
            return folder_id
            
        except GoogleCloudError as e:
            logger.exception("Google Cloud error creating folder")
            raise HTTPException(status_code=502, detail=f"Firestore error: {e}")
        except Exception as e:
            logger.exception("Unexpected error creating folder")
            raise HTTPException(status_code=500, detail=f"Failed to create folder: {e}")
