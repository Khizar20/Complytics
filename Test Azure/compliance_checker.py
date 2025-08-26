"""
Compliance Checking Module

This module compares Azure AD configurations against compliance rules
and generates audit reports.
"""

import os
import json
import logging
from typing import List, Dict, Any, Optional
from jsonpath_ng import parse, Fields, Index
from jsonpath_ng.ext import parse as parse_ext

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ComplianceChecker:
    """
    Checks Azure AD configurations against compliance rules.
    """
    
    def __init__(self):
        """Initialize the compliance checker."""
        self.rules = []
        self.operators = {
            '==': self._equals,
            '!=': self._not_equals,
            '>=': self._greater_than_or_equal,
            '<=': self._less_than_or_equal,
            '>': self._greater_than,
            '<': self._less_than,
            'includes': self._includes,
            'not_includes': self._not_includes,
            'contains': self._contains,
            'not_contains': self._not_contains,
            'exists': self._exists,
            'not_exists': self._not_exists
        }
    
    def load_rules(self, filepath: str) -> bool:
        """
        Load compliance rules from a JSON file.
        
        Args:
            filepath (str): Path to the JSON file containing rules
            
        Returns:
            bool: True if rules loaded successfully, False otherwise
        """
        try:
            with open(filepath, 'r', encoding='utf-8') as file:
                self.rules = json.load(file)
            logger.info(f"Loaded {len(self.rules)} compliance rules from {filepath}")
            return True
        except Exception as e:
            logger.error(f"Error loading rules from {filepath}: {str(e)}")
            return False
    
    def _extract_value_from_config(self, config: Dict[str, Any], field_path: str) -> Any:
        """
        Extract a value from the configuration using JSONPath.
        
        Args:
            config (Dict): Azure AD configuration
            field_path (str): JSONPath expression
            
        Returns:
            Any: Extracted value or None if not found
        """
        try:
            jsonpath_expr = parse_ext(field_path)
            matches = [match.value for match in jsonpath_expr.find(config)]
            
            if matches:
                # Return the first match, or list if multiple matches
                return matches[0] if len(matches) == 1 else matches
            return None
            
        except Exception as e:
            logger.error(f"Error extracting value with path '{field_path}': {str(e)}")
            return None
    
    def _equals(self, actual: Any, expected: Any) -> bool:
        """Check if actual equals expected."""
        return actual == expected
    
    def _not_equals(self, actual: Any, expected: Any) -> bool:
        """Check if actual does not equal expected."""
        return actual != expected
    
    def _greater_than_or_equal(self, actual: Any, expected: Any) -> bool:
        """Check if actual is greater than or equal to expected."""
        try:
            return float(actual) >= float(expected)
        except (ValueError, TypeError):
            return False
    
    def _less_than_or_equal(self, actual: Any, expected: Any) -> bool:
        """Check if actual is less than or equal to expected."""
        try:
            return float(actual) <= float(expected)
        except (ValueError, TypeError):
            return False
    
    def _greater_than(self, actual: Any, expected: Any) -> bool:
        """Check if actual is greater than expected."""
        try:
            return float(actual) > float(expected)
        except (ValueError, TypeError):
            return False
    
    def _less_than(self, actual: Any, expected: Any) -> bool:
        """Check if actual is less than expected."""
        try:
            return float(actual) < float(expected)
        except (ValueError, TypeError):
            return False
    
    def _includes(self, actual: Any, expected: Any) -> bool:
        """Check if actual includes expected."""
        if isinstance(actual, (list, tuple)):
            return expected in actual
        elif isinstance(actual, str):
            return expected in actual
        return False
    
    def _not_includes(self, actual: Any, expected: Any) -> bool:
        """Check if actual does not include expected."""
        return not self._includes(actual, expected)
    
    def _contains(self, actual: Any, expected: Any) -> bool:
        """Check if actual contains expected."""
        if isinstance(actual, str):
            return expected in actual
        return False
    
    def _not_contains(self, actual: Any, expected: Any) -> bool:
        """Check if actual does not contain expected."""
        return not self._contains(actual, expected)
    
    def _exists(self, actual: Any, expected: Any) -> bool:
        """Check if the field exists and is not None/empty."""
        if actual is None:
            return False
        if isinstance(actual, (str, list, dict)) and not actual:
            return False
        return True
    
    def _not_exists(self, actual: Any, expected: Any) -> bool:
        """Check if the field does not exist or is None/empty."""
        return not self._exists(actual, expected)
    
    def _evaluate_rule(self, rule: Dict[str, Any], config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Evaluate a single compliance rule against the configuration.
        
        Args:
            rule (Dict): Compliance rule
            config (Dict): Azure AD configuration
            
        Returns:
            Dict: Evaluation result
        """
        rule_id = rule.get('rule_id', 'UNKNOWN')
        title = rule.get('title', 'Unknown Rule')
        operator = rule.get('operator', '==')
        expected_value = rule.get('value')
        field_path = rule.get('field', '')
        remediation = rule.get('remediation', 'No remediation steps provided.')
        
        # Extract actual value from config
        actual_value = self._extract_value_from_config(config, field_path)
        
        # Check if operator is supported
        if operator not in self.operators:
            logger.warning(f"Unsupported operator '{operator}' for rule {rule_id}")
            return {
                'rule_id': rule_id,
                'title': title,
                'status': 'ERROR',
                'actual': actual_value,
                'expected': expected_value,
                'error': f"Unsupported operator: {operator}",
                'remediation': remediation
            }
        
        # Evaluate the rule
        try:
            is_compliant = self.operators[operator](actual_value, expected_value)
            status = 'PASS' if is_compliant else 'FAIL'
            
            return {
                'rule_id': rule_id,
                'title': title,
                'status': status,
                'actual': actual_value,
                'expected': expected_value,
                'operator': operator,
                'remediation': remediation if status == 'FAIL' else None
            }
            
        except Exception as e:
            logger.error(f"Error evaluating rule {rule_id}: {str(e)}")
            return {
                'rule_id': rule_id,
                'title': title,
                'status': 'ERROR',
                'actual': actual_value,
                'expected': expected_value,
                'error': str(e),
                'remediation': remediation
            }
    
    def check_compliance(self, config: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Check Azure AD configuration against all loaded compliance rules.
        
        Args:
            config (Dict): Azure AD configuration from Graph API
            
        Returns:
            List[Dict]: List of compliance check results
        """
        if not self.rules:
            logger.warning("No compliance rules loaded. Use load_rules() first.")
            return []
        
        results = []
        logger.info(f"Checking compliance against {len(self.rules)} rules...")
        
        for rule in self.rules:
            result = self._evaluate_rule(rule, config)
            results.append(result)
            
            # Log the result
            status_emoji = "✅" if result['status'] == 'PASS' else "❌" if result['status'] == 'FAIL' else "⚠️"
            logger.info(f"{status_emoji} {rule.get('rule_id')}: {result['status']}")
        
        return results
    
    def generate_summary(self, results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Generate a summary of compliance check results.
        
        Args:
            results (List[Dict]): Compliance check results
            
        Returns:
            Dict: Summary statistics
        """
        total = len(results)
        passed = len([r for r in results if r['status'] == 'PASS'])
        failed = len([r for r in results if r['status'] == 'FAIL'])
        errors = len([r for r in results if r['status'] == 'ERROR'])
        
        compliance_rate = (passed / total * 100) if total > 0 else 0
        
        return {
            'total_rules': total,
            'passed': passed,
            'failed': failed,
            'errors': errors,
            'compliance_rate': round(compliance_rate, 2),
            'summary': f"{passed}/{total} rules passed ({compliance_rate:.1f}% compliance)"
        }
    
    def save_audit_report(self, results: List[Dict[str, Any]], filepath: str = "compliance_audit_report.json"):
        """
        Save compliance audit report to a JSON file.
        
        Args:
            results (List[Dict]): Compliance check results
            filepath (str): Path to save the report
        """
        try:
            summary = self.generate_summary(results)
            report = {
                'summary': summary,
                'results': results,
                'timestamp': str(__import__('datetime').datetime.now())
            }
            
            with open(filepath, 'w', encoding='utf-8') as file:
                json.dump(report, file, indent=2, ensure_ascii=False)
            
            logger.info(f"Saved audit report to {filepath}")
            
        except Exception as e:
            logger.error(f"Error saving audit report to {filepath}: {str(e)}")
            raise


def main():
    """
    Main function to demonstrate compliance checking.
    """
    try:
        # Initialize the checker
        checker = ComplianceChecker()
        
        # Load rules
        if not checker.load_rules("compliance_rules.json"):
            print("❌ Failed to load compliance rules. Run compliance_extractor.py first.")
            return
        
        # Load Azure AD configuration (you would get this from your Graph API client)
        # For demonstration, we'll use a sample configuration
        sample_config = {
            "authenticationMethodsPolicy": {
                "authenticationMethodConfigurations": [
                    {
                        "id": "MicrosoftAuthenticator",
                        "state": "enabled"
                    },
                    {
                        "id": "Sms",
                        "state": "disabled"
                    }
                ]
            }
        }
        
        # Check compliance
        results = checker.check_compliance(sample_config)
        
        # Generate and display summary
        summary = checker.generate_summary(results)
        print(f"\n📊 Compliance Summary:")
        print(f"  {summary['summary']}")
        print(f"  Passed: {summary['passed']}")
        print(f"  Failed: {summary['failed']}")
        print(f"  Errors: {summary['errors']}")
        
        # Save audit report
        checker.save_audit_report(results)
        
        print(f"\n✅ Compliance check completed! Check compliance_audit_report.json for details.")
        
    except Exception as e:
        logger.error(f"Error in compliance checking: {str(e)}")
        print(f"❌ Error: {str(e)}")


if __name__ == "__main__":
    main() 