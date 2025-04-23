from typing import List, Optional, Any, Dict
from pathlib import Path
import yaml
from app.tools.extract_key_info import ProjectInfo

class RiskFlagger:
    """Tool for analyzing project information and flagging potential risks using configurable rules."""

    def __init__(self):
        self.rules = self._load_rules()

    def _load_rules(self) -> List[Dict[str, Any]]:
        """Load risk assessment rules from YAML configuration."""
        rules_path = Path(__file__).parent.parent / 'config' / 'risk_rules.yaml'
        try:
            with open(rules_path, 'r') as f:
                return yaml.safe_load(f).get('rules', [])
        except Exception as e:
            print(f"Warning: Could not load rules configuration: {e}")
            return []

    def _check_condition(self, value: Any, rule: Dict[str, Any], field_name: str) -> bool:
        """Check if a value matches the condition specified in the rule."""
        condition = rule['condition']
        rule_value = rule.get('value')

        if value is None:
            return condition == 'is_missing'

        match condition:
            case 'is_present':
                return bool(value)
            case 'is_missing':
                return False
            case 'is_true':
                return bool(value) is True
            case 'is_false':
                return bool(value) is False
            case 'less_than':
                try:
                    return float(str(value)) < rule_value
                except (ValueError, TypeError):
                    return False
            case 'contains_any':
                return (isinstance(value, str) and isinstance(rule_value, list) and 
                       any(keyword.lower() in value.lower() for keyword in rule_value))
            case 'not_contains_all':
                return (isinstance(value, str) and isinstance(rule_value, list) and 
                       not all(keyword.lower() in value.lower() for keyword in rule_value))
            case 'parsing_failed':
                try:
                    if field_name == 'term_length_years':
                        int(str(value))
                    elif field_name == 'capacity_mw':
                        float(str(value))
                    return False
                except (ValueError, TypeError):
                    return True
        return False

    def _format_flag_description(self, rule: Dict[str, Any], project_info: ProjectInfo) -> str:
        """Format the flag description with actual values from the project info."""
        description = rule['description']
        field_name = rule['field']
        field_value = getattr(project_info, field_name, None)

        # Handle special formatting cases
        if '{value}' in description:
            description = description.replace('{value}', str(rule.get('value', '')))
        if isinstance(field_value, list):
            if '{count}' in description:
                description = description.replace('{count}', str(len(field_value)))
            if '{details}' in description:
                description = description.replace('{details}', ', '.join(str(item) for item in field_value))

        return description

    def _should_apply_rule(self, rule: Dict[str, Any], project_info: ProjectInfo) -> bool:
        """Check if a rule should be applied based on its dependencies."""
        depends_on = rule.get('depends_on_field')
        if not depends_on:
            return True
            
        dependent_value = getattr(project_info, depends_on, None)
        if depends_on == 'agreement_type':
            return dependent_value is not None and 'ppa' in str(dependent_value).lower()
        return dependent_value is not None

    def analyze_project(self, project_info: Optional[ProjectInfo]) -> List[str]:
        """
        Analyze project information using configured rules and flag potential risks.

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
        
        for rule in self.rules:
            # Skip rule if dependencies aren't met
            if not self._should_apply_rule(rule, project_info):
                continue

            field_name = rule['field']
            field_value = getattr(project_info, field_name, None)

            if self._check_condition(field_value, rule, field_name):
                flag_description = self._format_flag_description(rule, project_info)
                flags.append(f"{rule['id']}: {flag_description}")

        return flags 