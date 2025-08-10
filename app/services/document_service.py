from typing import List, Union, Optional
from fastapi.encoders import jsonable_encoder
import os
import uuid
import logging
import asyncio
import json
from typing import List, Dict, Any
from datetime import datetime, timedelta
from fastapi import UploadFile, HTTPException, BackgroundTasks
from app.database import get_firestore_client, get_storage_client, get_storage_bucket_public_url
from google.cloud.exceptions import GoogleCloudError
from datetime import datetime

from app.schemas.document import AISummaryResponse, DocumentResponse, FolderItem, FileItem, AIInsightsResponse
from app.services.summarize_service import SummarizeService
from app.services.insights_service import InsightsService
from app.models.document import DocumentSummary
from app.services.summarize_service import SummarizeService
from app.services.folder_service import FolderService
from app.config import settings
from app.utils import process_filename_with_folder, extract_filename_parts
from app.utils.common import extract_blob_name, normalize_datetime, download_blob_text_with_parsing, clean_json_response

logger = logging.getLogger("app.document_service")

mock_summary = """
title: "Product Sync — AI-Powered Search (Aug 6, 2025)"
type: "meeting_summary"
authors: ["A. Patel (PM)", "R. Kumar (Eng)"]
date: "2025-08-06T10:30:00+05:30"
reading_time: "2 min"
tags: ["product", "search", "roadmap", "action-items"]
---

# Product Sync — AI-Powered Search (Aug 6, 2025)

**TL;DR**  
The team agreed to prioritize semantic ranking and reduce inference cost by batching embeddings. MVP scope includes semantic search + fuzzy fallback, A/B test with 10% traffic, and a rollout plan for Q4. Key blockers: dataset labelling and infra cost approval.

---

## Key Decisions
- **MVP scope:** Semantic ranking, fuzzy fallback, result re-ranking for top 50 results.
- **Traffic ramp:** Start A/B test at **10%** of traffic for 3 weeks, then scale to 50% if CTR improves ≥ 7%.
- **Cost control:** Use batched embeddings (monthly budget cap ₹120,000) and per-query cache TTL = 6 hours.

---

## Action Items
| Owner | Task | Due |
|---|---:|---:|
| R. Kumar (Eng) | Implement batched embedding pipeline + cache layer (Redis). | 2025-08-13 |
| S. Mehta (DS) | Create labelled relevance dataset (1,500 queries) and baseline eval. | 2025-08-20 |
| A. Patel (PM) | Prepare A/B experiment plan & success criteria. | 2025-08-10 |
| Ops | Estimate infra cost & request budget approval. | 2025-08-12 |

---

## Metrics to Watch
- **Primary:** Click-through rate (CTR) on top-5 results (target +7% vs control)
- **Secondary:** Query latency (P95 < 250 ms), cost per 1,000 queries
- **Safety:** Rate of unsafe or hallucinated answers (target < 0.5%)

---

## Risks & Mitigations
- **Risk:** Embedding model cost exceeds projection.  
  **Mitigation:** Use smaller model for low-value queries; cache aggressively.
- **Risk:** Labelled dataset biased by current user cohort.  
  **Mitigation:** Sample queries from multiple regions and verticals; run fairness checks.

---

## Full Notes
**Background:** Business requested improved discovery for long-tail products. Current keyword-based search returns low recall for synonyms and paraphrases.

**Proposal:** Integrate semantic embeddings at query time for ranking, keep existing lexical score as a safety fallback. Use a hybrid score: `score = α * semantic_score + (1-α) * lexical_score` where α = 0.7 for initial experiments.

**Implementation details discussed:**
- Batch embedding API calls every 2 seconds for queued queries, with opportunistic caching for repeated queries.
- Store document embeddings in vector DB (annoy/hnsw) with nightly reindexing for new products.
- Telemetry: add `search_experiment_bucket` and `relevance_signal` events.

**Open questions:**
1. Which vector DB in prod? (Weigh latency vs cost)
2. How to handle private product fields in embeddings?

---

## Example Highlight (AI-generated excerpt)
> *“After switching to semantic-first ranking, we observed a 9.3% increase in top-5 CTR during the internal pilot. Lexical fallback reduced irrelevant answers by 42%.”* — A. Patel

---

## Attachments
- `relevance_dataset_v1.csv` (1,500 rows)  
- A/B test plan — `ab_plan_semantic_search.md`

---

## Follow-ups
- Review infra budget proposal on **2025-08-12** (Ops meeting).
- DS and Eng to run initial offline eval and share results in the next sync (2025-08-13).

---

### Render hints (for apps)
- Use `reading_time` from frontmatter to show quick preview.  
- Display `Action Items` as a checklist with due-date badges.  
- Highlight `TL;DR`, `Key Decisions`, and `Metrics` on a compact card for dashboards.

---
"""

