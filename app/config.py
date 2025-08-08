import os
from typing import List
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    # Firebase settings
    FIREBASE_PROJECT_ID: str = os.environ.get("FIREBASE_PROJECT_ID", "")
    FIREBASE_STORAGE_BUCKET: str = os.environ.get("FIREBASE_STORAGE_BUCKET", "")
    FIREBASE_CREDENTIALS_PATH: str = os.environ.get("FIREBASE_CREDENTIALS_PATH", 
                                                   os.path.join(os.path.dirname(__file__), "service-account.json"))

    # File upload settings
    MAX_FILE_SIZE_MB: int = 10
    ALLOWED_EXTENSIONS: str = ".pdf,.docx"
    
  
    @property
    def allowed_extensions_list(self) -> List[str]:
        """Convert the comma-separated string to a list"""
        return [ext.strip() for ext in self.ALLOWED_EXTENSIONS.split(",")]
    
    class Config:
        env_file = ".env"
        extra = "ignore"  # Ignore extra fields from old Supabase config

settings = Settings()
