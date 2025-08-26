"""
Integrated Compliance Auditor

This module combines Azure AD configuration fetching with compliance
rule extraction and checking to provide a complete compliance audit solution.
"""

import os
import json
import logging
from typing import Dict, Any, List
from datetime import datetime

from azure_graph_client import AzureGraphClient
from compliance_extractor import ComplianceExtractor
from compliance_checker import ComplianceChecker

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ComplianceAuditor:
    """
    Integrated compliance auditor that fetches Azure AD configuration,
    extracts compliance rules, and performs compliance checks.
    """
    
    def __init__(self, google_api_key: str = None):
        """
        Initialize the compliance auditor.
        
        Args:
            google_api_key (str): Google API key for Gemini. If None, uses environment variable.
        """
        self.azure_client = AzureGraphClient()
        self.extractor = ComplianceExtractor(google_api_key)
        self.checker = ComplianceChecker()
        
    def extract_compliance_rules(self, framework_folder: str = "compliance_frameworks") -> List[Dict[str, Any]]:
        """
        Extract compliance rules from compliance documents.
        
        Args:
            framework_folder (str): Path to compliance frameworks folder
            
        Returns:
            List[Dict]: Extracted compliance rules
        """
        logger.info("Extracting compliance rules from documents...")
        rules = self.extractor.extract_rules_from_framework_folder(framework_folder)
        
        if rules:
            self.extractor.save_rules_to_file(rules)
            logger.info(f"Extracted {len(rules)} compliance rules")
        else:
            logger.warning("No compliance rules were extracted")
            
        return rules
    
    def fetch_azure_configuration(self) -> Dict[str, Any]:
        """
        Fetch Azure AD configuration using the Graph API client.
        
        Returns:
            Dict: Azure AD configuration
        """
        logger.info("Fetching Azure AD configuration...")
        
        try:
            # Get all configurations from Azure AD
            configurations = self.azure_client.get_all_configurations()
            
            if not configurations:
                logger.warning("No Azure AD configuration was retrieved")
                return {}
            
            logger.info(f"Retrieved {len(configurations)} configuration sections")
            return configurations
            
        except Exception as e:
            logger.error(f"Error fetching Azure AD configuration: {str(e)}")
            return {}
    
    def perform_compliance_audit(self, 
                                extract_rules: bool = True,
                                rules_file: str = "compliance_rules.json") -> Dict[str, Any]:
        """
        Perform a complete compliance audit.
        
        Args:
            extract_rules (bool): Whether to extract rules from documents
            rules_file (str): Path to existing rules file (if extract_rules=False)
            
        Returns:
            Dict: Complete audit results
        """
        audit_results = {
            'timestamp': datetime.now().isoformat(),
            'azure_configuration': {},
            'compliance_rules': [],
            'compliance_results': [],
            'summary': {}
        }
        
        try:
            # Step 1: Extract compliance rules (if requested)
            if extract_rules:
                logger.info("Step 1: Extracting compliance rules...")
                rules = self.extract_compliance_rules()
                audit_results['compliance_rules'] = rules
            else:
                # Load existing rules
                if os.path.exists(rules_file):
                    with open(rules_file, 'r') as f:
                        rules = json.load(f)
                    audit_results['compliance_rules'] = rules
                    logger.info(f"Loaded {len(rules)} existing compliance rules")
                else:
                    logger.error(f"Rules file not found: {rules_file}")
                    return audit_results
            
            # Step 2: Fetch Azure AD configuration
            logger.info("Step 2: Fetching Azure AD configuration...")
            azure_config = self.fetch_azure_configuration()
            audit_results['azure_configuration'] = azure_config
            
            # Step 3: Load rules into checker
            logger.info("Step 3: Loading compliance rules...")
            if not self.checker.load_rules(rules_file):
                logger.error("Failed to load compliance rules")
                return audit_results
            
            # Step 4: Perform compliance checks
            logger.info("Step 4: Performing compliance checks...")
            compliance_results = self.checker.check_compliance(azure_config)
            audit_results['compliance_results'] = compliance_results
            
            # Step 5: Generate summary
            logger.info("Step 5: Generating audit summary...")
            summary = self.checker.generate_summary(compliance_results)
            audit_results['summary'] = summary
            
            # Step 6: Save comprehensive audit report
            audit_filename = f"comprehensive_audit_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            with open(audit_filename, 'w', encoding='utf-8') as f:
                json.dump(audit_results, f, indent=2, ensure_ascii=False)
            
            logger.info(f"Comprehensive audit report saved to: {audit_filename}")
            
            return audit_results
            
        except Exception as e:
            logger.error(f"Error during compliance audit: {str(e)}")
            return audit_results
    
    def print_audit_summary(self, audit_results: Dict[str, Any]):
        """
        Print a formatted summary of the audit results.
        
        Args:
            audit_results (Dict): Complete audit results
        """
        print("\n" + "="*60)
        print("🔐 COMPREHENSIVE COMPLIANCE AUDIT REPORT")
        print("="*60)
        
        # Azure AD Configuration Summary
        azure_config = audit_results.get('azure_configuration', {})
        print(f"\n📊 Azure AD Configuration:")
        print(f"  Configuration sections: {len(azure_config)}")
        for section in azure_config.keys():
            print(f"    - {section}")
        
        # Compliance Rules Summary
        rules = audit_results.get('compliance_rules', [])
        print(f"\n📋 Compliance Rules:")
        print(f"  Total rules: {len(rules)}")
        
        # Compliance Results Summary
        summary = audit_results.get('summary', {})
        print(f"\n✅ Compliance Results:")
        print(f"  {summary.get('summary', 'No results')}")
        print(f"  Passed: {summary.get('passed', 0)}")
        print(f"  Failed: {summary.get('failed', 0)}")
        print(f"  Errors: {summary.get('errors', 0)}")
        print(f"  Compliance Rate: {summary.get('compliance_rate', 0)}%")
        
        # Detailed Results
        results = audit_results.get('compliance_results', [])
        if results:
            print(f"\n📝 Detailed Results:")
            for result in results:
                status_emoji = "✅" if result['status'] == 'PASS' else "❌" if result['status'] == 'FAIL' else "⚠️"
                print(f"  {status_emoji} {result.get('rule_id', 'UNKNOWN')}: {result.get('title', 'Unknown')}")
                if result['status'] == 'FAIL':
                    print(f"      Expected: {result.get('expected')} | Actual: {result.get('actual')}")
                    print(f"      Remediation: {result.get('remediation', 'No remediation provided')}")
        
        print("\n" + "="*60)


def main():
    """
    Main function to demonstrate the complete compliance audit process.
    """
    try:
        # Initialize the auditor
        auditor = ComplianceAuditor()
        
        print("🔐 Starting Comprehensive Compliance Audit...")
        print("This will:")
        print("1. Extract compliance rules from documents using Gemini 2.0 Flash")
        print("2. Fetch Azure AD configuration via Graph API")
        print("3. Perform compliance checks")
        print("4. Generate comprehensive audit report")
        
        # Perform the audit
        audit_results = auditor.perform_compliance_audit(extract_rules=True)
        
        # Print summary
        auditor.print_audit_summary(audit_results)
        
        print(f"\n✅ Comprehensive compliance audit completed!")
        print("Check the generated JSON files for detailed results.")
        
    except Exception as e:
        logger.error(f"Error in compliance audit: {str(e)}")
        print(f"❌ Error: {str(e)}")


if __name__ == "__main__":
    main() 