mock_summary_2 = """
# Summary – Sampoorn Suraksha Master Proposal Form

## Product Overview
- **Product Name:** SBI Life – Sampoorn Suraksha  
- **UIN:** 111N040V04  
- **Type:** Group non-linked, non-participating, pure risk premium life insurance  
- **Applicable For:** Non Employer – Employee Groups  

## General Instructions
1. All questions in the form must be answered.  
2. Tick (✔) wherever applicable.  
3. Any cancellation/alteration must be authenticated by authorised signatories.  
4. Insurance is a contract of utmost good faith — all material facts must be disclosed.  
5. Provide details if “Others” is selected in any field.

## Scheme Details
- **Nature:** Compulsory or Voluntary  
- **If Voluntary:** % of premium by policyholder and by member  
- **Entry Age Range:** [To be specified in the form]  

## Proposer Details
- **Proposed Policyholder Name:** [To be filled]  
- **Registered / Head Office Address & Pin Code:** [To be filled]  
- **Mailing Address:** [To be filled]  
- **Contact Details:**
  - Telephone No.  
  - Fax No.  
  - Email Address  
  [Link Text](https://example.com)

### Authorised Signatories
| Signatory | Name | Designation | Telephone | Fax | Email |
|-----------|------|-------------|-----------|-----|-------|
| 1         |      |             |           |     |       |
| 2         |      |             |           |     |       |
| 3         |      |             |           |     |       |

- **Minimum number of authorised signatures required:** [To be filled]  

## Organisation Details
- **Type of Business / Trade / Activity:** [To be filled]  
- **Source of Lead:** Direct / Broking / Corporate Agency / Others (Specify)  
- **Organisation Category** (for Lender-Borrower groups):  
  - RBI-regulated Scheduled Commercial Banks (incl. Co-op Banks)  
  - NBFC with RBI Certificate of Registration  
  - NHB-regulated Housing Finance Companies  
  - Small Finance Banks regulated by RBI  
  - Microfinance companies under Sec 8 of Companies Act 2013  
  - Others as approved by authority  

## PAN Requirement
- Provide PAN or submit Form 60 if annualised premium exceeds ₹50,000.  
[Link Text](https://example.com)
## Additional Notes
- Contact Information:  
  - **Toll-Free:** 1800 267 9090 (24×7)  
  - **Email:** info@sbilife.co.in  
  - **Website:** www.sbilife.co.in  
- **Registered Office:** ‘Natraj’, M.V. Road & Western Express Highway Junction, Andheri (E), Mumbai – 400069  
- **Disclaimer:** SBI Life Insurance Company Limited and SBI are separate legal entities.  
[Link Text](https://example.com)
"""
class DocumentService:
    def __init__(self):
        self.firestore_client = get_firestore_client()
        self.storage_client = get_storage_client()
        self.folder_service = FolderService()

   
    async def create_document(
        self,
        file: UploadFile,
        meta_data: str,
        background_tasks: Optional[BackgroundTasks] = None
    ) -> DocumentResponse:

        # Parse metadata
        try:
            metadata = json.loads(meta_data)
            current_folder_id = metadata.get("current_folder_id")
        except (json.JSONDecodeError, TypeError) as e:
            logger.error("Failed to parse meta_data: %s", str(e))
            raise HTTPException(status_code=400, detail="Invalid meta_data format. Must be valid JSON.")

        

        # Determine folder ID for the document
        if current_folder_id:
            logger.debug("Using existing folder '%s'", current_folder_id)
            # Use existing folder
            folder_id = current_folder_id
            folder_name = None
        else:
            # Fallback folder name
            folder_name = "Root"
            folder_id = await self.folder_service.create_folder("Root", current_folder_id)
            
        # 1. Process filename - remove folder name if folder_name is provided
        cleaned_filename, filename_metadata = process_filename_with_folder(
            original_filename=file.filename,
            folder_name=folder_name
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
           
            logger.debug("Generating signed URL for blob '%s'", filename)
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
            logger.info("Before uploading starts %s", folder_id)
            insert_payload = {
                "filename": filename,
                "original_filename": filename_metadata["original_filename"],  # Keep the original filename with folder
                "content_type": file.content_type,
                "file_size": file_size,
                "file_type": filename_parts.get("extension"),
                "storage_path": storage_url,
                "is_active": True,
                "created_at": current_time,
                "folder_id": folder_id
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

        # 6. Trigger background summary generation if background_tasks is provided
        if background_tasks:
            try:
                logger.info("Adding background task for summary generation of document_id=%s", record["id"])
                background_tasks.add_task(
                    self._generate_summary_background,
                    record["id"],
                    filename,  # The unique filename in storage
                    filename   # blob_name is same as filename in our case
                )
            except Exception as e:
                logger.warning("Failed to add background summary generation task: %s", str(e))
                # Don't fail the upload if background task scheduling fails

        # 7. Build response
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
        """Return a hierarchical list of FolderItem and FileItem objects representing
        the current document hierarchy. Folders with parent_id=null are at root level,
        folders with parent_id become children of their parent, and documents are
        associated with folders via folder_id.
        """
        try:
            # Get all folders from Firestore
            folders_ref = self.firestore_client.collection("folders")
            folders_query = folders_ref.where("is_active", "==", True)
            folders_docs = folders_query.stream()
            
            # Get all documents from Firestore
            docs_ref = self.firestore_client.collection("documents")
            docs_query = docs_ref.where("is_active", "==", True)
            docs = docs_query.stream()
            
            # Convert to lists and add IDs
            all_folders = []
            for folder_doc in folders_docs:
                folder_data = folder_doc.to_dict()
                folder_data["id"] = folder_doc.id
                all_folders.append(folder_data)
            
            all_docs = []
            for doc in docs:
                doc_data = doc.to_dict()
                doc_data["id"] = doc.id
                all_docs.append(doc_data)
            
            logger.info("Found %d active folders and %d active documents in Firestore", 
                       len(all_folders), len(all_docs))
            
            # If no folders and no documents found, return empty list
            if not all_folders and not all_docs:
                return []
            
            # Create folder lookup dictionary for easy access
            folders_dict = {folder["id"]: folder for folder in all_folders}
            
            # Group documents by folder_id
            documents_by_folder: Dict[str, List[Dict[str, Any]]] = {}
            documents_without_folder = []
            
            for doc in all_docs:
                folder_id = doc.get("folder_id")
                if folder_id and folder_id in folders_dict:
                    if folder_id not in documents_by_folder:
                        documents_by_folder[folder_id] = []
                    documents_by_folder[folder_id].append(doc)
                else:
                    documents_without_folder.append(doc)
            
            # Helper function to convert document to FileItem
            def create_file_item(doc: Dict[str, Any]) -> FileItem:
                file_extension = doc.get("file_type", "").lower().replace(".", "")
                return FileItem(
                    id=doc["id"],
                    name=doc["original_filename"],
                    created_at=normalize_datetime(doc.get("created_at")),
                    file_type=file_extension,
                    storage_path=doc["storage_path"]
                )
            
            # Helper function to build folder tree recursively
            def build_folder_item(folder_data: Dict[str, Any], processed_folders: set) -> FolderItem:
                folder_id = folder_data["id"]
                
                # Avoid infinite loops by checking if folder is already being processed
                if folder_id in processed_folders:
                    logger.warning("Circular reference detected for folder %s", folder_id)
                    return None
                
                processed_folders.add(folder_id)
                
                # Create folder item
                folder_item = FolderItem(
                    id=folder_id,
                    name=folder_data.get("name", "Unnamed Folder"),
                    created_at=normalize_datetime(folder_data.get("created_at")),
                    children=[]
                )
                
                # Add documents to this folder
                if folder_id in documents_by_folder:
                    for doc in documents_by_folder[folder_id]:
                        file_item = create_file_item(doc)
                        folder_item.children.append(file_item)
                
                # Add child folders to this folder
                child_folders = [f for f in all_folders if f.get("parent_id") == folder_id]
                for child_folder in child_folders:
                    child_folder_item = build_folder_item(child_folder, processed_folders.copy())
                    if child_folder_item:
                        folder_item.children.append(child_folder_item)
                
                return folder_item
            
            # Build the root level items
            items = []
            
            # Add root level folders (parent_id is null or not present)
            root_folders = [f for f in all_folders if f.get("parent_id") is None]
            for folder in root_folders:
                folder_item = build_folder_item(folder, set())
                if folder_item:
                    items.append(folder_item)
            
            # Add files without folder directly to root
            for doc in documents_without_folder:
                file_item = create_file_item(doc)
                items.append(file_item)
            
            # Return actual Pydantic models; FastAPI will handle serialization
            return items
            
        except GoogleCloudError as e:
            logger.exception("Google Cloud error getting folder structure")
            raise HTTPException(status_code=502, detail=f"Firestore error: {e}")
        except Exception as e:
            logger.exception("Unexpected error getting folder structure")
            raise HTTPException(status_code=500, detail=f"Failed to get folder structure: {e}")

    async def get_document_summary(self, document_id: str) -> AISummaryResponse:
        """Get document summary using the SummarizeService."""
        try:
            logger.info("Getting summary for document_id=%s", document_id)
            
            # Get document details
            doc_ref = self.firestore_client.collection("documents").document(document_id)
            import asyncio
            loop = asyncio.get_running_loop()
            doc = await loop.run_in_executor(None, doc_ref.get)
            if not doc.exists:
                raise HTTPException(status_code=404, detail="Document not found")
            
            doc_data = doc.to_dict()
            filename = doc_data.get("filename", "")
            storage_path = doc_data.get("storage_path")
            
            # Initialize summarize service
            summarize_service = SummarizeService()
            
            # Check for existing summary first
            stored_summary = await summarize_service.get_stored_document_summary(document_id)
            if stored_summary:
                logger.info("Found existing summary for document_id=%s", document_id)
                response_data = {
                    "id": document_id,
                    "filename": filename,
                    "summary": stored_summary.summary_text
                }
                return AISummaryResponse(**response_data)
            
            # No existing summary found, check if generation is in progress
            try:
                progress_ref = self.firestore_client.collection("document_summary_progress").document(document_id)
                progress_doc = await loop.run_in_executor(None, progress_ref.get)
                
                if progress_doc.exists:
                    progress_data = progress_doc.to_dict()
                    status = progress_data.get("status")
                    
                    if status == "generating":
                        logger.info("Summary generation in progress for document_id=%s", document_id)
                        response_data = {
                            "id": document_id,
                            "filename": filename,
                            "summary": "Summary is being generated in the background. Please check back in a few moments."
                        }
                        return AISummaryResponse(**response_data)
                    elif status == "failed":
                        error_msg = progress_data.get("error", "Unknown error")
                        logger.info("Background summary generation failed for document_id=%s: %s", document_id, error_msg)
                        # Clean up failed progress record
                        try:
                            await loop.run_in_executor(None, progress_ref.delete)
                        except Exception:
                            pass
            except Exception as e:
                logger.warning("Failed to check summary progress: %s", str(e))
            
            # No existing summary and no generation in progress, generate one synchronously as fallback
            logger.info("Generating summary synchronously for document_id=%s", document_id)
            
            # Get document content
            blob_name = None
            if storage_path:
                try:
                    blob_name = extract_blob_name(storage_path)
                except Exception:
                    logger.info("Could not parse blob name from storage path '%s'", storage_path)
                    blob_name = None
            
            # Download and summarize content
            file_text_content = download_blob_text_with_parsing(self.storage_client, blob_name) if blob_name else None
            
            if file_text_content:
                summary_text = await summarize_service.get_or_generate_summary(
                    document_id, file_text_content, filename
                )
            else:
                logger.warning("No file content available for summarization")
                summary_text = "Unable to generate summary: Document content could not be extracted."
            
            response_data = {
                "id": document_id,
                "filename": filename,
                "summary": summary_text
            }
            
            return AISummaryResponse(**response_data)

        except GoogleCloudError as e:
            logger.exception("Google Cloud error getting document summary")
            raise HTTPException(status_code=502, detail=f"Firestore error: {e}")
        except Exception as e:
            logger.exception("Unexpected error getting document summary")
            raise HTTPException(status_code=500, detail=f"Failed to get document summary: {e}")


    async def _generate_summary_background(self, document_id: str, filename: str, blob_name: str):
        """Background task to generate document summary after upload."""
        try:
            logger.info("Starting background summary generation for document_id=%s", document_id)
            
            # Store a flag indicating summary generation is in progress
            try:
                summary_progress_ref = self.firestore_client.collection("document_summary_progress").document(document_id)
                await asyncio.get_running_loop().run_in_executor(
                    None, 
                    summary_progress_ref.set, 
                    {
                        "document_id": document_id,
                        "status": "generating",
                        "started_at": datetime.utcnow()
                    }
                )
            except Exception as e:
                logger.warning("Failed to set summary progress flag: %s", str(e))
            
            # Download and parse document content
            file_text_content = download_blob_text_with_parsing(self.storage_client, blob_name)
            
            if not file_text_content:
                logger.warning("No text content extracted from document_id=%s, skipping summary generation", document_id)
                # Update progress status
                try:
                    summary_progress_ref = self.firestore_client.collection("document_summary_progress").document(document_id)
                    await asyncio.get_running_loop().run_in_executor(
                        None, 
                        summary_progress_ref.set, 
                        {
                            "document_id": document_id,
                            "status": "failed",
                            "error": "No text content extracted",
                            "completed_at": datetime.utcnow()
                        }
                    )
                except Exception:
                    pass
                return
            
            # Initialize summarize service and generate summary
            summarize_service = SummarizeService()
            summary_text = await summarize_service.generate_document_summary(file_text_content, filename)
            
            if summary_text:
                # Store the generated summary
                await summarize_service.store_document_summary(document_id, summary_text)
                logger.info("Successfully generated and stored summary for document_id=%s", document_id)
                
                # Update progress status to completed
                try:
                    summary_progress_ref = self.firestore_client.collection("document_summary_progress").document(document_id)
                    await asyncio.get_running_loop().run_in_executor(
                        None, 
                        summary_progress_ref.set, 
                        {
                            "document_id": document_id,
                            "status": "completed",
                            "completed_at": datetime.utcnow()
                        }
                    )
                except Exception as e:
                    logger.warning("Failed to update summary progress status: %s", str(e))
            else:
                logger.warning("Failed to generate summary for document_id=%s", document_id)
                # Update progress status to failed
                try:
                    summary_progress_ref = self.firestore_client.collection("document_summary_progress").document(document_id)
                    await asyncio.get_running_loop().run_in_executor(
                        None, 
                        summary_progress_ref.set, 
                        {
                            "document_id": document_id,
                            "status": "failed",
                            "error": "Summary generation failed",
                            "completed_at": datetime.utcnow()
                        }
                    )
                except Exception:
                    pass
                
        except Exception as e:
            logger.exception("Error in background summary generation for document_id=%s: %s", document_id, str(e))
            # Update progress status to failed
            try:
                summary_progress_ref = self.firestore_client.collection("document_summary_progress").document(document_id)
                await asyncio.get_running_loop().run_in_executor(
                    None, 
                    summary_progress_ref.set, 
                    {
                        "document_id": document_id,
                        "status": "failed",
                        "error": str(e),
                        "completed_at": datetime.utcnow()
                    }
                )
            except Exception:
                pass
            # Don't raise exceptions in background tasks as they won't be handled by the caller

    async def get_document_insights(self, document_id: str) -> AIInsightsResponse:
        """Get document insights using the SummarizeService and LLM insights extraction."""
        try:
            import json
            logger.info("Getting insights for document_id=%s", document_id)
            
            # Get document details
            doc_ref = self.firestore_client.collection("documents").document(document_id)
            import asyncio
            loop = asyncio.get_running_loop()
            doc = await loop.run_in_executor(None, doc_ref.get)
            if not doc.exists:
                raise HTTPException(status_code=404, detail="Document not found")
            
            doc_data = doc.to_dict()
            filename = doc_data.get("filename", "")
            
            # Initialize insights service
            insights_service = InsightsService()
            
            # First get the document summary (required for insights generation)
            summary_response = await self.get_document_summary(document_id)
            summary_text = summary_response.summary
            
            if not summary_text or summary_text.strip() == "":
                logger.warning("No summary available for insights generation")
                fallback_insights = {
                    "document_type": "unknown",
                    "key_insights": {
                        "financial_data": {"amounts": [], "dates": []},
                        "coverage_details": [],
                        "critical_information": ["No summary available for insights generation"]
                    },
                    "confidence_score": 0.0
                }
                response_data = {
                    "id": document_id,
                    "filename": filename,
                    "insights": fallback_insights
                }
                return AIInsightsResponse(**response_data)
            
            # Get or generate insights from the summary
            insights_json = await insights_service.get_or_generate_insights(
                document_id, summary_text, filename
            )

            
            # Parse the insights JSON
            try:
                if insights_json is None:
                    logger.warning("insights_json is None")
                    insights_dict = {}
                elif isinstance(insights_json, str):
                    logger.info("Parsing insights_json as string, length: %d", len(insights_json))
                    
                    # Clean the JSON response using the common utility
                    cleaned_json = clean_json_response(insights_json)
                    logger.info("Cleaned JSON length: %d", len(cleaned_json))
                    
                    insights_dict = json.loads(cleaned_json)
                elif isinstance(insights_json, dict):
                    logger.info("insights_json is already a dict")
                    insights_dict = insights_json
                else:
                    logger.warning("Unexpected insights_json type: %s", type(insights_json))
                    insights_dict = {}
            except json.JSONDecodeError as e:
                logger.error("Failed to parse insights JSON: %s", str(e))
                logger.error("Raw insights_json content: %s", repr(insights_json))
                insights_dict = {
                    "document_type": "unknown",
                    "key_insights": {
                        "financial_data": {"amounts": [], "dates": []},
                        "coverage_details": [],
                        "critical_information": ["Failed to parse insights data"]
                    },
                    "confidence_score": 0.0
                }
            except Exception as e:
                logger.error("Unexpected error parsing insights JSON: %s", str(e))
                logger.error("Raw insights_json content: %s", repr(insights_json))
                insights_dict = {
                    "document_type": "unknown",
                    "key_insights": {
                        "financial_data": {"amounts": [], "dates": []},
                        "coverage_details": [],
                        "critical_information": ["Unexpected error parsing insights data"]
                    },
                    "confidence_score": 0.0
                }
            
            # Validate and ensure proper structure of insights_dict
            if not isinstance(insights_dict, dict):
                logger.warning("insights_dict is not a dictionary, converting to default structure")
                insights_dict = {
                    "document_type": "unknown",
                    "key_insights": {
                        "financial_data": {"amounts": [], "dates": []},
                        "coverage_details": [],
                        "critical_information": ["Invalid insights data structure"]
                    },
                    "confidence_score": 0.0
                }
            else:
                # Ensure required keys exist
                if "document_type" not in insights_dict:
                    insights_dict["document_type"] = "unknown"
                
                if "key_insights" not in insights_dict:
                    insights_dict["key_insights"] = {
                        "financial_data": {"amounts": [], "dates": []},
                        "coverage_details": [],
                        "critical_information": []
                    }
                elif not isinstance(insights_dict["key_insights"], dict):
                    insights_dict["key_insights"] = {
                        "financial_data": {"amounts": [], "dates": []},
                        "coverage_details": [],
                        "critical_information": []
                    }
                else:
                    # Ensure sub-keys exist in key_insights
                    key_insights = insights_dict["key_insights"]
                    if "financial_data" not in key_insights:
                        key_insights["financial_data"] = {"amounts": [], "dates": []}
                    elif not isinstance(key_insights["financial_data"], dict):
                        key_insights["financial_data"] = {"amounts": [], "dates": []}
                    else:
                        # Validate financial_data structure
                        fin_data = key_insights["financial_data"]
                        if "amounts" not in fin_data or not isinstance(fin_data["amounts"], list):
                            fin_data["amounts"] = []
                        if "dates" not in fin_data or not isinstance(fin_data["dates"], list):
                            fin_data["dates"] = []
                    
                    if "coverage_details" not in key_insights:
                        key_insights["coverage_details"] = []
                    elif not isinstance(key_insights["coverage_details"], list):
                        key_insights["coverage_details"] = []
                    
                    if "critical_information" not in key_insights:
                        key_insights["critical_information"] = []
                    elif not isinstance(key_insights["critical_information"], list):
                        key_insights["critical_information"] = []
                
                if "confidence_score" not in insights_dict:
                    insights_dict["confidence_score"] = 0.0
                elif not isinstance(insights_dict["confidence_score"], (int, float)):
                    insights_dict["confidence_score"] = 0.0
            
            logger.info("Final insights_dict structure validated successfully")
            
            # Create DocumentInsights object from the validated dictionary
            try:
                from app.schemas.document import DocumentInsights
                insights_obj = DocumentInsights(**insights_dict)
            except Exception as e:
                logger.error("Failed to create DocumentInsights object: %s", str(e))
                logger.error("insights_dict content: %s", insights_dict)
                # Create a minimal valid insights object as fallback
                insights_obj = DocumentInsights(
                    document_type="unknown",
                    key_insights={
                        "financial_data": {"amounts": [], "dates": []},
                        "coverage_details": [],
                        "critical_information": ["Failed to parse insights structure"]
                    },
                    confidence_score=0.0
                )
            
            response_data = {
                "id": document_id,
                "filename": filename,
                "insights": insights_obj
            }
            
            return AIInsightsResponse(**response_data)

        except GoogleCloudError as e:
            logger.exception("Google Cloud error getting document insights")
            raise HTTPException(status_code=502, detail=f"Firestore error: {e}")
        except Exception as e:
            logger.exception("Unexpected error getting document insights")
            raise HTTPException(status_code=500, detail=f"Failed to get document insights: {e}")
