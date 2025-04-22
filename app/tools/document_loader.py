from pathlib import Path
from typing import Union, Dict, Any

from pypdf import PdfReader
from docx import Document

class DocumentLoader:
    """Utility class for loading and extracting text from different document types"""
    
    @staticmethod
    def extract_from_pdf(file_path: Union[str, Path]) -> str:
        """Extract text from a PDF file"""
        reader = PdfReader(file_path)
        return "\n".join(page.extract_text() for page in reader.pages)
    
    @staticmethod
    def extract_from_docx(file_path: Union[str, Path]) -> str:
        """Extract text from a DOCX file"""
        doc = Document(file_path)
        return "\n".join(paragraph.text for paragraph in doc.paragraphs if paragraph.text.strip())
    
    @classmethod
    def load_document(cls, file_path: Union[str, Path]) -> Dict[str, Any]:
        """Load a document and extract its text based on file type"""
        file_path = Path(file_path)
        
        if not file_path.exists():
            return {
                "filename": file_path.name,
                "file_type": file_path.suffix.lower(),
                "text": "",
                "success": False,
                "error": "File not found"
            }
        
        file_type = file_path.suffix.lower()
        
        try:
            if file_type == '.pdf':
                text = cls.extract_from_pdf(file_path)
            elif file_type in ['.docx', '.doc']:
                text = cls.extract_from_docx(file_path)
            else:
                return {
                    "filename": file_path.name,
                    "file_type": file_type,
                    "text": "",
                    "success": False,
                    "error": f"Unsupported file type: {file_type}"
                }
            
            return {
                "filename": file_path.name,
                "file_type": file_type,
                "text": text,
                "success": True
            }
            
        except Exception as e:
            return {
                "filename": file_path.name,
                "file_type": file_type,
                "text": "",
                "success": False,
                "error": str(e)
            }
