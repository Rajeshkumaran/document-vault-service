# Document Vault Service

A FastAPI-based document management service powered by Firebase/Google Cloud with AI-powered summarization.

## Features

- Document upload and storage with hierarchical folder structure
- AI-powered document summarization using Claude (Anthropic)
- Document retrieval and management
- RESTful API endpoints
- Firebase & Firestore database integration
- PDF text extraction and processing
- File validation and processing
- Background task processing for document summarization

## Prerequisites

1. **Firebase Project**: Create a new project at [firebase.google.com](https://firebase.google.com)
   - Enable Firestore Database
   - Enable Cloud Storage
   - Create a service account and download the JSON credentials
2. **Python 3.8+**: Make sure you have Python installed
3. **Anthropic API Key**: Optional, for AI-powered document summarization

## Setup

### 1. Create a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On macOS/Linux
# or
venv\Scripts\activate  # On Windows
```

### 2. Install dependencies:
```bash
pip install -r requirements.txt
```

### 3. Set up Firebase

1. Go to your Firebase project console
2. Enable Firestore Database in Native mode
3. Enable Cloud Storage and create a bucket
4. Go to **Project settings > Service accounts**
5. Generate a new private key and download the JSON file
6. Place the service account JSON file in the `app/` directory as `service-account.json`

### 4. Set up environment variables

```bash
cp .env.example .env
# Edit .env with your Firebase configuration
```

Your `.env` should look like:

```env
FIREBASE_PROJECT_ID=your-project-id
FIREBASE_STORAGE_BUCKET=your-project-id.appspot.com
FIREBASE_CREDENTIALS_PATH=app/service-account.json
ANTHROPIC_API_KEY=your-anthropic-api-key-here
MAX_FILE_SIZE_MB=10
ALLOWED_EXTENSIONS=.pdf,.docx
```

### 5. Start the development server:
```bash
uvicorn app.main:app --reload
```

## API Documentation

Once the server is running, visit:
- Swagger UI: <http://localhost:7000/docs>
- ReDoc: <http://localhost:7000/redoc>

## Database Schema

The application uses Firebase Firestore with the following collections:

### Documents Collection

```javascript
{
  id: "auto-generated-doc-id",
  filename: "unique-filename.pdf",
  original_filename: "original-name.pdf", 
  content_type: "application/pdf",
  file_size: 1024000,
  storage_path: "documents/unique-filename.pdf",
  is_active: true,
  created_at: "2024-01-01T00:00:00Z",
  updated_at: "2024-01-01T00:00:00Z",
  folder_id: "optional-folder-id",
  folder_name: "optional-folder-name"
}
```

### Document Summaries Collection

```javascript
{
  document_id: "document-id-reference",
  summary_text: "AI-generated summary text...",
  created_at: "2024-01-01T00:00:00Z", 
  updated_at: "2024-01-01T00:00:00Z"
}
```

## Storage

The application uses a hybrid storage approach:

- **Firestore Storage**: Primary storage for files

## AI-Powered Features

The service includes intelligent document processing:

- **Document Summarization**: Uses Anthropic Claude to generate concise, structured summaries
- **PDF Text Extraction**: Automatic text extraction from PDF documents  
- **Background Processing**: Asynchronous summarization without blocking uploads

## Project Structure

```text
document-vault-service/
├── app/
│   ├── __init__.py
│   ├── main.py                 # FastAPI application
│   ├── config.py              # Configuration settings
│   ├── database.py            # Firebase client setup
│   ├── service-account.json   # Firebase credentials (not in git)
│   ├── models/
│   │   ├── __init__.py
│   │   └── document.py        # Pydantic models
│   ├── schemas/
│   │   ├── __init__.py
│   │   └── document.py        # API schemas
│   ├── api/
│   │   ├── __init__.py
│   │   ├── deps.py            # Dependencies
│   │   └── routes/
│   │       ├── __init__.py
│   │       └── documents.py   # Document routes
│   ├── services/
│   │   ├── __init__.py
│   │   ├── document_service.py # Business logic
│   │   ├── llm_service.py     # AI/Claude integration
│   │   └── summarize_service.py # Document summarization
│   └── utils/
│       ├── __init__.py
│       ├── common.py
│       └── filename_utils.py
├── tests/
│   ├── __init__.py
│   ├── test_documents.py
│   └── test_document_summary.py
├── uploads/                   # Local file storage
├── requirements.txt
├── .env.example
├── .env                       # Your environment variables (not in git)
├── .gitignore
└── README.md
```

## Testing

Run tests with:
```bash
pytest
```

## API Endpoints

The service provides the following REST API endpoints:

- `POST /api/v1/documents/create` - Upload a document with optional folder organization
  - Accepts multipart/form-data with file, folderName, and folderId
  - Returns document metadata and triggers background summarization
  
- `GET /api/v1/documents/` - List all documents in hierarchical folder structure
  - Optional folder_id parameter to get specific folder contents
  - Returns nested folder and file structure
  
- `GET /api/v1/documents/{document_id}/summary` - Get AI-generated summary for a document
  - Returns document summary with metadata
  - Uses cached summary or generates new one via Claude API

## Models and Schemas

### Core Models

- **Document**: Base document model with file metadata
- **DocumentSummary**: AI-generated summary model with text content
- **DocumentResponse**: API response model for document operations
- **AISummaryResponse**: API response model for summary operations  
- **FolderItem**: Hierarchical folder structure model
- **FileItem**: Individual file item in folder hierarchy

### Schema Features

- **Hierarchical Structure**: Support for nested folders and files
- **Type Safety**: Full Pydantic validation and serialization
- **Backward Compatibility**: Maintained aliases for legacy endpoints
- **Recursive Models**: Self-referencing folder structures


The test suite includes:

- **Document Operations**: Upload, retrieval, and storage tests
- **AI Summarization**: LLM integration and fallback testing
- **Background Tasks**: Asynchronous processing validation

## Security Notes

### Environment Files

- **`.env.example`**: Template file with placeholder values - **SAFE to commit to git**
- **`.env`**: Your actual file with real credentials - **NEVER commit to git** (excluded in .gitignore)

Always use placeholder/dummy values in `.env.example` and real secrets only in `.env`.

## Environment Variables

| Variable | Description | Default | Required |
|----------|-------------|---------|----------|
| `FIREBASE_PROJECT_ID` | Your Firebase project ID | "" | Yes |
| `FIREBASE_STORAGE_BUCKET` | Firebase storage bucket name | "" | Yes |
| `FIREBASE_CREDENTIALS_PATH` | Path to service account JSON | `app/service-account.json` | Yes |
| `ANTHROPIC_API_KEY` | Anthropic Claude API key for summarization | "" | No |
| `MAX_FILE_SIZE_MB` | Maximum file size in MB | 10 | No |
| `ALLOWED_EXTENSIONS` | Comma-separated file extensions | ".pdf,.docx" | No |
