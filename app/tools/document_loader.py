from pathlib import Path
from typing import Union, Dict, Any

from pypdf import PdfReader
from docx import Document

class DocumentLoader:
    """Utility class for loading and extracting text from different document types"""
    
    @staticmethod
    def extract_from_pdf(file_path: Union[str, Path]) -> str:
        """Extract text from a PDF file"""
        print(f"Loading PDF file: {file_path}")
        reader = PdfReader(file_path)
        text = ""
        for i, page in enumerate(reader.pages):
            page_text = page.extract_text()
            print(f"Extracted text from page {i+1}: {page_text[:100]}...")
            text += page_text + "\n"
        return text
    
    @staticmethod
    def extract_from_docx(file_path: Union[str, Path]) -> str:
        """Extract text from a DOCX file"""
        print(f"Loading DOCX file: {file_path}")
        doc = Document(file_path)
        text = ""
        for i, paragraph in enumerate(doc.paragraphs):
            if paragraph.text.strip():
                print(f"Extracted paragraph {i+1}: {paragraph.text[:100]}...")
                text += paragraph.text + "\n"
        return text
    
    @classmethod
    def load_document(cls, file_path: Union[str, Path]) -> Dict[str, Any]:
        """Load a document and extract its text based on file type"""
        file_path = Path(file_path)
        print(f"Processing document: {file_path}")
        
        if not file_path.exists():
            print(f"File not found: {file_path}")
            raise FileNotFoundError(f"File not found: {file_path}")
        
        file_type = file_path.suffix.lower()
        print(f"Detected file type: {file_type}")
        
        try:
            if file_type == '.pdf':
                text = cls.extract_from_pdf(file_path)
            elif file_type in ['.docx', '.doc']:
                text = cls.extract_from_docx(file_path)
            else:
                print(f"Unsupported file type: {file_type}")
                raise ValueError(f"Unsupported file type: {file_type}")
            
            print(f"Successfully extracted text, length: {len(text)}")
            return {
                "filename": file_path.name,
                "file_type": file_type,
                "text": text,
                "success": True
            }
            
        except Exception as e:
            print(f"Error processing document: {str(e)}")
            return {
                "filename": file_path.name,
                "file_type": file_type,
                "text": "",
                "success": False,
                "error": str(e)
            }
