from typing import Dict, List, Optional
from pydantic import BaseModel
from anthropic import Anthropic
import os
from dotenv import load_dotenv
import json
import re

class DocumentSummary(BaseModel):
    """Simple model for document summary"""
    content: str = ""

class DocumentSummarizer:
    """Class for generating summaries of renewable energy project documents"""
    
    def __init__(self):
        load_dotenv()
        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            raise ValueError("ANTHROPIC_API_KEY must be set")
        self.client = Anthropic(api_key=api_key)
        
        self.system_prompt = """Create a concise summary of this renewable energy project document.
        Focus on the key points and main takeaways.
        Include important technical, commercial, and environmental aspects if present.
        Be clear and direct in your summary."""
    
    def _clean_text(self, text: str) -> str:
        """Clean text by removing control characters and normalizing whitespace"""
        # Remove or replace control characters
        text = re.sub(r'[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]', '', text)
        # Normalize whitespace
        text = re.sub(r'\s+', ' ', text)
        # Strip leading/trailing whitespace
        return text.strip()

    def _clean_json_response(self, content: str) -> str:
        """Clean the response content to ensure valid JSON"""
        # Remove any non-JSON text before the first {
        content = content[content.find('{'):] if '{' in content else content
        # Remove any non-JSON text after the last }
        content = content[:content.rfind('}')+1] if '}' in content else content
        # Clean control characters
        content = self._clean_text(content)
        return content

    def summarize(self, text: str) -> DocumentSummary:
        """Generate a summary of the document text"""
        try:
            # Clean input text
            cleaned_text = self._clean_text(text)
            
            response = self.client.messages.create(
                model="claude-3-sonnet-20240229",
                max_tokens=4096,
                messages=[{
                    "role": "user",
                    "content": f"""Please provide a clear and concise summary of this document:

                    {cleaned_text}

                    Return the summary as a JSON object with a single 'content' field."""
                }],
                system=self.system_prompt
            )
            
            content = response.content[0].text
            
            try:
                # Try to parse as JSON directly first
                cleaned_content = self._clean_json_response(content)
                data = json.loads(cleaned_content)
                return DocumentSummary(**data)
            except json.JSONDecodeError as e:
                print(f"JSON parsing error: {str(e)}")
                # If JSON parsing fails, use the content directly
                return DocumentSummary(content=self._clean_text(content))
                
        except Exception as e:
            print(f"Error in summarize: {str(e)}")
            raise Exception(f"Error generating summary: {str(e)}") 