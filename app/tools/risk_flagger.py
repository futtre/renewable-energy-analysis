from typing import List, Optional
from app.tools.extract_key_info import ProjectInfo

class RiskFlagger:
    """Tool for analyzing project information and flagging potential risks."""

    @staticmethod
    def _check_ppa_term_length(project_info: ProjectInfo) -> Optional[str]:
        """Check if PPA term length is potentially short."""
        if project_info.term_length_years is not None:
            # Convert to int if it's a string number
            term_length = int(str(project_info.term_length_years))
            if term_length < 15:
                return f"SHORT PPA TERM: PPA term length is {term_length} years, which is below the typical 15-year threshold"
        return None

    @staticmethod
    def _check_project_size(project_info: ProjectInfo) -> List[str]:
        """Check if project capacity is unusually small or large."""
        flags = []
        if project_info.capacity_mw is not None:
            capacity = float(project_info.capacity_mw)
            if capacity < 5:
                flags.append(f"SMALL PROJECT: Project capacity is only {capacity} MW, which may affect economies of scale and project viability")
            elif capacity < 20:
                flags.append(f"MEDIUM-SMALL PROJECT: Project capacity is {capacity} MW, which may have higher per-MW costs")
            elif capacity > 500:
                flags.append(f"LARGE PROJECT: Project capacity is {capacity} MW, which may have grid integration and interconnection challenges")
            
            # Check if project area size is provided for density calculation
            if project_info.project_area_size:
                # Try to extract numeric value from area size string
                try:
                    area_str = project_info.project_area_size.lower()
                    area_value = float(''.join(c for c in area_str if c.isdigit() or c == '.'))
                    if 'acre' in area_str:
                        density = capacity / area_value  # MW/acre
                        if density < 0.004:  # Less than 4 kW per acre
                            flags.append(f"LOW DENSITY: Project density is {density:.3f} MW/acre, which may indicate land use inefficiency")
                except ValueError:
                    pass  # Skip density check if area can't be parsed
        return flags

    @staticmethod
    def _check_missing_critical_info(project_info: ProjectInfo) -> List[str]:
        """Check for missing critical information."""
        flags = []
        critical_fields = [
            ("project_name", "Project name"),
            ("project_type", "Project type"),
            ("capacity_mw", "Project capacity"),
            ("location_address", "Project location"),
            ("developer_name", "Developer information"),
            ("purchaser_or_offtaker", "Offtaker information"),
            ("agreement_type", "Agreement type"),
            ("term_length_years", "PPA term length")
        ]
        
        for field, description in critical_fields:
            if getattr(project_info, field) is None:
                flags.append(f"MISSING INFO: {description} is not specified")
        
        return flags

    @staticmethod
    def _check_environmental_risks(project_info: ProjectInfo) -> List[str]:
        """Check for environmental and permitting risks."""
        flags = []
        
        # Check for environmental concerns
        if project_info.key_environmental_concerns:
            flags.extend([f"ENVIRONMENTAL CONCERN: {concern}" 
                        for concern in project_info.key_environmental_concerns])
            
            # Only flag missing mitigation if there are environmental concerns
            if project_info.mitigation_mentioned is False:
                flags.append("HIGH RISK - NO MITIGATION: Environmental concerns exist but mitigation measures are not mentioned")
        
        # Check for permitting status
        if not project_info.key_permits_mentioned:
            flags.append("PERMITTING RISK: No specific permits or approvals are mentioned")
        
        # Check for lead regulatory agency
        if not project_info.lead_regulatory_agency:
            flags.append("REGULATORY RISK: Lead regulatory agency is not identified")
            
        return flags

    @staticmethod
    def _check_contract_risks(project_info: ProjectInfo) -> List[str]:
        """Check for contract-related risks."""
        flags = []
        
        # Check liquidated damages provisions
        if project_info.liquidated_damages_mention is False:
            flags.append("CONTRACT RISK: Liquidated damages provisions are not mentioned, which may affect project's risk allocation")
            
        # Check environmental attributes ownership
        if not project_info.environmental_attributes_ownership:
            flags.append("UNCLEAR REC OWNERSHIP: Environmental attributes (RECs) ownership is not specified")
        elif "seller" in project_info.environmental_attributes_ownership.lower():
            flags.append("REC OWNERSHIP NOTE: Seller retains environmental attributes, which may affect project economics")
            
        # Check guaranteed output or availability
        if not project_info.guaranteed_output_or_availability:
            flags.append("PERFORMANCE RISK: No guaranteed output or availability metrics specified")
            
        # Check delivery point
        if not project_info.delivery_point:
            flags.append("DELIVERY RISK: Power delivery point is not specified")
            
        return flags

    @classmethod
    def analyze_project(cls, project_info: Optional[ProjectInfo]) -> List[str]:
        """
        Analyze project information and flag potential risks.

        Args:
            project_info: A Pydantic ProjectInfo object containing the extracted data,
                        or None if extraction failed.

        Returns:
            A list of strings, where each string represents a potential risk or flag.
            Returns an empty list if no risks are flagged or if input is None.
        """
        if not project_info:
            return []

        flags = []

        # Check PPA term length
        if ppa_flag := cls._check_ppa_term_length(project_info):
            flags.append(ppa_flag)

        # Check project size and density
        flags.extend(cls._check_project_size(project_info))

        # Add missing information flags
        flags.extend(cls._check_missing_critical_info(project_info))

        # Add environmental risk flags
        flags.extend(cls._check_environmental_risks(project_info))

        # Add contract risk flags
        flags.extend(cls._check_contract_risks(project_info))

        return flags 