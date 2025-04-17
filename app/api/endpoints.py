from pathlib import Path
from typing import List

from fastapi import APIRouter, UploadFile, File, HTTPException
from fastapi.responses import JSONResponse

from app.tools.document_loader import DocumentLoader
from app.tools.extract_key_info import ExtractKeyInfo
from app.tools.document_summarizer import DocumentSummarizer

router = APIRouter()

# Ensure uploads directory exists
UPLOAD_DIR = Path("uploads")
UPLOAD_DIR.mkdir(exist_ok=True)

@router.post("/upload/")
async def upload_document(file: UploadFile = File(...)):
    """
    Upload and process a document, extracting structured information and generating a summary
    """
    # Validate file type
    allowed_extensions = ['.pdf', '.docx', '.doc']
    file_extension = Path(file.filename).suffix.lower()
    
    if file_extension not in allowed_extensions:
        raise HTTPException(
            status_code=400,
            detail=f"File type not supported. Allowed types: {', '.join(allowed_extensions)}"
        )
    
    # Save the file
    file_path = UPLOAD_DIR / file.filename
    try:
        with open(file_path, "wb") as buffer:
            content = await file.read()
            buffer.write(content)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save file: {str(e)}")
    
    # Process the document
    try:
        # Load document text
        doc_result = DocumentLoader.load_document(file_path)
        if not doc_result["success"]:
            raise ValueError(f"Failed to load document: {doc_result.get('error')}")
        
        # Extract structured information using LLM
        extractor = ExtractKeyInfo()
        project_info = extractor.extract_info(doc_result["text"])
        
        # Generate document summary
        summarizer = DocumentSummarizer()
        doc_summary = summarizer.summarize(doc_result["text"])
        
        return {
            "filename": file.filename,
            "content_type": file.content_type,
            "file_type": doc_result["file_type"],
            "text_length": len(doc_result["text"]),
            "text_preview": doc_result["text"][:500] if doc_result["text"] else None,
            "project_info": project_info.model_dump(exclude_none=True),
            "summary": doc_summary.model_dump(exclude_none=True)
        }
    except Exception as e:
        print(f"Error processing document: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to process document: {str(e)}")

@router.get("/supported-formats/")
async def get_supported_formats() -> JSONResponse:
    """
    Get list of supported document formats
    """
    return JSONResponse(content={
        "supported_formats": [
            {"extension": ".pdf", "description": "PDF documents"},
            {"extension": ".docx", "description": "Microsoft Word documents"},
            {"extension": ".doc", "description": "Legacy Microsoft Word documents"}
        ]
    })
