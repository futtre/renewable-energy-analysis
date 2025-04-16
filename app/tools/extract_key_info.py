from typing import List, Optional
from pydantic import BaseModel, Field
from anthropic import Anthropic
import os
from dotenv import load_dotenv
import json

class ProjectInfo(BaseModel):
    """Pydantic model for structured renewable energy project information"""
    project_name: Optional[str] = Field(None, description="The official name of the renewable energy project.")
    project_type: Optional[str] = Field(None, description="Type of project (e.g., Solar PV, Onshore Wind, Offshore Wind, Battery Storage).")
    capacity_mw: Optional[float] = Field(None, description="The generation capacity of the project in Megawatts (MW).")
    location_address: Optional[str] = Field(None, description="The physical address or description of the project's location.")
    developer_name: Optional[str] = Field(None, description="The name of the company developing the project.")
    key_dates: List[str] = Field([], description="List of important dates mentioned (e.g., PPA signing date, COD, NTP), in YYYY-MM-DD format if possible.")
    counterparties: List[str] = Field([], description="List of key counterparties mentioned (e.g., offtaker, EPC contractor, landowner).")

class ExtractKeyInfo:
    """Class for extracting structured information from renewable energy project documents using Claude"""
    
    def __init__(self):
        # Load environment variables
        load_dotenv()
        
        # Initialize Claude client
        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            raise ValueError("ANTHROPIC_API_KEY must be set in environment variables")
        self.client = Anthropic(api_key=api_key)
        
        # Create the system prompt
        self.system_prompt = """You are a specialized assistant for extracting structured information from renewable energy project documents.
        Your task is to analyze the provided text and extract key information according to a specific schema.
        You must return the information in valid JSON format that matches the schema exactly.
        If a piece of information is not found in the text, leave it as null or an empty list as appropriate.
        Be precise and only include information that is explicitly stated in the text."""
    
    def extract_info(self, text: str) -> ProjectInfo:
        """Extract key information from document text using Claude
        
        Args:
            text (str): The document text to analyze
            
        Returns:
            ProjectInfo: Structured information about the renewable energy project
            
        Raises:
            ValueError: If the API response cannot be parsed
            Exception: For other errors during extraction
        """
        # Create the user message with the schema
        schema_example = ProjectInfo.model_json_schema()
        user_message = f"""Please analyze this text and extract information according to this exact JSON schema:
        {json.dumps(schema_example, indent=2)}
        
        Text to analyze:
        {text}
        
        Return ONLY the JSON object with the extracted information, nothing else."""
        
        try:
            # Call Claude API
            response = self.client.messages.create(
                model="claude-3-7-sonnet-20250219",
                max_tokens=1000,
                messages=[{
                    "role": "user",
                    "content": user_message
                }],
                system=self.system_prompt
            )
            
            # Extract JSON from response
            content = response.content[0].text
            
            # Parse JSON and create ProjectInfo object
            try:
                # Find JSON block in response
                json_start = content.find('{')
                json_end = content.rfind('}') + 1
                if json_start >= 0 and json_end > json_start:
                    json_str = content[json_start:json_end]
                    data = json.loads(json_str)
                    return ProjectInfo(**data)
                else:
                    raise ValueError("No JSON found in Claude's response")
            except json.JSONDecodeError as e:
                raise ValueError(f"Failed to parse JSON from Claude's response: {e}")
            
        except Exception as e:
            raise Exception(f"Error extracting information: {e}") 