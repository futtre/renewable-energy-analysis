import streamlit as st
import requests
import os
import json
from pathlib import Path
from typing import Dict, Any, List
import time

# Configuration
FASTAPI_URL = os.environ.get("FASTAPI_URL", "http://127.0.0.1:8000")
UPLOAD_ENDPOINT = f"{FASTAPI_URL}/api/v1/upload/"

def format_project_info(info: Dict[str, Any], external_info: Dict[str, Any] = None) -> None:
    if not info:
        st.info("No project information was extracted.")
        return

    basic_tab, parties_tab, ppa_tab, env_tab, external_tab = st.tabs([
        "Basic Info", "Parties", "PPA Terms", "Environmental", "External Research"
    ])

    with basic_tab:
        st.markdown("**Basic Project Information**")
        basic_fields = [
            ("project_name", "Project Name"),
            ("project_type", "Project Type"),
            ("capacity_mw", "Capacity (MW)"),
            ("location_address", "Location"),
            ("project_area_size", "Project Area Size"),
            ("technology_details", "Technology Details"),
            ("number_of_units", "Number of Units")
        ]
        for field, label in basic_fields:
            if info.get(field) is not None:
                st.markdown(f"- {label}: {info[field]}")

    with parties_tab:
        st.markdown("**Parties Involved**")
        party_fields = [
            ("developer_name", "Developer"),
            ("purchaser_or_offtaker", "Purchaser/Offtaker"),
            ("seller_or_provider", "Seller/Provider")
        ]
        for field, label in party_fields:
            if info.get(field):
                st.markdown(f"- {label}: {info[field]}")
        if info.get("key_counterparties"):
            st.markdown("- Other Key Counterparties:")
            for party in info["key_counterparties"]:
                st.markdown(f"  - {party}")

    with ppa_tab:
        if any(info.get(field) for field in ["agreement_type", "agreement_effective_date", "term_length_years", "contract_price_details"]):
            st.markdown("**PPA Terms**")
            ppa_fields = [
                ("agreement_type", "Agreement Type"),
                ("agreement_effective_date", "Effective Date"),
                ("term_length_years", "Term Length"),
                ("contract_price_details", "Contract Price Details"),
                ("guaranteed_output_or_availability", "Guaranteed Output/Availability"),
                ("delivery_point", "Delivery Point"),
                ("environmental_attributes_ownership", "Environmental Attributes Ownership")
            ]
            for field, label in ppa_fields:
                if info.get(field):
                    st.markdown(f"- {label}: {info[field]}")
            if info.get("liquidated_damages_mention") is not None:
                st.markdown(f"- Liquidated Damages Mentioned: {info['liquidated_damages_mention']}")

    with env_tab:
        if any(info.get(field) for field in ["lead_regulatory_agency", "assessment_type", "key_permits_mentioned"]):
            st.markdown("**Environmental/Permitting Information**")
            if info.get("lead_regulatory_agency"):
                st.markdown(f"- Lead Regulatory Agency: {info['lead_regulatory_agency']}")
            if info.get("assessment_type"):
                st.markdown(f"- Assessment Type: {info['assessment_type']}")
            if info.get("key_permits_mentioned"):
                st.markdown("- Key Permits:")
                for permit in info["key_permits_mentioned"]:
                    st.markdown(f"  - {permit}")
            if info.get("key_environmental_concerns"):
                st.markdown("- Environmental Concerns:")
                for concern in info["key_environmental_concerns"]:
                    st.markdown(f"  - {concern}")
            if info.get("mitigation_mentioned") is not None:
                st.markdown(f"- Mitigation Measures Mentioned: {info['mitigation_mentioned']}")

    with external_tab:
        st.markdown("**External Research Results**")
        if external_info:
            for party_type in ["developer", "offtaker"]:
                if external_info.get(party_type):
                    st.markdown(f"##### {party_type.title()} Research")
                    st.markdown(f"**{external_info[party_type]['name']}**")
                    if external_info[party_type].get('summary'):
                        with st.expander(f"View {party_type.title()} Summary", expanded=True):
                            st.markdown(external_info[party_type]['summary'])
                    else:
                        st.info(f"No external information found for the {party_type}.")

            if not external_info.get("developer") and not external_info.get("offtaker"):
                st.info("No external research information available.")
        else:
            st.info("No external research information available.")

