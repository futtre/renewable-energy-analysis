from datetime import datetime, UTC
import os
import json
from sqlalchemy import Column, Integer, String, DateTime, Text, Float, Boolean, TypeDecorator, JSON
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()

class JSONEncodedDict(TypeDecorator):
    """Represents a JSON structure as a text-based column."""
    impl = Text

    def process_bind_param(self, value, dialect):
        if value is not None:
            return json.dumps(value)
        return None

    def process_result_value(self, value, dialect):
        if value is not None:
            return json.loads(value)
        return None

class DocumentAnalysis(Base):
    __tablename__ = "document_analysis"

    # --- Metadata ---
    id = Column(Integer, primary_key=True, index=True)
    original_filename = Column(String, index=True)
    upload_time = Column(DateTime, default=lambda: datetime.now(UTC))
    processing_status = Column(String, default="Processing")  # Processing, Completed, Failed, Partial
    processing_notes = Column(Text, nullable=True)  # Store any warnings or partial errors

    # --- Extracted Info (from ProjectInfo Pydantic model) ---
    # Core Project Details
    project_name = Column(String, nullable=True, index=True)
    project_type = Column(String, nullable=True)
    capacity_mw = Column(Float, nullable=True)
    location_address = Column(Text, nullable=True)  # Use Text for potentially long addresses
    project_area_size = Column(String, nullable=True)
    technology_details = Column(Text, nullable=True)
    number_of_units = Column(Integer, nullable=True)

    # Parties Involved with External Info
    developer_name = Column(String, nullable=True, index=True)
    developer_external_summary = Column(Text, nullable=True)  # External info about developer
    purchaser_or_offtaker = Column(String, nullable=True, index=True)
    offtaker_external_summary = Column(Text, nullable=True)  # External info about offtaker
    seller_or_provider = Column(String, nullable=True, index=True)
    key_counterparties = Column(JSONEncodedDict, nullable=True)  # Store lists as JSON

    # PPA Specific Terms
    agreement_type = Column(String, nullable=True)
    agreement_effective_date = Column(String, nullable=True)  # Store as string for flexibility
    term_length_years = Column(Float, nullable=True)
    contract_price_details = Column(Text, nullable=True)
    guaranteed_output_or_availability = Column(Text, nullable=True)
    liquidated_damages_mention = Column(Boolean, nullable=True)
    delivery_point = Column(String, nullable=True)
    environmental_attributes_ownership = Column(String, nullable=True)

    # EIA/Permitting Specific Terms
    lead_regulatory_agency = Column(String, nullable=True)
    assessment_type = Column(String, nullable=True)
    key_permits_mentioned = Column(JSONEncodedDict, nullable=True)  # Store as JSON-encoded text
    key_environmental_concerns = Column(JSONEncodedDict, nullable=True)  # Store as JSON-encoded text
    mitigation_mentioned = Column(Boolean, nullable=True)

    # Key Dates (Consolidated)
    key_project_dates = Column(JSONEncodedDict, nullable=True)  # Store as JSON-encoded text

    # --- Analysis Outputs ---
    summary = Column(Text, nullable=True)
    risk_flags = Column(JSONEncodedDict, nullable=True)  # Store as JSON-encoded text
    extracted_text_preview = Column(Text, nullable=True)  # Store the first 500 chars of extracted text

    # --- Timestamps ---
    created_at = Column(DateTime, default=lambda: datetime.now(UTC))
    updated_at = Column(DateTime, default=lambda: datetime.now(UTC), onupdate=lambda: datetime.now(UTC))

    def __repr__(self):
        return f"<DocumentAnalysis(id={self.id}, filename='{self.original_filename}', project='{self.project_name}')>" 