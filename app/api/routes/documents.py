import os
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
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


@router.post("/documents/{document_id}/summary", response_model=DocumentSummaryResponse)
async def create_document_summary(
    document_id: str,
    summary_data: DocumentSummaryCreate,
    firestore_client = Depends(get_firestore_client)
):
    """Store a summary for a specific document.

    Args:
        document_id: The ID of the document
        summary_data: The summary data to store

    Returns:
        DocumentSummaryResponse: The stored summary
    """
    logger.info("[documents] Storing summary for document_id=%s", document_id)

    service = SummarizeService()
    summary = await service.store_document_summary(document_id=document_id, summary_text=summary_data.summary_text)
    return summary


@router.get("/documents/{document_id}/summary/stored", response_model=DocumentSummaryResponse)
async def get_stored_document_summary(
    document_id: str,
    firestore_client = Depends(get_firestore_client)
):
    """Get the stored summary for a specific document (without generating if missing).

    Args:
        document_id: The ID of the document

    Returns:
        DocumentSummaryResponse: The stored summary
    """
    logger.info("[documents] Getting stored summary for document_id=%s", document_id)

    service = SummarizeService()
    summary = await service.get_stored_document_summary(document_id)
    if not summary:
        raise HTTPException(status_code=404, detail="No stored summary found for this document")
    return summary


@router.put("/documents/{document_id}/summary", response_model=DocumentSummaryResponse)
async def update_document_summary(
    document_id: str,
    summary_data: DocumentSummaryCreate,
    firestore_client = Depends(get_firestore_client)
):
    """Update the summary for a specific document.

    Args:
        document_id: The ID of the document
        summary_data: The updated summary data

    Returns:
        DocumentSummaryResponse: The updated summary
    """
    logger.info("[documents] Updating summary for document_id=%s", document_id)

    service = SummarizeService()
    summary = await service.update_document_summary(document_id=document_id, new_summary_text=summary_data.summary_text)
    return summary


@router.delete("/documents/{document_id}/summary")
async def delete_document_summary(
    document_id: str,
    firestore_client = Depends(get_firestore_client)
):
    """Delete the summary for a specific document.

    Args:
        document_id: The ID of the document

    Returns:
        dict: Success message
    """
    logger.info("[documents] Deleting summary for document_id=%s", document_id)

    service = SummarizeService()
    success = await service.delete_document_summary(document_id)
    if success:
        return {"message": "Summary deleted successfully"}
    else:
        raise HTTPException(status_code=500, detail="Failed to delete summary")