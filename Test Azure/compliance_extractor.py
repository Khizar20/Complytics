"""
Compliance Rule Extraction Module

This module uses Gemini 2.0 Flash to extract Azure AD compliance rules
from compliance documents (PDF or text) and convert them to JSON format.
"""

import os
import json
import logging
from typing import List, Dict, Any, Optional, Tuple
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
    
    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize the compliance extractor with Gemini API.
        
        Args:
            api_key (str): Google API key for Gemini. If None, uses environment variable.
        """
        primary_from_env = os.getenv("GOOGLE_API_KEY1")
        fallback_from_env = os.getenv("GOOGLE_API_KEY2")

        self._gemini_keys: List[str] = []
        for candidate in (api_key, primary_from_env, fallback_from_env):
            if candidate:
                value = candidate.strip()
                if value and value not in self._gemini_keys:
                    self._gemini_keys.append(value)

        if not self._gemini_keys:
            raise ValueError("Google API key is required. Set GOOGLE_API_KEY1 (and optionally GOOGLE_API_KEY2) environment variables.")

        self._active_key_index: Optional[int] = None
        self.model: Optional[genai.GenerativeModel] = None
        self._ensure_model_initialized()

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

    def _configure_model_for_index(self, index: int) -> bool:
        if index < 0 or index >= len(self._gemini_keys):
            return False
        key = self._gemini_keys[index]
        if not key:
            return False
        try:
            genai.configure(api_key=key)
            self.model = genai.GenerativeModel('gemini-2.0-flash')
            self._active_key_index = index
            logger.info("Gemini configured successfully with key #%d", index + 1)
            return True
        except Exception as exc:
            logger.warning("Failed to configure Gemini with key #%d: %s", index + 1, exc)
            self.model = None
            return False

    def _ensure_model_initialized(self) -> bool:
        if self.model is not None:
            return True
        for idx in range(len(self._gemini_keys)):
            if self._configure_model_for_index(idx):
                return True
        return False

    def _switch_to_fallback_key(self) -> bool:
        if len(self._gemini_keys) <= 1:
            return False
        current = self._active_key_index
        for idx in range(len(self._gemini_keys)):
            if idx == current:
                continue
            if self._configure_model_for_index(idx):
                logger.info("Gemini failover succeeded using key #%d", idx + 1)
                return True
        logger.warning("Gemini failover failed: no alternate API keys succeeded")
        return False

    def _generate_with_gemini(self, prompt: str) -> Tuple[Optional[str], Optional[str]]:
        if not self._ensure_model_initialized():
            return None, "No Gemini API key configured"

        attempts = max(1, len(self._gemini_keys) or 1)
        last_error: Optional[str] = None
        for _ in range(attempts):
            active_index = (self._active_key_index or 0) + 1 if self._active_key_index is not None else None
            try:
                response = self.model.generate_content(prompt)  # type: ignore[call-arg]
                text = (getattr(response, "text", "") or "").strip()
                if text:
                    return text, None
                logger.warning(
                    "Gemini returned an empty response using key #%s",
                    active_index if active_index is not None else "unknown",
                )
                last_error = "Empty response"
            except Exception as exc:
                logger.warning(
                    "Gemini generation failed with key #%s: %s",
                    active_index if active_index is not None else "unknown",
                    exc,
                )
                last_error = str(exc)
            finally:
                self.model = None

            if not self._switch_to_fallback_key():
                break

        return None, last_error
    
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
            
            # Generate response using Gemini with fallback keys
            response_text, error = self._generate_with_gemini(full_prompt)
            if not response_text:
                logger.error(f"Gemini generation failed for {document_path}: {error}")
                return []
            
            # Parse the response
            try:
                # Extract JSON from the response
                response_text = response_text.strip()
                
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
                logger.error(f"Response: {response_text}")
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