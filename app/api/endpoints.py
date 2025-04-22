from pathlib import Path
from typing import Dict, Any
import uuid
from fastapi import APIRouter, UploadFile, File, HTTPException, BackgroundTasks
from fastapi.responses import JSONResponse

from app.tools.document_loader import DocumentLoader
from app.tools.extract_key_info import ExtractKeyInfo
from app.tools.document_summarizer import DocumentSummarizer

router = APIRouter()

# Ensure uploads directory exists
UPLOAD_DIR = Path("uploads")
UPLOAD_DIR.mkdir(exist_ok=True)

# Store task results
TASKS: Dict[str, Dict[str, Any]] = {}

def process_document(task_id: str, file_path: Path):
    """Background task to process the document"""
    try:
        # Load document text
        doc_result = DocumentLoader.load_document(file_path)
        if not doc_result["success"]:
            TASKS[task_id] = {
                "status": "error",
                "message": f"Failed to load document: {doc_result['error']}"
            }
            return

        # Extract structured information and generate summary
        extractor = ExtractKeyInfo()
        summarizer = DocumentSummarizer()
        
        project_info = extractor.extract_info(doc_result["text"])
        doc_summary = summarizer.summarize(doc_result["text"])
        
        TASKS[task_id] = {
            "status": "completed",
            "project_info": project_info.model_dump(exclude_none=True),
            "summary": {"content": doc_summary.content}
        }
        
    except Exception as e:
        TASKS[task_id] = {"status": "error", "message": str(e)}
    finally:
        # Clean up uploaded file
        try:
            file_path.unlink()
        except Exception:
            pass  # Ignore cleanup errors

@router.post("/upload/")
async def upload_document(background_tasks: BackgroundTasks, file: UploadFile = File(...)) -> Dict[str, str]:
    """Upload a document and start processing it asynchronously"""
    # Validate file type
    allowed_extensions = ['.pdf', '.docx', '.doc']
    file_extension = Path(file.filename).suffix.lower()
    
    if file_extension not in allowed_extensions:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type. Allowed types: {', '.join(allowed_extensions)}"
        )
    
    # Generate task ID and save file
    task_id = str(uuid.uuid4())
    file_path = UPLOAD_DIR / f"{task_id}{file_extension}"
    
    try:
        content = await file.read()
        file_path.write_bytes(content)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save file: {str(e)}")
    
    # Initialize task and start processing
    TASKS[task_id] = {"status": "processing"}
    background_tasks.add_task(process_document, task_id, file_path)
    
    return {"task_id": task_id}

@router.get("/status/{task_id}")
async def get_task_status(task_id: str) -> Dict[str, Any]:
    """Get the status of a document processing task"""
    if task_id not in TASKS:
        raise HTTPException(status_code=404, detail="Task not found")
    return TASKS[task_id]

@router.get("/supported-formats")
async def get_supported_formats() -> Dict[str, list]:
    """Get list of supported document formats"""
    return {
        "supported_formats": [
            {"extension": ".pdf", "description": "PDF documents"},
            {"extension": ".docx", "description": "Microsoft Word documents"},
            {"extension": ".doc", "description": "Legacy Microsoft Word documents"}
        ]
    }
