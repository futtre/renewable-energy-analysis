from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

# Load environment variables at startup
load_dotenv()

from app.api.endpoints import router as api_router

app = FastAPI(title="AI Due Diligence MVP")

# Configure CORS for Streamlit frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:8501"],  # Streamlit default port
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routes
app.include_router(api_router, prefix="/api/v1", tags=["documents"])

@app.get("/")
async def root():
    """
    Root endpoint providing basic API information"""
    return {"message": "Welcome to the AI Due Diligence MVP API!"}
