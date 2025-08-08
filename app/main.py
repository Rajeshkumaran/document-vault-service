from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import os
import logging

from app.api.routes import documents
from app.config import settings



LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
logging.basicConfig(
    level=LOG_LEVEL,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)

# Optional: reduce noisy third-party loggers (uncomment as needed)
# logging.getLogger("httpx").setLevel(logging.WARNING)
# logging.getLogger("asyncio").setLevel(logging.WARNING)

logger = logging.getLogger("app")

app = FastAPI(
    title="Document Vault Service",
    description="A document vault service",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure this properly for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(documents.router, prefix="/api/v1", tags=["documents"])

@app.get("/")
async def root():
    """Root endpoint"""
    logger.debug("Root endpoint called")
    return {
        "message": "Welcome to Document Vault Service",
        "version": "1.0.0",
        "docs": "/docs",
        "redoc": "/redoc",
        "database": "Supabase"
    }

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    logger.debug("Health check endpoint called")
    return {"status": "healthy", "service": "document-vault-service", "database": "supabase"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=7000, reload=True)
