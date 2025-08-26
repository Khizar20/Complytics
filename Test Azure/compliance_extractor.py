"""
Compliance Rule Extraction Module

This module uses Gemini 2.0 Flash to extract Azure AD compliance rules
from compliance documents (PDF or text) and convert them to JSON format.
"""

import os
import json
import logging
from typing import List, Dict, Any, Optional
from pathlib import Path

import google.generativeai as genai
import PyPDF2
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ComplianceExtractor:
    """
    Extracts Azure AD compliance rules from compliance documents using Gemini 2.0 Flash.
    """
    
    def __init__(self, api_key: str = None):
        """
        Initialize the compliance extractor with Gemini API.
        
        Args:
            api_key (str): Google API key for Gemini. If None, uses environment variable.
        """
        self.api_key = api_key or os.getenv('GOOGLE_API_KEY')
        if not self.api_key:
            raise ValueError("Google API key is required. Set GOOGLE_API_KEY environment variable.")
        
        # Configure Gemini
        genai.configure(api_key=self.api_key)
        self.model = genai.GenerativeModel('gemini-2.0-flash')
        
        # Define the rule extraction prompt
        self.extraction_prompt = """
You are an expert in Azure AD compliance and security. Your task is to extract actionable Azure AD compliance rules from the given compliance document.

For each compliance requirement that relates to Azure AD, create a JSON rule with the following structure:

{
  "rule_id": "UNIQUE_RULE_ID",
  "title": "Clear, concise title",
  "description": "Detailed description of the requirement",
  "graph_path": "/relevant/graph/api/path",
  "field": "json.path.to.field",
  "operator": "==",
  "value": "expected_value",
  "severity": "high|medium|low",
  "control_id": "ORIGINAL_CONTROL_ID",
  "remediation": "Step-by-step remediation instructions"
}

Rules for extraction:
1. Only extract rules that can be verified against Azure AD Graph API
2. Use appropriate Graph API paths (e.g., /policies/authenticationMethodsPolicy for MFA)
3. Use JSONPath notation for field access (e.g., "authenticationMethodConfigurations[?(@.id=='MicrosoftAuthenticator')].state")
4. Use appropriate operators: ==, !=, >=, <=, includes, not_includes
5. Provide clear remediation steps
6. Include original control IDs from the compliance framework

Return only the JSON array of rules, no additional text.
"""
    
    def extract_text_from_pdf(self, pdf_path: str) -> str:
        """
        Extract text content from a PDF file.
        
        Args:
            pdf_path (str): Path to the PDF file
            
        Returns:
            str: Extracted text content
        """
        try:
            with open(pdf_path, 'rb') as file:
                pdf_reader = PyPDF2.PdfReader(file)
                text = ""
                for page in pdf_reader.pages:
                    text += page.extract_text() + "\n"
                return text
        except Exception as e:
            logger.error(f"Error extracting text from PDF {pdf_path}: {str(e)}")
            raise
    
    def extract_rules_from_document(self, document_path: str) -> List[Dict[str, Any]]:
        """
        Extract compliance rules from a document using Gemini 2.0 Flash.
        
        Args:
            document_path (str): Path to the compliance document (PDF or text)
            
        Returns:
            List[Dict]: List of extracted compliance rules
        """
        try:
            # Extract text from document
            if document_path.lower().endswith('.pdf'):
                text_content = self.extract_text_from_pdf(document_path)
            else:
                with open(document_path, 'r', encoding='utf-8') as file:
                    text_content = file.read()
            
            # Truncate content if too long (Gemini has limits)
            if len(text_content) > 30000:
                text_content = text_content[:30000] + "\n[Content truncated for processing]"
            
            # Create the full prompt
            full_prompt = f"{self.extraction_prompt}\n\nCompliance Document Content:\n{text_content}"
            
            # Generate response using Gemini
            response = self.model.generate_content(full_prompt)
            
            # Parse the response
            try:
                # Extract JSON from the response
                response_text = response.text.strip()
                
                # Find JSON array in the response
                start_idx = response_text.find('[')
                end_idx = response_text.rfind(']') + 1
                
                if start_idx != -1 and end_idx != -1:
                    json_str = response_text[start_idx:end_idx]
                    rules = json.loads(json_str)
                    
                    logger.info(f"Successfully extracted {len(rules)} rules from {document_path}")
                    return rules
                else:
                    logger.warning("No JSON array found in Gemini response")
                    return []
                    
            except json.JSONDecodeError as e:
                logger.error(f"Error parsing JSON from Gemini response: {str(e)}")
                logger.error(f"Response: {response.text}")
                return []
                
        except Exception as e:
            logger.error(f"Error extracting rules from {document_path}: {str(e)}")
            return []
    
    def extract_rules_from_framework_folder(self, framework_folder: str = "compliance_frameworks") -> List[Dict[str, Any]]:
        """
        Extract rules from all documents in the compliance frameworks folder.
        
        Args:
            framework_folder (str): Path to the compliance frameworks folder
            
        Returns:
            List[Dict]: Combined list of all extracted rules
        """
        all_rules = []
        framework_path = Path(framework_folder)
        
        if not framework_path.exists():
            logger.error(f"Compliance frameworks folder not found: {framework_folder}")
            return all_rules
        
        # Process all files in the folder
        for file_path in framework_path.glob("*"):
            if file_path.is_file() and (file_path.suffix.lower() in ['.pdf', '.txt']):
                logger.info(f"Processing compliance document: {file_path}")
                rules = self.extract_rules_from_document(str(file_path))
                all_rules.extend(rules)
        
        # Remove duplicates based on rule_id
        unique_rules = {}
        for rule in all_rules:
            rule_id = rule.get('rule_id')
            if rule_id and rule_id not in unique_rules:
                unique_rules[rule_id] = rule
        
        logger.info(f"Total unique rules extracted: {len(unique_rules)}")
        return list(unique_rules.values())
    
    def save_rules_to_file(self, rules: List[Dict[str, Any]], filepath: str = "compliance_rules.json"):
        """
        Save extracted rules to a JSON file.
        
        Args:
            rules (List[Dict]): List of compliance rules
            filepath (str): Path to save the JSON file
        """
        try:
            with open(filepath, 'w', encoding='utf-8') as file:
                json.dump(rules, file, indent=2, ensure_ascii=False)
            logger.info(f"Saved {len(rules)} rules to {filepath}")
        except Exception as e:
            logger.error(f"Error saving rules to {filepath}: {str(e)}")
            raise


def main():
    """
    Main function to demonstrate compliance rule extraction.
    """
    try:
        # Initialize the extractor
        extractor = ComplianceExtractor()
        
        # Extract rules from all compliance documents
        logger.info("Starting compliance rule extraction...")
        rules = extractor.extract_rules_from_framework_folder()
        
        if rules:
            # Save rules to file
            extractor.save_rules_to_file(rules)
            
            print(f"\n✅ Successfully extracted {len(rules)} compliance rules!")
            print("\nSample rules:")
            for i, rule in enumerate(rules[:3]):  # Show first 3 rules
                print(f"\nRule {i+1}:")
                print(f"  ID: {rule.get('rule_id')}")
                print(f"  Title: {rule.get('title')}")
                print(f"  Severity: {rule.get('severity')}")
                print(f"  Control ID: {rule.get('control_id')}")
        else:
            print("❌ No rules were extracted. Check the compliance documents and API key.")
            
    except Exception as e:
        logger.error(f"Error in compliance extraction: {str(e)}")
        print(f"❌ Error: {str(e)}")


if __name__ == "__main__":
    main() 