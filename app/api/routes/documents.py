import os
from typing import List, Optional, Union
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, BackgroundTasks
from google.cloud import firestore, storage
import logging

from app.database import get_firestore_client, get_storage_client
from app.schemas.document import DocumentResponse, FolderItem, FileItem, AISummaryResponse, DocumentSummaryCreate, DocumentSummaryResponse
from app.services.document_service import DocumentService
from app.services.summarize_service import SummarizeService
from app.config import settings

logger = logging.getLogger("app.document_service")

router = APIRouter()

@router.post("/documents/create", response_model=DocumentResponse)
async def create_document(
    background_tasks: BackgroundTasks,
    meta_data: str = Form(...),
    file: UploadFile = File(...),
    firestore_client = Depends(get_firestore_client),
    storage_client = Depends(get_storage_client)
):
    """Upload new document.

    Expected multipart/form-data keys:
      - file (the uploaded file)
      - meta_data (JSON string containing optional current_folder_id)
    """

    logger.info("[documents] Starting upload for file '%s' (content_type=%s)", file.filename, file.content_type)
    
    service = DocumentService()
    document = await service.create_document(
        file=file, 
        meta_data=meta_data,
        background_tasks=background_tasks
    )
    return document

@router.get("/documents", response_model=List[Union[FolderItem, FileItem]])
async def get_documents(
    folder_id: Optional[str] = None,
    firestore_client = Depends(get_firestore_client),
    storage_client = Depends(get_storage_client)
):
    """Get hierarchical folder structure with documents.
    
    Args:
        folder_id: Optional folder ID to get specific folder structure
        
    Returns:
        FolderItem: Hierarchical folder structure with nested files and folders
    """
    logger.info("[documents] Getting folder structure for folder_id=%s", folder_id)
    
    service = DocumentService()
    items = await service.get_documents()
    return items


@router.get("/documents/{document_id}/summary", response_model=AISummaryResponse)
async def get_document_summary(
    document_id: str,
    firestore_client = Depends(get_firestore_client),
    storage_client = Depends(get_storage_client)
):
    """Get a summary of a specific document.

    Args:
        document_id: The ID of the document to retrieve

    Returns:
        DocumentResponse: The document summary
    """
    logger.info("[documents] Getting summary for document_id=%s", document_id)

    service = DocumentService()
    document = await service.get_document_summary(document_id=document_id)
    return document

