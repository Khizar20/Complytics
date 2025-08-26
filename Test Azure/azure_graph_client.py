"""
Azure AD Graph API Client Module

This module provides functionality to authenticate with Azure AD using MSAL
and query Microsoft Graph API for configuration settings.
"""

import os
import json
import logging
from typing import Dict, Any, Optional
from urllib.parse import urljoin

import msal
import requests
from dotenv import load_dotenv

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

class AzureGraphClient:
    """
    Client for interacting with Microsoft Graph API using Azure AD authentication.
    """
    
    def __init__(self):
        """Initialize the Azure Graph client with configuration from environment variables."""
        self.client_id = os.getenv('AZURE_CLIENT_ID')
        self.tenant_id = os.getenv('AZURE_TENANT_ID')
        self.client_secret = os.getenv('AZURE_CLIENT_SECRET')
        
        if not all([self.client_id, self.tenant_id, self.client_secret]):
            raise ValueError(
                "Missing required environment variables. "
                "Please ensure AZURE_CLIENT_ID, AZURE_TENANT_ID, and AZURE_CLIENT_SECRET are set in .env file"
            )
        
        # Microsoft Graph API endpoints
        self.authority = f"https://login.microsoftonline.com/{self.tenant_id}"
        self.graph_endpoint = "https://graph.microsoft.com/v1.0"
        
        # Initialize MSAL application
        self.app = msal.ConfidentialClientApplication(
            client_id=self.client_id,
            client_credential=self.client_secret,
            authority=self.authority
        )
        
        # Scopes for Microsoft Graph API
        self.scopes = ["https://graph.microsoft.com/.default"]
    
    def get_graph_token(self) -> Optional[str]:
        """
        Obtain an access token for Microsoft Graph API using client credentials flow.
        
        Returns:
            str: Access token if successful, None otherwise
        """
        try:
            # Get token using client credentials flow
            result = self.app.acquire_token_for_client(scopes=self.scopes)
            
            if "access_token" in result:
                logger.info("Successfully obtained access token")
                return result["access_token"]
            else:
                logger.error(f"Failed to acquire token: {result.get('error_description', 'Unknown error')}")
                return None
                
        except Exception as e:
            logger.error(f"Error obtaining access token: {str(e)}")
            return None
    
    def fetch_graph_config(self, endpoint: str) -> Optional[Dict[str, Any]]:
        """
        Fetch configuration data from Microsoft Graph API.
        
        Args:
            endpoint (str): The Graph API endpoint to query (e.g., '/conditionalAccess/policies')
            
        Returns:
            dict: JSON response from the API, or None if failed
        """
        token = self.get_graph_token()
        if not token:
            logger.error("Failed to obtain access token")
            return None
        
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }
        
        # Ensure the endpoint starts with / and construct the full URL
        if not endpoint.startswith('/'):
            endpoint = '/' + endpoint
        url = f"{self.graph_endpoint}{endpoint}"
        
        try:
            logger.info(f"Fetching data from: {url}")
            response = requests.get(url, headers=headers)
            
            if response.status_code == 200:
                data = response.json()
                logger.info(f"Successfully fetched data from {endpoint}")
                return data
            else:
                logger.error(f"API request failed with status {response.status_code}: {response.text}")
                return None
                
        except Exception as e:
            logger.error(f"Error fetching data from {endpoint}: {str(e)}")
            return None
    
    def get_conditional_access_policies(self) -> Optional[Dict[str, Any]]:
        """
        Fetch Conditional Access Policies from Microsoft Graph API.
        
        Returns:
            dict: Conditional access policies data
        """
        return self.fetch_graph_config("/conditionalAccess/policies")
    
    def get_authentication_methods_policy(self) -> Optional[Dict[str, Any]]:
        """
        Fetch Authentication Methods Policy from Microsoft Graph API.
        
        Returns:
            dict: Authentication methods policy data
        """
        return self.fetch_graph_config("/policies/authenticationMethodsPolicy")
    
    def get_password_policies(self) -> Optional[Dict[str, Any]]:
        """
        Fetch Password Policies from Microsoft Graph API.
        
        Returns:
            dict: Password policies data
        """
        return self.fetch_graph_config("/policies/authenticationFlowsPolicy")
    
    def get_users(self, top: int = 10) -> Optional[Dict[str, Any]]:
        """
        Fetch users from Microsoft Graph API.
        
        Args:
            top (int): Number of users to retrieve (default: 10)
            
        Returns:
            dict: Users data
        """
        return self.fetch_graph_config(f"/users?$top={top}")
    
    def get_all_configurations(self) -> Dict[str, Any]:
        """
        Fetch all configuration settings from Microsoft Graph API.
        
        Returns:
            dict: Dictionary containing all configuration data
        """
        configurations = {}
        
        # Fetch Conditional Access Policies
        logger.info("Fetching Conditional Access Policies...")
        cap_data = self.get_conditional_access_policies()
        if cap_data:
            configurations['conditional_access_policies'] = cap_data
        
        # Fetch Authentication Methods Policy
        logger.info("Fetching Authentication Methods Policy...")
        amp_data = self.get_authentication_methods_policy()
        if amp_data:
            configurations['authentication_methods_policy'] = amp_data
        
        # Fetch Password Policies
        logger.info("Fetching Password Policies...")
        pp_data = self.get_password_policies()
        if pp_data:
            configurations['password_policies'] = pp_data
        
        # Fetch Users (optional)
        logger.info("Fetching Users...")
        users_data = self.get_users()
        if users_data:
            configurations['users'] = users_data
        
        return configurations


def main():
    """
    Main function to demonstrate the Azure Graph API client functionality.
    """
    try:
        # Initialize the client
        client = AzureGraphClient()
        
        # Fetch all configurations
        logger.info("Starting Azure AD configuration fetch...")
        configurations = client.get_all_configurations()
        
        # Print results in JSON format
        print("\n" + "="*50)
        print("AZURE AD CONFIGURATION RESULTS")
        print("="*50)
        
        for config_type, data in configurations.items():
            print(f"\n{config_type.upper().replace('_', ' ')}:")
            print("-" * 30)
            print(json.dumps(data, indent=2, default=str))
        
        if not configurations:
            print("No configuration data was retrieved. Please check your permissions and credentials.")
        
    except ValueError as e:
        logger.error(f"Configuration error: {e}")
        print(f"Configuration error: {e}")
        print("Please ensure all required environment variables are set in your .env file.")
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        print(f"An error occurred: {str(e)}")


if __name__ == "__main__":
    main() 