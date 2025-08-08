# app/database.py

import os
from urllib.parse import quote
from google.cloud import firestore, storage
from google.oauth2 import service_account
from app.config import settings

# Use the credentials path from settings
FIREBASE_CREDENTIALS_PATH = settings.FIREBASE_CREDENTIALS_PATH

if not FIREBASE_CREDENTIALS_PATH or not os.path.exists(FIREBASE_CREDENTIALS_PATH):
    raise RuntimeError(
        f"Google Cloud credentials not found at {FIREBASE_CREDENTIALS_PATH}. "
        "Set FIREBASE_CREDENTIALS_PATH environment variable or ensure service-account.json exists in the app directory."
    )

# Load credentials
credentials = service_account.Credentials.from_service_account_file(FIREBASE_CREDENTIALS_PATH)

# Firestore & Storage clients
firestore_client = firestore.Client(credentials=credentials, project=credentials.project_id)
storage_client = storage.Client(credentials=credentials, project=credentials.project_id)

def get_firestore_client():
    return firestore_client

def get_storage_client():
    return storage_client

def get_storage_bucket_public_url(filename):
    # URL encode the filename to handle spaces and special characters
    encoded_filename = quote(filename, safe='')
    return f"https://firebasestorage.googleapis.com/v0/b/{settings.FIREBASE_STORAGE_BUCKET}/o/{encoded_filename}?alt=media"
