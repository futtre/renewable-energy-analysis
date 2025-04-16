# WIP - due diligence app for renewable energy


## Features

- Upload PDF and Word documents
- Extract text content using document parsers
- Use LLM to analyze and extract structured project information
- Return both raw text and structured data via API

```

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
   - Add your Anthropic API key or any other LLM provider:
     ```
     ANTHROPIC_API_KEY=your_api_key_here
     ```

## Running the Service

Start the FastAPI server:
```bash
uvicorn app.main:app --reload
```

The API will be available at `http://localhost:8000`

## API Endpoints

### POST /api/v1/upload/
Upload and process a document.

**Request:**
- Multipart form data with file

**Response:**
```json
{
    "filename": "example.pdf",
    "content_type": "application/pdf",
    "file_type": ".pdf",
    "text_length": 1234,
    "text_preview": "First 500 characters...",
    "project_info": {
        "project_name": "Example Project",
        "project_type": "Solar PV",
        "capacity_mw": 100,
        "location_address": "Example Location",
        "developer_name": "Example Developer",
        "key_dates": ["2024-01-01"],
        "counterparties": ["Example Contractor"]
    }
}
```

### GET /api/v1/supported-formats/
Get list of supported document formats.

## Development

- The project uses FastAPI for the API framework
- Document parsing is handled by `python-docx` and `PyPDF2`
- Text analysis is performed using Anthropic's Claude AI
- Structured data is validated using Pydantic models