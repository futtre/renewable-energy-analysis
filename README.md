# AI Due Diligence MVP for Renewable Energy Projects

A FastAPI and Streamlit-based application for analyzing renewable energy project documents using AI.

## Features

- Upload and process PDF and Word documents (.pdf, .docx, .doc)
- Extract structured project information using Claude AI
- Generate concise document summaries
- Asynchronous processing with real-time status updates
- Clean and modern Streamlit UI

## Key Components

- **Document Processing**: Extracts text from PDFs and Word documents
- **Information Extraction**: Uses Claude AI to extract structured project information including:
  - Basic project details (name, type, capacity, location)
  - Key parties (developer, purchaser/offtaker, other counterparties)
  - PPA terms and conditions
  - Environmental and permitting information
  - Key project dates
- **Document Summarization**: Generates concise summaries focusing on key aspects
- **Real-time Status Updates**: Tracks processing status and provides immediate feedback

## Setup

1. Create a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate 
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Set up environment variables:
   - Copy `.env.example` to `.env`
   - Add your Anthropic API key:
     ```
     ANTHROPIC_API_KEY=your_api_key_here
     FRONTEND_URL=http://localhost:3000  # Optional: Custom frontend URL
     ```

## Running the Application

1. Start the FastAPI backend:
   ```bash
   uvicorn app.main:app --reload
   ```
   The API will be available at `http://localhost:8000`

2. Start the Streamlit frontend:
   ```bash
   streamlit run streamlit_app.py
   ```
   The UI will be available at `http://localhost:8501`

## API Endpoints

### POST /api/v1/upload/
Upload a document for processing.

**Request:**
- Multipart form data with file

**Response:**
```json
{
    "task_id": "uuid-task-identifier"
}
```

### GET /api/v1/status/{task_id}
Get processing status and results.

**Response:**
```json
{
    "status": "completed",
    "project_info": {
        "project_name": "Example Solar Project",
        "project_type": "Solar PV",
        "capacity_mw": 100.0,
        "location_address": "Example County, State",
        "project_area_size": "500 acres",
        "technology_details": "Monocrystalline Solar Panels",
        "developer_name": "Example Developer",
        "purchaser_or_offtaker": "Example Utility",
        "key_counterparties": ["EPC Contractor", "O&M Provider"],
        "agreement_type": "Power Purchase Agreement",
        "term_length_years": 20,
        "key_project_dates": ["COD: 2025-01-01", "Construction Start: 2024-06-01"]
    },
    "summary": {
        "content": "Document summary text..."
    }
}
```

### GET /api/v1/supported-formats
Get list of supported document formats.

**Response:**
```json
{
    "supported_formats": [
        {"extension": ".pdf", "description": "PDF documents"},
        {"extension": ".docx", "description": "Microsoft Word documents"},
        {"extension": ".doc", "description": "Legacy Microsoft Word documents"}
    ]
}
```

## Architecture

- **FastAPI Backend**: Handles document processing and AI integration
- **Streamlit Frontend**: Provides user interface for document upload and results display
- **Claude AI**: Powers the information extraction and summarization
- **Background Processing**: Handles long-running tasks asynchronously
- **Real-time Updates**: Enables status checking and result retrieval

## Technical Details

- FastAPI for the API framework
- Streamlit for the frontend UI
- `python-docx` and `pypdf` for document parsing
- Anthropic's Claude 3 Sonnet for AI processing
- Pydantic for data validation and serialization
- Background tasks for asynchronous processing
