from pathlib import Path
from typing import Dict, Any, List
import uuid
from fastapi import APIRouter, UploadFile, File, HTTPException, BackgroundTasks, Depends
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from app.tools.document_loader import DocumentLoader
from app.tools.extract_key_info import ExtractKeyInfo
from app.tools.document_summarizer import DocumentSummarizer
from app.tools.risk_flagger import RiskFlagger
from app.tools.external_info_fetcher import ExternalInfoFetcher
from app.db import DocumentAnalysis, get_db

router = APIRouter()

# Ensure uploads directory exists
UPLOAD_DIR = Path("uploads")
UPLOAD_DIR.mkdir(exist_ok=True)

# Store task results
TASKS: Dict[str, Dict[str, Any]] = {}

async def process_document(task_id: str, file_path: Path, db: Session):
    """Process the document and store results in database"""
    processing_error_details: List[str] = []
    db_record = None
    
    try:
        # Create initial database record
        db_record = DocumentAnalysis(
            original_filename=file_path.name,
            processing_status="Processing"
        )
        db.add(db_record)
        db.commit()
        db.refresh(db_record)

        # Update task status to show processing started
        TASKS[task_id] = {"status": "processing", "analysis_id": db_record.id}

        # Load document text
        doc_result = DocumentLoader.load_document(file_path)
        if not doc_result["success"]:
            error_msg = f"Failed to load document: {doc_result['error']}"
            processing_error_details.append(error_msg)
            raise Exception(error_msg)

        extracted_text = doc_result["text"]
        db_record.extracted_text_preview = extracted_text[:500] + "..." if len(extracted_text) > 500 else extracted_text

        # Extract structured information and generate summary
        extractor = ExtractKeyInfo()
        summarizer = DocumentSummarizer()
        
        try:
            project_info = extractor.extract_info(extracted_text)
        except Exception as e:
            processing_error_details.append(f"Error extracting information: {str(e)}")
            project_info = None
        
        try:
            doc_summary = summarizer.summarize(extracted_text)
            summary = doc_summary.content
        except Exception as e:
            processing_error_details.append(f"Error generating summary: {str(e)}")
            summary = None
        
        # Analyze for potential risks
        try:
            risk_flagger = RiskFlagger()
            risk_flags = risk_flagger.analyze_project(project_info) if project_info else []
        except Exception as e:
            processing_error_details.append(f"Error analyzing risks: {str(e)}")
            risk_flags = []

        # Update database record with all extracted information
        db_record.processing_status = "Completed" if not processing_error_details else "Partial"
        db_record.processing_notes = "; ".join(processing_error_details) if processing_error_details else "Completed successfully"
        db_record.summary = summary
        db_record.risk_flags = risk_flags
        
        if project_info:
            data_dict = project_info.model_dump()
            direct_fields = [
                'project_name', 'project_type', 'capacity_mw', 'location_address',
                'project_area_size', 'technology_details', 'number_of_units',
                'developer_name', 'purchaser_or_offtaker', 'seller_or_provider',
                'key_counterparties', 'agreement_type', 'agreement_effective_date',
                'term_length_years', 'contract_price_details',
                'guaranteed_output_or_availability', 'liquidated_damages_mention',
                'delivery_point', 'environmental_attributes_ownership',
                'lead_regulatory_agency', 'assessment_type', 'key_permits_mentioned',
                'key_environmental_concerns', 'mitigation_mentioned', 'key_project_dates'
            ]
            
            for field in direct_fields:
                if field in data_dict:
                    setattr(db_record, field, data_dict[field])

            # Fetch external information about entities
            try:
                info_fetcher = ExternalInfoFetcher()
                
                # Fetch developer info
                if db_record.developer_name:
                    developer_summary = await info_fetcher.fetch_and_summarize_entity_info(db_record.developer_name)
                    db_record.developer_external_summary = developer_summary
                
                # Fetch offtaker info
                if db_record.purchaser_or_offtaker:
                    offtaker_summary = await info_fetcher.fetch_and_summarize_entity_info(db_record.purchaser_or_offtaker)
                    db_record.offtaker_external_summary = offtaker_summary
                
            except Exception as e:
                processing_error_details.append(f"Error fetching external info: {str(e)}")

        db.commit()
        db.refresh(db_record)
        
        # Update task status
        TASKS[task_id] = {
            "status": "completed" if not processing_error_details else "partial",
            "project_info": project_info.model_dump() if project_info else {},
            "summary": {"content": summary} if summary else {"content": ""},
            "risk_flags": risk_flags if risk_flags else [],
            "processing_notes": db_record.processing_notes,
            "analysis_id": db_record.id,
            "external_info": {
                "developer": {
                    "name": db_record.developer_name,
                    "summary": db_record.developer_external_summary
                } if db_record.developer_name else None,
                "offtaker": {
                    "name": db_record.purchaser_or_offtaker,
                    "summary": db_record.offtaker_external_summary
                } if db_record.purchaser_or_offtaker else None
            } if (db_record.developer_name or db_record.purchaser_or_offtaker) else {}
        }
        
    except Exception as e:
        error_msg = str(e)
        if db_record:
            db_record.processing_status = "Failed"
            db_record.processing_notes = error_msg
            db.commit()
        TASKS[task_id] = {
            "status": "error",
            "message": error_msg,
            "project_info": {},
            "summary": {"content": ""},
            "risk_flags": [],
            "processing_notes": error_msg,
            "analysis_id": db_record.id if db_record else None,
            "external_info": {}
        }
    finally:
        # Clean up uploaded file
        try:
            file_path.unlink()
        except Exception:
            pass

