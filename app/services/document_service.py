import os
import uuid
import logging
from typing import List
from datetime import datetime, timedelta
from fastapi import UploadFile, HTTPException
from app.database import get_firestore_client, get_storage_client, get_storage_bucket_public_url
from google.cloud.exceptions import GoogleCloudError
from datetime import datetime

from app.schemas.document import DocumentResponse
from app.config import settings
from app.utils import process_filename_with_folder, extract_filename_parts

logger = logging.getLogger("app.document_service")

class DocumentService:
    def __init__(self):
        self.firestore_client = get_firestore_client()
        self.storage_client = get_storage_client()

    async def create_document(
        self,
        file: UploadFile,
        folderName: str,
        folderId: str
    ) -> DocumentResponse:
        
        logger.info("Starting upload for file '%s' (content_type=%s, folderName=%s)", file.filename, file.content_type, folderName)

        # 1. Process filename - remove folder name if folderName is provided
        cleaned_filename, filename_metadata = process_filename_with_folder(
            original_filename=file.filename,
            folder_name=folderName
        )
        
        
        # 2. Generate unique filename
        filename_parts = extract_filename_parts(cleaned_filename)
        filename = f"{filename_parts['name_without_extension']}_{uuid.uuid4().hex}{filename_parts['extension']}"
        logger.info("Generated unique filename '%s' from cleaned name '%s'", filename, cleaned_filename)

        # 3. Read file content
        content = await file.read()
        file_size = len(content)
        logger.debug("Read file bytes size=%d", file_size)

        # 4. Upload to Firebase Storage
        try:
            logger.debug("Uploading to Firebase Storage bucket '%s' path '%s'", settings.FIREBASE_STORAGE_BUCKET, filename)
            bucket = self.storage_client.bucket(settings.FIREBASE_STORAGE_BUCKET)
            blob = bucket.blob(filename)
            
            # Upload with metadata
            blob.upload_from_string(
                content,
                content_type=file.content_type
            )
            
        except GoogleCloudError as e:
            logger.exception("Google Cloud error during storage upload")
            raise HTTPException(status_code=502, detail=f"Cloud Storage error: {e}")
        except Exception as e:
            logger.exception("Unexpected exception during storage upload")
            raise HTTPException(status_code=500, detail=f"Storage upload failed: {e}")
        finally:
            # Reset file pointer (not strictly needed, but safe if reused)
            try:
                file.file.seek(0)
            except Exception:
                pass

        # Generate public URL or signed URL
        try:
           
            logger.info("Generating signed URL for blob '%s'", filename)
            signed_url = blob.generate_signed_url(
                    version="v4",
                    expiration=datetime.utcnow() + timedelta(days=7),
                    method="GET"
                )
            storage_url = signed_url
            logger.info("Generated signed URL for blob '%s'", signed_url)
 
        except Exception as e:
            logger.warning("Could not generate URL, using fallback: %s", e)
            storage_url = get_storage_bucket_public_url(filename)
            
        # 5. Insert metadata to Firestore
        try:
            doc_id = str(uuid.uuid4())  # Generate document ID
            current_time = datetime.utcnow()
            
            insert_payload = {
                "filename": filename,
                "original_filename": filename_metadata["original_filename"],  # Keep the original filename with folder
                "content_type": file.content_type,
                "file_size": file_size,
                "storage_path": storage_url,
                "is_active": True,
                "created_at": current_time,
                
                "folder_name": filename_metadata["folder_name"],  # Store folder name separately
                "folder_id": folderId
            }
            
            logger.debug("Inserting metadata to Firestore: %s", insert_payload)
            doc_ref = self.firestore_client.collection("documents").document(doc_id)
            doc_ref.set(insert_payload)
            
            # Fetch the created document to get the full record
            doc_snapshot = doc_ref.get()
            if not doc_snapshot.exists:
                logger.error("Document was not created in Firestore")
                raise HTTPException(status_code=500, detail="Failed to persist document metadata")
                
            record = doc_snapshot.to_dict()
            record["id"] = doc_snapshot.id  # Add the document ID
            logger.debug("Inserted Firestore document id=%s", doc_snapshot.id)
            
        except GoogleCloudError as e:
            logger.exception("Google Cloud error inserting metadata (cleaning up storage file)")
            try:
                bucket = self.storage_client.bucket(settings.FIREBASE_STORAGE_BUCKET)
                blob = bucket.blob(filename)
                blob.delete()
            except Exception:
                pass
            raise HTTPException(status_code=502, detail=f"Firestore error: {e}")
        except Exception as e:
            logger.exception("Unexpected error inserting metadata (cleaning up storage file)")
            try:
                bucket = self.storage_client.bucket(settings.FIREBASE_STORAGE_BUCKET)
                blob = bucket.blob(filename)
                blob.delete()
            except Exception:
                pass
            raise HTTPException(status_code=500, detail=f"Failed to save document metadata: {e}")

        # 6. Build response
        return DocumentResponse(
            id=record["id"],
            filename=record["filename"],
            original_filename=record["original_filename"],
            content_type=record["content_type"],
            file_size=record["file_size"],
            storage_path=record["storage_path"],
            is_active=record["is_active"],
            created_at=record["created_at"],
        )
    
    async def create_documents(
        self,
        files: List[UploadFile],
        folderName: str = None
    ) -> List[DocumentResponse]:
        """Create multiple documents sequentially.

        Currently processes files one-by-one; if one fails the previous ones remain.
        Caller can implement compensation if needed.
        
        Args:
            files: List of uploaded files
            folderName: Optional folder name to remove from filenames
        """
        if not files:
            raise HTTPException(status_code=400, detail="No files provided")
        results: List[DocumentResponse] = []
        logger.info("Starting batch upload count=%d, folderName=%s", len(files), folderName)
        for f in files:
            logger.debug("Processing batch file '%s'", f.filename)
            doc = await self.create_document(file=f, folderName=folderName)
            results.append(doc)
        logger.info("Completed batch upload count=%d", len(results))
        return results
      