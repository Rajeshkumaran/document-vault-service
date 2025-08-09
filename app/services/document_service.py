from typing import List, Union, Optional
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

from app.schemas.document import AISummaryResponse, DocumentResponse, FolderItem, FileItem
from app.models.document import DocumentSummary
from app.services.summarize_service import SummarizeService
from app.config import settings
from app.utils import process_filename_with_folder, extract_filename_parts
from app.utils.common import extract_blob_name, normalize_datetime, download_blob_text_with_parsing

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

    async def create_document(
        self,
        file: UploadFile,
        folderName: str,
        folderId: str
    ) -> DocumentResponse:

        logger.info("Starting upload for file '%s' (content_type=%s, folderName=%s, folderId=%s)", file.filename, file.content_type, folderName, folderId)

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
            logger.debug("Uploading to Firebase Storage bucket '%s' path '%s'", settings.FIREBASE_STORAGE_BUCKET, filename, folderId)
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
            
            logger.info("Found %d active documents in Firestore", len(all_docs))
            # Group documents by folder_name to create folder structure
            folder_groups: Dict[str, List[Dict[str, Any]]] = {}
            documents_without_folder = []
            
            for doc in all_docs:
                doc_data = doc.to_dict()
                doc_data["id"] = doc.id
                # Group by folder_id if it exists
                folder_id = doc_data.get("folder_id")

                if folder_id:
                    if folder_id not in folder_groups:
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
                        file_type=file_extension,
                        storage_path=doc["storage_path"]
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
                    file_type=file_extension,
                    storage_path=doc["storage_path"]
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
            
            # No existing summary, generate one
            logger.info("No existing summary, generating new one for document_id=%s", document_id)
            
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
                summary_text = ""
            
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