def format_summary(summary: Dict[str, Any]) -> None:
    if not summary or not summary.get("content"):
        st.info("No summary was generated.")
        return
    st.markdown("**Document Summary**")
    st.markdown(summary["content"])

def format_risk_flags(flags: List[str]) -> None:
    if not flags:
        st.info("No risk flags were identified.")
        return

    st.markdown("**Risk Analysis**")
    categories = {
        "MISSING INFO": [],
        "CONTRACT RISK": [],
        "ENVIRONMENTAL": [],
        "PROJECT SIZE": [],
        "PPA TERM": [],
        "OTHER": []
    }
    
    for flag in flags:
        categorized = False
        for category in categories.keys():
            if flag.startswith(category):
                categories[category].append(flag)
                categorized = True
                break
        if not categorized:
            categories["OTHER"].append(flag)
    
    for category, category_flags in categories.items():
        if category_flags:
            with st.expander(f"{category} ({len(category_flags)})", expanded=True):
                for flag in category_flags:
                    st.markdown(f"⚠️ {flag}")

def poll_status(task_id: str) -> Dict[str, Any]:
    max_retries = 180  # 30 minutes maximum
    retry_count = 0
    
    with st.spinner("Processing document... This may take several minutes."):
        while retry_count < max_retries:
            try:
                response = requests.get(f"{FASTAPI_URL}/api/v1/status/{task_id}")
                if response.status_code == 200:
                    status = response.json()
                    if status["status"] == "completed":
                        return status
                    elif status["status"] == "error":
                        raise Exception(status["message"])
                time.sleep(10)
                retry_count += 1
            except Exception as e:
                raise Exception(f"Error checking status: {str(e)}")
        raise Exception("Processing timeout after 30 minutes")

# App Layout
st.set_page_config(
    page_title="AI Document Analysis MVP",
    layout="wide",
    initial_sidebar_state="expanded"
)

with st.sidebar:
    st.markdown("### About")
    st.markdown("""
    This tool analyzes renewable energy project documents using AI to:
    - Extract key project information
    - Generate structured summaries
    - Identify important details
    """)
    
    st.markdown("### Supported File Types")
    st.markdown("- PDF (.pdf)")
    st.markdown("- Microsoft Word (.docx, .doc)")
    
    st.markdown("### API Status")
    try:
        health_check = requests.get(f"{FASTAPI_URL}/", timeout=5)
        if health_check.status_code == 200:
            st.success("Backend API is online")
        else:
            st.error("Backend API is not responding correctly")
    except:
        st.error("Backend API is offline")

st.title("📄 AI Document Analysis MVP")
st.markdown("Upload a renewable energy project document to extract key information and get an AI-powered analysis.")

uploaded_file = st.file_uploader(
    "Choose a document...",
    type=["pdf", "docx", "doc"],
    accept_multiple_files=False,
    help="Upload a PDF or Word document related to a renewable energy project."
)

process_button = st.button(
    "🔍 Analyze Document",
    disabled=(uploaded_file is None),
    help="Click to start AI analysis of the document"
)

if process_button and uploaded_file is not None:
    try:
        files = {"file": (uploaded_file.name, uploaded_file.getvalue(), uploaded_file.type)}
        response = requests.post(UPLOAD_ENDPOINT, files=files)
        
        if response.status_code == 200:
            task_info = response.json()
            results = poll_status(task_info["task_id"])
            
            if results["status"] == "completed":
                st.success("✅ Analysis complete!")
                
                tab1, tab2, tab3 = st.tabs(["📊 Project Info", "📝 Summary", "⚠️ Risk Analysis"])
                
                with tab1:
                    st.markdown("### Extracted Project Information")
                    format_project_info(results.get("project_info", {}), results.get("external_info", {}))
                
                with tab2:
                    st.markdown("### Document Summary")
                    format_summary(results.get("summary", {}))
                
                with tab3:
                    st.markdown("### Risk Analysis")
                    format_risk_flags(results.get("risk_flags", []))
        else:
            st.error("❌ Error starting document analysis")
            with st.expander("Error Details"):
                try:
                    error_detail = response.json().get("detail", response.text)
                    st.code(error_detail)
                except:
                    st.code(f"Status Code: {response.status_code}\nResponse: {response.text[:500]}...")
    
    except Exception as e:
        st.error(f"⚠️ Error: {str(e)}")

elif process_button and uploaded_file is None:
    st.warning("⚠️ Please upload a document first.")