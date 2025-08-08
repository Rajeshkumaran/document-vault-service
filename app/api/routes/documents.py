import os
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from google.cloud import firestore, storage
import logging

from app.database import get_firestore_client, get_storage_client
from app.schemas.document import DocumentResponse
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
