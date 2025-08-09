from datetime import datetime
from typing import Optional, List, Union, Dict, Any
from pydantic import BaseModel, Field

class DocumentBase(BaseModel):
    filename: str

class DocumentCreate(DocumentBase):
    original_filename: str
    content_type: str
    file_size: int
    storage_path: Optional[str] = None


class DocumentResponse(DocumentBase):
    id: str  # Changed from int to str for Firestore document IDs
    original_filename: str
    content_type: str
    file_size: int
    storage_path: Optional[str] = None
    is_active: bool
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True

class AISummaryResponse(DocumentBase):
    id: str  # Changed from int to str for Firestore document IDs
    summary: Optional[str] = None

    class Config:
        from_attributes = True

class DocumentSummaryCreate(BaseModel):
    document_id: str
    summary_text: str

class DocumentSummaryResponse(BaseModel):
    document_id: str
    summary_text: str
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True

# Hierarchical folder/document structure schemas
class FileItem(BaseModel):
    id: str
    name: str
    created_at: datetime
    type: str = "file"
    file_type: str
    storage_path: Optional[str] = None

class FolderItem(BaseModel):
    id: str
    name: str
    created_at: datetime
    type: str = "folder"
    # Use default_factory to avoid mutable default list being shared across instances
    children: List[Union['FolderItem', 'FileItem']] = Field(default_factory=list)

# Enable forward references for recursive model
FolderItem.model_rebuild()

# Aliases for backward compatibility
Document = DocumentResponse
DocumentInDB = DocumentResponse
DocumentInDBBase = DocumentResponse
