from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
from contextlib import asynccontextmanager
import os

# Load environment variables at startup
load_dotenv()

from app.api.endpoints import router as api_router
from app.db import create_db_and_tables

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for database initialization"""
    # Initialize database tables
    create_db_and_tables()
    yield

app = FastAPI(
    title="AI Due Diligence MVP",
    description="API for processing and analyzing renewable energy project documents",
    version="0.1.0",
    lifespan=lifespan
)

# Configure CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:8501",  # Streamlit default
        os.getenv("FRONTEND_URL", "http://localhost:3000")  # Optional custom frontend
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routes
app.include_router(api_router, prefix="/api/v1", tags=["documents"])

@app.get("/")
async def root() -> dict:
    """Root endpoint providing basic API information"""
    return {
        "message": "Welcome to the AI Due Diligence MVP API!",
        "version": "0.1.0",
        "docs_url": "/docs"
    }
