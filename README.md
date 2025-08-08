# Document Vault Service

A FastAPI-based document management service powered by Supabase.

## Features

- Document upload and storage
- Document retrieval and management
- RESTful API endpoints
- Supabase database integration
- Supabase Storage for file storage
- File validation and processing
- Dual storage (local backup + Supabase Storage)

## Prerequisites

1. **Supabase Project**: Create a new project at [supabase.com](https://supabase.com)
2. **Python 3.8+**: Make sure you have Python installed

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

### 3. Set up Supabase:

1. Go to your Supabase project dashboard
2. Get your project URL and anon key from **Settings > API**
3. Run the SQL script from `supabase_setup.sql` in your Supabase SQL editor
4. Create a storage bucket named "documents" in **Storage**

### 4. Set up environment variables:
```bash
cp .env.example .env
# Edit .env with your Supabase configuration
```

Your `.env` should look like:
```env
SUPABASE_URL=https://your-project-id.supabase.co
SUPABASE_ANON_KEY=your-anon-key-here
SUPABASE_SERVICE_KEY=your-service-key-here
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

The application uses a single `documents` table in Supabase with the following structure:

```sql
CREATE TABLE documents (
    id BIGSERIAL PRIMARY KEY,
    filename VARCHAR(255) NOT NULL,
    original_filename VARCHAR(255) NOT NULL,
    content_type VARCHAR(100) NOT NULL,
    file_size INTEGER NOT NULL,
    file_path VARCHAR(500) NOT NULL,
    storage_path VARCHAR(500),
    description TEXT,
    tags JSONB,
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now(),
    updated_at TIMESTAMP WITH TIME ZONE
);
```

## Storage

The application uses a hybrid storage approach:
- **Supabase Storage**: Primary storage for files
- **Local Storage**: Backup storage in the `uploads/` folder

## Project Structure

```
document-vault-service/
├── app/
│   ├── __init__.py
│   ├── main.py                 # FastAPI application
│   ├── config.py              # Configuration settings
│   ├── database.py            # Supabase client setup
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
│   │   └── document_service.py # Business logic
│   └── utils/
│       ├── __init__.py
│       └── security.py
├── tests/
│   ├── __init__.py
│   └── test_documents.py
├── uploads/                   # Local file storage
├── requirements.txt
├── supabase_setup.sql         # Database setup script
├── .env.example
├── .env
├── .gitignore
└── README.md
```

## Testing

Run tests with:
```bash
pytest
```

## API Endpoints

- `POST /api/v1/documents/` - Upload a document
- `GET /api/v1/documents/` - List all documents
- `GET /api/v1/documents/{id}` - Get a specific document
- `PUT /api/v1/documents/{id}` - Update document metadata
- `DELETE /api/v1/documents/{id}` - Delete a document (soft delete)
- `GET /api/v1/documents/{id}/download` - Download a document

## Security Notes

### Environment Files
- **`.env.example`**: Template file with placeholder values - **SAFE to commit to git**
- **`.env`**: Your actual file with real credentials - **NEVER commit to git** (excluded in .gitignore)

Always use placeholder/dummy values in `.env.example` and real secrets only in `.env`.

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `SUPABASE_URL` | Your Supabase project URL | Required |
| `SUPABASE_ANON_KEY` | Supabase anonymous key | Required |
| `SUPABASE_SERVICE_KEY` | Supabase service key (optional) | "" |
| `SECRET_KEY` | JWT secret key | "your-super-secret-key..." |
| `MAX_FILE_SIZE_MB` | Maximum file size in MB | 10 |
| `SUPABASE_STORAGE_BUCKET` | Supabase storage bucket name | "documents" |
