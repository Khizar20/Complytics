"""
Example usage of the Azure Graph API Client

This script demonstrates how to use the AzureGraphClient class
to fetch specific configuration data from Microsoft Graph API.
"""

import json
from azure_graph_client import AzureGraphClient

def example_usage():
    """
    Example usage of the Azure Graph API client.
    """
    try:
        # Initialize the client
        client = AzureGraphClient()
        
        print("🔐 Azure AD Graph API Client Example")
        print("=" * 50)
        
        # Example 1: Get Conditional Access Policies
        print("\n📋 Example 1: Conditional Access Policies")
        print("-" * 40)
        cap_data = client.get_conditional_access_policies()
        if cap_data:
            print(f"✅ Retrieved {len(cap_data.get('value', []))} conditional access policies")
            print(json.dumps(cap_data, indent=2, default=str))
        else:
            print("❌ Failed to retrieve conditional access policies")
        
        # Example 2: Get Authentication Methods Policy
        print("\n🔐 Example 2: Authentication Methods Policy")
        print("-" * 40)
        amp_data = client.get_authentication_methods_policy()
        if amp_data:
            print("✅ Retrieved authentication methods policy")
            print(json.dumps(amp_data, indent=2, default=str))
        else:
            print("❌ Failed to retrieve authentication methods policy")
        
        # Example 3: Get Users (first 5)
        print("\n👥 Example 3: Users (first 5)")
        print("-" * 40)
        users_data = client.get_users(top=5)
        if users_data:
            print(f"✅ Retrieved {len(users_data.get('value', []))} users")
            print(json.dumps(users_data, indent=2, default=str))
        else:
            print("❌ Failed to retrieve users")
        
        # Example 4: Custom endpoint
        print("\n🔧 Example 4: Custom Endpoint - Directory Roles")
        print("-" * 40)
        custom_data = client.fetch_graph_config("/directoryRoles")
        if custom_data:
            print(f"✅ Retrieved {len(custom_data.get('value', []))} directory roles")
            print(json.dumps(custom_data, indent=2, default=str))
        else:
            print("❌ Failed to retrieve directory roles")
        
        # Example 5: Get all configurations at once
        print("\n📊 Example 5: All Configurations")
        print("-" * 40)
        all_configs = client.get_all_configurations()
        if all_configs:
            print(f"✅ Retrieved {len(all_configs)} configuration types")
            for config_type, data in all_configs.items():
                print(f"  - {config_type}: {len(data.get('value', [])) if isinstance(data, dict) and 'value' in data else 'N/A'} items")
        else:
            print("❌ Failed to retrieve configurations")
            
    except Exception as e:
        print(f"❌ Error: {str(e)}")

if __name__ == "__main__":
    example_usage() 