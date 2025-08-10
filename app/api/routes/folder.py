import asyncio
import logging
from fastapi import APIRouter, Depends, HTTPException

from app.database import get_firestore_client
from app.schemas.folder import FolderCreateRequest, FolderCreateResponse
from app.services.folder_service import FolderService

logger = logging.getLogger("app.folder_service")

router = APIRouter()

@router.post("/folders/create", response_model=FolderCreateResponse)
async def create_folder(
    folder_request: FolderCreateRequest,
    firestore_client = Depends(get_firestore_client)
):
    """Create a new folder.
    
    Args:
        folder_request: Request containing folder name and optional parent folder ID
        
    Returns:
        FolderCreateResponse: Created folder details
    """
    logger.info("[folders] Creating folder '%s' with parent_id=%s", 
                folder_request.folder_name, folder_request.parent_folder_id)
    
    folder_service = FolderService()
    folder_id = await folder_service.create_folder(
        folder_name=folder_request.folder_name,
        parent_folder_id=folder_request.parent_folder_id
    )
    
    # Get the created folder data to return complete response
    loop = asyncio.get_running_loop()
    folder_ref = firestore_client.collection("folders").document(folder_id)
    folder_doc = await loop.run_in_executor(None, folder_ref.get)
    
    if not folder_doc.exists:
        logger.error("[folders] Created folder not found in database")
        raise HTTPException(status_code=500, detail="Failed to retrieve created folder")
    
    folder_data = folder_doc.to_dict()
    
    return FolderCreateResponse(
        id=folder_id,
        name=folder_data["name"],
        parent_id=folder_data.get("parent_id"),
        created_at=folder_data["created_at"]
    )
