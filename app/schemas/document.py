from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel

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

# Aliases for backward compatibility
Document = DocumentResponse
DocumentInDB = DocumentResponse
DocumentInDBBase = DocumentResponse
