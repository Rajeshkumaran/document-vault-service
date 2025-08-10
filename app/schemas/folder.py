from typing import Optional
from pydantic import BaseModel, Field
from datetime import datetime

class FolderCreateRequest(BaseModel):
    folder_name: str = Field(..., min_length=1, max_length=255, description="Name of the folder to create")
    parent_folder_id: Optional[str] = Field(None, description="ID of the parent folder. If not provided, folder will be created at root level")

class FolderCreateResponse(BaseModel):
    id: str
    name: str
    parent_id: Optional[str]
    created_at: datetime
    message: str = "Folder created successfully"
