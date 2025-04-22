from typing import List, Optional, Dict, Any, Union
from pydantic import BaseModel, Field
from anthropic import Anthropic
import os
from dotenv import load_dotenv
import json
import re

class ProjectInfo(BaseModel):
    # Core Project Details
    project_name: Optional[str] = Field(None, description="The official name of the renewable energy project.")
    project_type: Optional[str] = Field(None, description="Type of project (e.g., Solar PV, Onshore Wind, Offshore Wind, Battery Storage, Hybrid).")
    capacity_mw: Optional[float] = Field(None, description="The generation capacity of the project in Megawatts (MW).")
    location_address: Optional[str] = Field(None, description="The physical address, coordinates, or description of the project's location (e.g., county, state, near landmark).")
    project_area_size: Optional[str] = Field(None, description="The size of the project area if mentioned (e.g., '26,000 acres', '11,287-acre project area').")
    technology_details: Optional[str] = Field(None, description="Specific technology mentioned (e.g., 'Monocrystalline Silicon PV Panels', 'Vestas V162-5.6 MW turbines').")
    number_of_units: Optional[int] = Field(None, description="Number of turbines or distinct generation units mentioned.")

    # Parties Involved
    developer_name: Optional[str] = Field(None, description="The name of the company developing the project.")
    purchaser_or_offtaker: Optional[str] = Field(None, description="The entity purchasing the power (e.g., Utility, Corporate Offtaker). Often called 'Purchaser' or 'Offtaker'.")
    seller_or_provider: Optional[str] = Field(None, description="The entity selling the power, often the project owner/developer. Often called 'Seller' or 'Provider'.")
    key_counterparties: List[str] = Field(default_factory=list, description="List of other key counterparties mentioned (e.g., EPC contractor, landowner, financier).")

    # PPA Specific Terms
    agreement_type: Optional[str] = Field(None, description="Type of agreement if specified (e.g., 'Power Purchase Agreement', 'PPA', 'SPPA').")
    agreement_effective_date: Optional[str] = Field(None, description="The date the agreement becomes effective (e.g., 'January 15, 2024', 'Effective Date'). Try YYYY-MM-DD format.")
    term_length_years: Optional[Union[int, str]] = Field(None, description="The duration of the agreement term in years (e.g., 20, 'twenty (20) years').")
    contract_price_details: Optional[str] = Field(None, description="Details about the price of energy (e.g., '$XX/MWh', 'fixed price', 'escalating rate').")
    guaranteed_output_or_availability: Optional[str] = Field(None, description="Mention of guaranteed energy production, availability metrics, or performance guarantees.")
    liquidated_damages_mention: Optional[bool] = Field(None, description="Whether liquidated damages for delays or performance shortfalls are mentioned (True/False).")
    delivery_point: Optional[str] = Field(None, description="The point where energy ownership transfers (e.g., 'Interconnection Point', 'Metering Device').")
    environmental_attributes_ownership: Optional[str] = Field(None, description="Who owns the RECs or other environmental attributes (e.g., 'Seller retains all ownership', 'Buyer receives RECs').")

    # EIA/Permitting Specific Terms
    lead_regulatory_agency: Optional[str] = Field(None, description="Lead government agency mentioned conducting review (e.g., 'Bureau of Ocean Energy Management', 'BLM', 'Scottish Government Energy Consents Unit').")
    assessment_type: Optional[str] = Field(None, description="Type of assessment document (e.g., 'Environmental Impact Statement', 'EIS', 'Environmental Impact Assessment', 'EIA').")
    key_permits_mentioned: List[str] = Field(default_factory=list, description="List of specific permits or approvals mentioned (e.g., 'Section 36 consent', 'Conditional Use Permit', 'ROW grant').")
    key_environmental_concerns: List[str] = Field(default_factory=list, description="List of key environmental resources or impacts discussed (e.g., 'wildlife', 'visual impacts', 'cultural resources', 'noise').")
    mitigation_mentioned: Optional[bool] = Field(None, description="Whether mitigation measures for environmental impacts are discussed (True/False).")

    # Key Dates
    key_project_dates: List[str] = Field(default_factory=list, description="List of important project milestone dates mentioned (e.g., 'COD targeted for Q4 2025', 'NTP anticipated Q3 2024', 'Financial Close date'). Try YYYY-MM-DD format if possible.")

    @classmethod
    def parse_response(cls, content: str) -> 'ProjectInfo':
        """Parse Claude's response into a ProjectInfo object"""
        try:
            # Remove any non-JSON text before the first {
            content = content[content.find('{'):] if '{' in content else content
            # Remove any non-JSON text after the last }
            content = content[:content.rfind('}')+1] if '}' in content else content
            # Clean control characters
            content = re.sub(r'[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]', '', content)
            # Normalize whitespace
            content = re.sub(r'\s+', ' ', content)
            
            data = json.loads(content)
            # Initialize list fields if not present
            data.setdefault('key_counterparties', [])
            data.setdefault('key_permits_mentioned', [])
            data.setdefault('key_environmental_concerns', [])
            data.setdefault('key_project_dates', [])
            return cls(**data)
        except Exception as e:
            print(f"Error parsing response: {str(e)}")
            return cls()

class ExtractKeyInfo:
    """Class for extracting key information from renewable energy project documents"""
    
    def __init__(self):
        load_dotenv()
        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            raise ValueError("ANTHROPIC_API_KEY must be set")
        self.client = Anthropic(api_key=api_key)
        
        self.system_prompt = """You are an expert assistant specializing in renewable energy project documentation (PPAs, EIAs, etc.).
        Analyze the following text extracted from a project document.
        Extract the key information based *only* on the provided text.
        Format your response as a single, valid JSON object matching the provided schema structure.
        If a specific piece of information is not found in the text, use a JSON `null` value for that field.
        For boolean fields (like 'liquidated_damages_mention'), use `true` or `false` if explicitly mentioned or clearly implied, otherwise use `null`.
        Ensure the output is only the JSON object, with no introductory text or explanations."""

    def _clean_text(self, text: str) -> str:
        """Clean text by removing control characters and normalizing whitespace"""
        # Remove or replace control characters
        text = re.sub(r'[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]', '', text)
        # Normalize whitespace
        text = re.sub(r'\s+', ' ', text)
        # Strip leading/trailing whitespace
        return text.strip()

    def extract_info(self, text: str) -> ProjectInfo:
        """Extract key information from document text"""
        try:
            # Clean input text
            cleaned_text = self._clean_text(text)
            
            schema_json = json.dumps(ProjectInfo.model_json_schema(), indent=2)
            user_message = f"""Please analyze this text from a renewable energy project document and extract key information.
            Format your response as a JSON object matching this schema:
            {schema_json}
            
            Text to analyze:
            {cleaned_text}
            
            Return ONLY the JSON object. Use null for missing information and empty lists for list fields with no data."""

            response = self.client.messages.create(
                model="claude-3-sonnet-20240229",
                max_tokens=4096,
                messages=[{
                    "role": "user",
                    "content": user_message
                }],
                system=self.system_prompt
            )
            
            return ProjectInfo.parse_response(response.content[0].text)
                
        except Exception as e:
            print(f"Error in extract_info: {str(e)}")
            raise Exception(f"Error extracting information: {str(e)}") 