@router.post("/upload/")
async def upload_document(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
) -> Dict[str, str]:
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
    background_tasks.add_task(process_document, task_id, file_path, db)
    
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

@router.get("/analyses/")
async def get_analyses(db: Session = Depends(get_db)):
    """Get list of all document analyses"""
    analyses = db.query(DocumentAnalysis).order_by(DocumentAnalysis.created_at.desc()).all()
    return [{
        "id": analysis.id,
        "filename": analysis.original_filename,
        "status": analysis.processing_status,
        "project_name": analysis.project_name,
        "project_type": analysis.project_type,
        "capacity_mw": analysis.capacity_mw,
        "created_at": analysis.created_at,
        "processing_notes": analysis.processing_notes
    } for analysis in analyses]

@router.get("/analyses/{analysis_id}")
async def get_analysis(analysis_id: int, db: Session = Depends(get_db)):
    """Get detailed information for a specific analysis"""
    analysis = db.query(DocumentAnalysis).filter(DocumentAnalysis.id == analysis_id).first()
    if not analysis:
        raise HTTPException(status_code=404, detail="Analysis not found")
    
    return {
        "id": analysis.id,
        "metadata": {
            "filename": analysis.original_filename,
            "status": analysis.processing_status,
            "created_at": analysis.created_at,
            "processing_notes": analysis.processing_notes
        },
        "project_info": {
            "name": analysis.project_name,
            "type": analysis.project_type,
            "capacity_mw": analysis.capacity_mw,
            "location": analysis.location_address,
            "area_size": analysis.project_area_size,
            "technology": analysis.technology_details,
            "units": analysis.number_of_units
        },
        "parties": {
            "developer": {
                "name": analysis.developer_name,
                "external_summary": analysis.developer_external_summary
            } if analysis.developer_name else None,
            "offtaker": {
                "name": analysis.purchaser_or_offtaker,
                "external_summary": analysis.offtaker_external_summary
            } if analysis.purchaser_or_offtaker else None,
            "provider": analysis.seller_or_provider,
            "counterparties": analysis.key_counterparties
        },
        "ppa_terms": {
            "agreement_type": analysis.agreement_type,
            "effective_date": analysis.agreement_effective_date,
            "term_years": analysis.term_length_years,
            "price_details": analysis.contract_price_details,
            "guaranteed_output": analysis.guaranteed_output_or_availability,
            "liquidated_damages": analysis.liquidated_damages_mention,
            "delivery_point": analysis.delivery_point,
            "environmental_attributes": analysis.environmental_attributes_ownership
        },
        "environmental": {
            "agency": analysis.lead_regulatory_agency,
            "assessment_type": analysis.assessment_type,
            "permits": analysis.key_permits_mentioned,
            "concerns": analysis.key_environmental_concerns,
            "mitigation_mentioned": analysis.mitigation_mentioned
        },
        "dates": analysis.key_project_dates,
        "analysis_results": {
            "summary": analysis.summary,
            "risk_flags": analysis.risk_flags
        }
    }
