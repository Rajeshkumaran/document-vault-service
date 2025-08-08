from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel

class Document(BaseModel):
    """Document model for Supabase"""
    id: Optional[int] = None
    filename: str
    original_filename: str
    content_type: str
    file_size: int
    file_path: str
    storage_path: Optional[str] = None  # Path in Supabase storage
    is_active: bool = True
    created_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True
