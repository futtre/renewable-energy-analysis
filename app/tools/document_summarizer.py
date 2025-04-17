from typing import Dict, Any
from pydantic import BaseModel, Field
from anthropic import Anthropic
import os
from dotenv import load_dotenv
import json

class DocumentSummary(BaseModel):
    """Pydantic model for structured document summary"""
    executive_summary: str = Field(..., description="A 2-3 sentence high-level overview of the project.")
    key_highlights: Dict[str, str] = Field(..., description="Key aspects of the project organized by category (e.g., Technology, Timeline, Participants).")
    risks_and_considerations: list[str] = Field(default_factory=list, description="Potential risks, dependencies, or important considerations mentioned in the document.")
    next_steps: list[str] = Field(default_factory=list, description="Any mentioned next steps, milestones, or future actions.")

class DocumentSummarizer:
    """Class for generating structured summaries of renewable energy project documents using LLM"""
    
    def __init__(self):
        # Load environment variables
        load_dotenv()
        
        # Initialize Claude client
        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            raise ValueError("ANTHROPIC_API_KEY must be set in environment variables")
        self.client = Anthropic(api_key=api_key)
        
        # Create the system prompt
        self.system_prompt = """You are a specialized assistant for analyzing renewable energy project documents.
        Your task is to create structured summaries that highlight the most important aspects of the project.
        Focus on key commercial, technical, and timeline aspects that would be relevant for due diligence.
        Be concise but comprehensive, and ensure all information is directly supported by the document.
        If certain aspects are not mentioned in the document, leave those sections empty rather than making assumptions."""
    
    def summarize(self, text: str) -> DocumentSummary:
        """Generate a structured summary of the document text
        
        Args:
            text (str): The document text to analyze
            
        Returns:
            DocumentSummary: Structured summary of the document
            
        Raises:
            ValueError: If the API response cannot be parsed
            Exception: For other errors during summarization
        """
        # Create the user message with the schema
        schema_example = DocumentSummary.model_json_schema()
        user_message = f"""Please analyze this renewable energy project document and create a structured summary according to this exact JSON schema:
        {json.dumps(schema_example, indent=2)}
        
        Focus on extracting:
        1. A clear executive summary of the project
        2. Key highlights organized by relevant categories
        3. Any risks or important considerations
        4. Next steps or upcoming milestones
        
        Document text to analyze:
        {text}
        
        Return ONLY the JSON object with the structured summary, nothing else."""
        
        try:
            # Call Claude API
            response = self.client.messages.create(
                model="claude-3-7-sonnet-20250219",
                max_tokens=1500,
                messages=[{
                    "role": "user",
                    "content": user_message
                }],
                system=self.system_prompt
            )
            
            # Extract JSON from response
            content = response.content[0].text
            
            # Parse JSON and create DocumentSummary object
            try:
                # Find JSON block in response
                json_start = content.find('{')
                json_end = content.rfind('}') + 1
                if json_start >= 0 and json_end > json_start:
                    json_str = content[json_start:json_end]
                    data = json.loads(json_str)
                    return DocumentSummary(**data)
                else:
                    raise ValueError("No JSON found in Claude's response")
            except json.JSONDecodeError as e:
                raise ValueError(f"Failed to parse JSON from Claude's response: {e}")
            
        except Exception as e:
            raise Exception(f"Error generating summary: {e}") 