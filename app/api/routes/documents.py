import os
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from google.cloud import firestore, storage
import logging

from app.database import get_firestore_client, get_storage_client
from app.schemas.document import DocumentResponse, FolderItem, FileItem
from app.services.document_service import DocumentService
from app.config import settings

logger = logging.getLogger("app.document_service")

router = APIRouter()

@router.post("/documents/create", response_model=DocumentResponse)
async def create_document(
    folderName: str = Form(""),
    folderId: str = Form(""),
    file: UploadFile = File(...),
    firestore_client = Depends(get_firestore_client),
    storage_client = Depends(get_storage_client)
):
    """Upload new document.

    Expected multipart/form-data keys:
      - file (the uploaded file)
    """

    logger.info("[documents] Starting upload for file '%s' (content_type=%s, folderName=%s)", file.filename, file.content_type, folderName)
    
    service = DocumentService()
    document = await service.create_document(file=file, folderName=folderName, folderId=folderId)
    return document

@router.get("/documents", response_model=list[FolderItem | FileItem])
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
