from typing import List, Union
from fastapi.encoders import jsonable_encoder
import os
import uuid
import logging
from typing import List, Dict, Any
from datetime import datetime, timedelta
from fastapi import UploadFile, HTTPException
from app.database import get_firestore_client, get_storage_client, get_storage_bucket_public_url
from google.cloud.exceptions import GoogleCloudError
from datetime import datetime

from app.schemas.document import DocumentResponse, FolderItem, FileItem
from app.config import settings
from app.utils import process_filename_with_folder, extract_filename_parts
from app.utils.common import normalize_datetime

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
                "file_type": filename_parts.get("extension"),
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
    
    async def get_documents(self) -> List[Union['FolderItem', 'FileItem']]:
        """Return a flat list of FolderItem and FileItem objects representing
        the current document hierarchy. Each folder contains its children.
        """
        try:
            # Get all documents from Firestore
            docs_ref = self.firestore_client.collection("documents")
            
            # Get all active documents
            query = docs_ref.where("is_active", "==", True)     
            docs = query.stream()
            
            # If no documents found and no folder_id specified, return sample structure
            all_docs = list(docs)
            if not all_docs:
                return []
            
            # Group documents by folder_name to create folder structure
            folder_groups: Dict[str, List[Dict[str, Any]]] = {}
            documents_without_folder = []
            
            for doc in all_docs:
                doc_data = doc.to_dict()
                doc_data["id"] = doc.id
                
                # Group by folder_name if it exists
                folder_name = doc_data.get("folder_name")
                folder_id = doc_data.get("folder_id")
                
                if folder_name and folder_name.strip():
                    if folder_name not in folder_groups:
                        folder_groups[folder_id] = []
                    folder_groups[folder_id].append(doc_data)
                else:
                    documents_without_folder.append(doc_data)
            
            # Create the root folder structure
            items = []

            # Add folder items
            for folder_id, folder_docs in folder_groups.items():
                # Create folder item
                folder_item = FolderItem(
                    id=folder_id,
                    name=folder_docs[0].get("folder_name"),
                    created_at=normalize_datetime(folder_docs[0].get("created_at")),
                    children=[]
                )
                
                # Add files to folder
                for doc in folder_docs:
                    file_extension = doc.get("file_type", "").lower().replace(".", "")
                    file_item = FileItem(
                        id=doc["id"],
                        name=doc["original_filename"],
                        created_at=normalize_datetime(doc.get("created_at")),
                        file_type=file_extension
                    )
                    folder_item.children.append(file_item)
                
                items.append(folder_item)
            
            # Add files without folder directly to root
            for doc in documents_without_folder:
                file_extension = doc.get("file_type", "").lower().replace(".", "")
                file_item = FileItem(
                    id=doc["id"],
                    name=doc["original_filename"],
                    created_at=normalize_datetime(doc.get("created_at")),
                    file_type=file_extension
                )
                items.append(file_item)
            
            # Return actual Pydantic models; FastAPI will handle serialization
            return items
            
        except GoogleCloudError as e:
            logger.exception("Google Cloud error getting folder structure")
            raise HTTPException(status_code=502, detail=f"Firestore error: {e}")
        except Exception as e:
            logger.exception("Unexpected error getting folder structure")
            raise HTTPException(status_code=500, detail=f"Failed to get folder structure: {e}")

   