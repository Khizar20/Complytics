from fastapi import APIRouter, HTTPException, Depends, status, Query
from fastapi.responses import Response
from pydantic import BaseModel, Field
from typing import Optional, List
from utils.security import get_current_user
from schemas.users import UserInDB

import msal
import requests
from datetime import datetime, timedelta
from db import database
import base64
import os
import json
import csv
import io
from bson import ObjectId


router = APIRouter()


class AzureCredentials(BaseModel):
    clientId: str = Field(..., min_length=1)
    clientSecret: str = Field(..., min_length=1)
    tenantId: str = Field(..., min_length=1)


def _encrypt_credentials(credentials: str) -> str:
    """Simple base64 encoding for demo - in production use proper encryption"""
    return base64.b64encode(credentials.encode()).decode()


def _decrypt_credentials(encrypted: str) -> str:
    """Simple base64 decoding for demo - in production use proper decryption"""
    return base64.b64decode(encrypted.encode()).decode()


def _test_azure_connection(client_id: str, client_secret: str, tenant_id: str) -> Optional[str]:
    authority = f"https://login.microsoftonline.com/{tenant_id}"
    app = msal.ConfidentialClientApplication(
        client_id=client_id,
        client_credential=client_secret,
        authority=authority,
    )
    scopes = ["https://graph.microsoft.com/.default"]
    result = app.acquire_token_for_client(scopes=scopes)
    if "access_token" in result:
        return result["access_token"]
    error_description = result.get("error_description") or result.get("error") or "Unknown error"
    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail=f"Azure AD authentication failed: {error_description}",
    )


def _get_azure_graph_data(access_token: str, endpoint: str):
    """Fetch data from Microsoft Graph API"""
    headers = {
        'Authorization': f'Bearer {access_token}',
        'Content-Type': 'application/json'
    }
    
    try:
        response = requests.get(f"https://graph.microsoft.com/v1.0{endpoint}", headers=headers)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch data from Azure Graph API: {str(e)}"
        )


def _project_root_dir() -> str:
    # routes/azure.py -> routes -> Complytics Backend -> project root
    return os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))


def _load_iso_rules() -> list:
    """Load ISO 27017 rules from iso_27017_rules.json."""
    try:
        root = _project_root_dir()
        iso_path = os.path.join(root, 'Test Azure', 'iso_27017_rules.json')
        with open(iso_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return data
    except Exception:
        return []


def _load_iso_graph_paths() -> set:
    """Load unique Graph API paths from iso_27017_rules.json."""
    try:
        rules = _load_iso_rules()
        paths = set()
        for rule in rules:
            path = rule.get('graph_path')
            if path:
                paths.add(path)
        return paths
    except Exception:
        return set()


def _strip_query(path: str) -> str:
    return path.split('?', 1)[0]


def _check_compliance(azure_data: dict) -> dict:
    """Check Azure AD configuration against ISO 27017 rules."""
    rules = _load_iso_rules()
    compliance_results = {
        "compliant": [],
        "non_compliant": [],
        "not_applicable": [],
        "summary": {
            "total_rules": len(rules),
            "compliant_count": 0,
            "non_compliant_count": 0,
            "not_applicable_count": 0,
            "compliance_score": 0
        }
    }
    
    for rule in rules:
        rule_result = {
            "rule_id": rule.get("rule_id"),
            "title": rule.get("title"),
            "description": rule.get("description"),
            "severity": rule.get("severity"),
            "control_id": rule.get("control_id"),
            "remediation": rule.get("remediation"),
            "status": "not_applicable",
            "current_value": None,
            "expected_value": rule.get("value"),
            "operator": rule.get("operator"),
            "graph_path": rule.get("graph_path"),
            "field": rule.get("field")
        }
        
        # Map graph paths to our fetched data
        data_key = None
        if rule.get("graph_path") == "/identity/conditionalAccess/policies":
            data_key = "conditional_access_policies"
        elif rule.get("graph_path") == "/policies/crossTenantAccessPolicy":
            data_key = "cross_tenant_access_policy"
        elif rule.get("graph_path") == "/auditLogs/directoryAudits":
            data_key = "audit_logs"
        elif rule.get("graph_path") == "/organization/{id}/certificateBasedAuthConfiguration":
            data_key = "certificate_based_auth_configuration"
        elif rule.get("graph_path") == "/policies/authorizationPolicy":
            data_key = "authorization_policy"
        elif rule.get("graph_path") == "/identityProtection/riskyUsers":
            data_key = "identity_protection_risky_users"
        elif rule.get("graph_path") == "/organization":
            data_key = "organization"
        elif rule.get("graph_path") == "/identityGovernance/lifecycleWorkflows/workflows":
            data_key = "lifecycle_workflows"
        elif rule.get("graph_path") == "/directoryRoles":
            data_key = "directory_roles"
        elif rule.get("graph_path") == "/directoryRoles/{id}/members":
            data_key = "directory_role_members"
        elif rule.get("graph_path") == "/policies/crossTenantAccessPolicy/default":
            data_key = "cross_tenant_access_default"
        elif rule.get("graph_path") == "/policies/crossTenantAccessPolicy/partners/{tenantId}":
            data_key = "cross_tenant_access_partners_details"
        elif rule.get("graph_path") == "/groupSettings":
            data_key = "group_settings"
        elif rule.get("graph_path") == "/settings":
            data_key = "settings"
        elif rule.get("graph_path") == "/organization/{organizationId}":
            data_key = "organization"
        
        if data_key and data_key in azure_data:
            rule_data = azure_data[data_key]
            
            # Check if we have error in data
            if isinstance(rule_data, dict) and rule_data.get("error"):
                rule_result["status"] = "not_applicable"
                rule_result["reason"] = f"Data fetch error: {rule_data['error']}"
                compliance_results["not_applicable"].append(rule_result)
                continue
            
            # Extract current value based on field path
            current_value = _extract_field_value(rule_data, rule.get("field"))
            rule_result["current_value"] = current_value
            
            # Check compliance based on operator
            is_compliant = _evaluate_rule(current_value, rule.get("operator"), rule.get("value"))
            
            if is_compliant:
                rule_result["status"] = "compliant"
                compliance_results["compliant"].append(rule_result)
            else:
                rule_result["status"] = "non_compliant"
                compliance_results["non_compliant"].append(rule_result)
        else:
            rule_result["status"] = "not_applicable"
            rule_result["reason"] = "Data not available for this rule"
            compliance_results["not_applicable"].append(rule_result)
    
    # Calculate summary
    compliance_results["summary"]["compliant_count"] = len(compliance_results["compliant"])
    compliance_results["summary"]["non_compliant_count"] = len(compliance_results["non_compliant"])
    compliance_results["summary"]["not_applicable_count"] = len(compliance_results["not_applicable"])
    
    # Calculate compliance score (only based on applicable rules)
    applicable_rules = compliance_results["summary"]["compliant_count"] + compliance_results["summary"]["non_compliant_count"]
    if applicable_rules > 0:
        compliance_results["summary"]["compliance_score"] = round(
            (compliance_results["summary"]["compliant_count"] / applicable_rules) * 100, 2
        )
    
    return compliance_results


def _extract_field_value(data: dict, field_path: str) -> any:
    """Extract value from nested data structure using field path."""
    if not field_path or not data:
        return None
    
    try:
        # Handle different field path formats
        if field_path.startswith("values[?(@.name=='"):
            # Handle array filtering like "values[?(@.name=='EnableGroupCreation')].value"
            import re
            match = re.search(r"values\[\?\(@\.name=='([^']+)'\)\]\.value", field_path)
            if match and isinstance(data, dict) and "value" in data:
                target_name = match.group(1)
                for item in data["value"]:
                    if isinstance(item, dict) and item.get("name") == target_name:
                        return item.get("value")
            return None
        elif "." in field_path:
            # Handle nested field access like "defaultUserRolePermissions.allowedToAccessAADAdminPortal"
            parts = field_path.split(".")
            current = data
            for part in parts:
                if isinstance(current, dict) and part in current:
                    current = current[part]
                else:
                    return None
            return current
        else:
            # Simple field access
            return data.get(field_path)
    except Exception:
        return None


def _evaluate_rule(current_value: any, operator: str, expected_value: any) -> bool:
    """Evaluate if current value meets the rule criteria."""
    if current_value is None:
        return False
    
    try:
        if operator == "==":
            return current_value == expected_value
        elif operator == "!=":
            return current_value != expected_value
        elif operator == ">=":
            return current_value >= expected_value
        elif operator == "<=":
            return current_value <= expected_value
        elif operator == ">":
            return current_value > expected_value
        elif operator == "<":
            return current_value < expected_value
        elif operator == "in":
            return current_value in expected_value
        elif operator == "not_in":
            return current_value not in expected_value
        else:
            return False
    except Exception:
        return False


@router.post("/connect")
async def connect_azure_ad(
    credentials: AzureCredentials,
    current_user: UserInDB = Depends(get_current_user),
):
    try:
        if not current_user.organization_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="User is not associated with an organization",
            )
        
        # Test the connection and get access token
        access_token = _test_azure_connection(
            credentials.clientId, credentials.clientSecret, credentials.tenantId
        )
        
        # Store encrypted credentials and connection status
        await database.db.azure_connections.update_one(
            {"organization_id": current_user.organization_id},
            {
                "$set": {
                    "organization_id": current_user.organization_id,
                    "connected": True,
                    "tenant_id": credentials.tenantId,
                    "client_id": _encrypt_credentials(credentials.clientId),
                    "client_secret": _encrypt_credentials(credentials.clientSecret),
                    "updated_at": datetime.utcnow(),
                    "last_connected_at": datetime.utcnow(),
                }
            },
            upsert=True,
        )
        return {"status": "success", "message": "Connected to Azure AD"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


@router.post("/disconnect")
async def disconnect_azure_ad(current_user: UserInDB = Depends(get_current_user)):
    if not current_user.organization_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User is not associated with an organization",
        )
    await database.db.azure_connections.update_one(
        {"organization_id": current_user.organization_id},
        {"$set": {"connected": False, "updated_at": datetime.utcnow()}},
        upsert=True,
    )
    return {"status": "success", "message": "Disconnected from Azure AD"}


@router.get("/status")
async def get_azure_status(current_user: UserInDB = Depends(get_current_user)):
    if not current_user.organization_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User is not associated with an organization",
        )
    doc = await database.db.azure_connections.find_one(
        {"organization_id": current_user.organization_id}
    )
    is_connected = bool(doc and doc.get("connected"))
    return {
        "connected": is_connected,
        "tenant_id": (doc or {}).get("tenant_id"),
        "updated_at": (doc or {}).get("updated_at"),
        "last_connected_at": (doc or {}).get("last_connected_at"),
    }


@router.get("/config")
async def get_azure_config(current_user: UserInDB = Depends(get_current_user)):
    print(f"=== Azure Config Endpoint Called ===")
    print(f"User: {current_user.email}")
    print(f"Organization ID: {current_user.organization_id}")
    
    if not current_user.organization_id:
        print("ERROR: User not associated with organization")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User is not associated with an organization",
        )
    
    print("Checking Azure connection...")
    
    # Check if connected
    doc = await database.db.azure_connections.find_one(
        {"organization_id": current_user.organization_id}
    )
    
    if not doc:
        print("ERROR: No Azure connection found")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Azure AD is not connected",
        )
    
    if not doc.get("connected"):
        print("ERROR: Azure connection not active")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Azure AD is not connected",
        )
    
    print("Azure connection found and active")
    
    try:
        # Get stored credentials
        print("Retrieving stored Azure credentials...")
        
        # Check if credentials exist
        stored_client_id = doc.get("client_id")
        stored_client_secret = doc.get("client_secret")
        tenant_id = doc.get("tenant_id")
        
        if not stored_client_id or not stored_client_secret:
            print("ERROR: Missing stored credentials")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Azure AD credentials are missing. Please reconnect to Azure AD.",
            )
        
        client_id = _decrypt_credentials(stored_client_id)
        client_secret = _decrypt_credentials(stored_client_secret)
        
        print(f"Retrieved credentials for tenant: {tenant_id}")
        
        # Get fresh access token
        print("Getting fresh access token...")
        access_token = _test_azure_connection(client_id, client_secret, tenant_id)
        print("Successfully obtained fresh access token")
        
        # Fetch real data from Azure AD
        config_data = {}
        
        # Fetch Conditional Access Policies
        print("Fetching Conditional Access Policies...")
        try:
            conditional_access = _get_azure_graph_data(access_token, "/identity/conditionalAccess/policies")
            config_data["conditional_access_policies"] = conditional_access
            print("Successfully fetched Conditional Access Policies")
        except Exception as e:
            print(f"Failed to fetch conditional access policies: {str(e)}")
            config_data["conditional_access_policies"] = {
                "error": f"Failed to fetch conditional access policies: {str(e)}",
                "value": []
            }
        
        # Fetch Authentication Methods Policy
        print("Fetching Authentication Methods Policy...")
        try:
            auth_methods = _get_azure_graph_data(access_token, "/policies/authenticationMethodsPolicy")
            config_data["authentication_methods_policy"] = auth_methods
            print("Successfully fetched Authentication Methods Policy")
        except Exception as e:
            print(f"Failed to fetch authentication methods policy: {str(e)}")
            config_data["authentication_methods_policy"] = {
                "error": f"Failed to fetch authentication methods policy: {str(e)}",
                "authenticationMethodConfigurations": []
            }
        
        # Fetch Users (limited to first 10 for performance)
        print("Fetching Users...")
        try:
            users = _get_azure_graph_data(access_token, "/users?$top=10&$select=id,displayName,userPrincipalName,accountEnabled")
            config_data["users"] = users
            print("Successfully fetched Users")
        except Exception as e:
            print(f"Failed to fetch users: {str(e)}")
            config_data["users"] = {
                "error": f"Failed to fetch users: {str(e)}",
                "value": []
            }
        
        # Fetch Organization settings
        print("Fetching Organization settings...")
        try:
            organization = _get_azure_graph_data(access_token, "/organization")
            config_data["organization"] = organization
            print("Successfully fetched Organization settings")
        except Exception as e:
            print(f"Failed to fetch organization settings: {str(e)}")
            config_data["organization"] = {
                "error": f"Failed to fetch organization settings: {str(e)}",
                "value": []
            }
        
        # Fetch Authorization Policy
        print("Fetching Authorization Policy...")
        try:
            auth_policy = _get_azure_graph_data(access_token, "/policies/authorizationPolicy")
            config_data["authorization_policy"] = auth_policy
            print("Successfully fetched Authorization Policy")
        except Exception as e:
            print(f"Failed to fetch authorization policy: {str(e)}")
            config_data["authorization_policy"] = {
                "error": f"Failed to fetch authorization policy: {str(e)}",
                "value": []
            }
        
        # Fetch Application Registrations
        print("Fetching Application Registrations...")
        try:
            apps = _get_azure_graph_data(access_token, "/applications?$top=10&$select=id,displayName,appId,createdDateTime")
            config_data["applications"] = apps
            print("Successfully fetched Application Registrations")
        except Exception as e:
            print(f"Failed to fetch applications: {str(e)}")
            config_data["applications"] = {
                "error": f"Failed to fetch applications: {str(e)}",
                "value": []
            }
        
        # Fetch Groups
        print("Fetching Groups...")
        try:
            groups = _get_azure_graph_data(access_token, "/groups?$top=10&$select=id,displayName,description,createdDateTime")
            config_data["groups"] = groups
            print("Successfully fetched Groups")
        except Exception as e:
            print(f"Failed to fetch groups: {str(e)}")
            config_data["groups"] = {
                "error": f"Failed to fetch groups: {str(e)}",
                "value": []
            }
        
        # Fetch Cross Tenant Access Policy
        print("Fetching Cross Tenant Access Policy...")
        try:
            cross_tenant = _get_azure_graph_data(access_token, "/policies/crossTenantAccessPolicy")
            config_data["cross_tenant_access_policy"] = cross_tenant
            print("Successfully fetched Cross Tenant Access Policy")
        except Exception as e:
            print(f"Failed to fetch cross tenant access policy: {str(e)}")
            config_data["cross_tenant_access_policy"] = {
                "error": f"Failed to fetch cross tenant access policy: {str(e)}",
                "value": []
            }
        
        # Fetch Cross Tenant Access Default Policy
        print("Fetching Cross Tenant Access Default Policy...")
        try:
            cross_tenant_default = _get_azure_graph_data(access_token, "/policies/crossTenantAccessPolicy/default")
            config_data["cross_tenant_access_default"] = cross_tenant_default
            print("Successfully fetched Cross Tenant Access Default Policy")
        except Exception as e:
            print(f"Failed to fetch cross tenant access default: {str(e)}")
            config_data["cross_tenant_access_default"] = {
                "error": f"Failed to fetch cross tenant access default: {str(e)}"
            }

        # Fetch Cross Tenant Access Partners (summary)
        print("Fetching Cross Tenant Access Partners...")
        try:
            partners = _get_azure_graph_data(access_token, "/policies/crossTenantAccessPolicy/partners")
            config_data["cross_tenant_access_partners"] = partners
            # Optionally fetch details for first few partners
            try:
                partner_values = (partners or {}).get("value", [])
                detailed_partners = {}
                for partner in partner_values[:3]:
                    partner_id = partner.get("tenantId") or partner.get("id")
                    if partner_id:
                        detail = _get_azure_graph_data(access_token, f"/policies/crossTenantAccessPolicy/partners/{partner_id}")
                        detailed_partners[partner_id] = detail
                if detailed_partners:
                    config_data["cross_tenant_access_partners_details"] = detailed_partners
            except Exception as e:
                print(f"Failed to fetch partner details: {str(e)}")
        except Exception as e:
            print(f"Failed to fetch cross tenant partners: {str(e)}")
            config_data["cross_tenant_access_partners"] = {
                "error": f"Failed to fetch cross tenant partners: {str(e)}",
                "value": []
            }

        # Fetch Audit Logs Directory Audits
        print("Fetching Audit Logs...")
        try:
            audit_logs = _get_azure_graph_data(access_token, "/auditLogs/directoryAudits?$top=10")
            config_data["audit_logs"] = audit_logs
            print("Successfully fetched Audit Logs")
        except Exception as e:
            print(f"Failed to fetch audit logs: {str(e)}")
            config_data["audit_logs"] = {
                "error": f"Failed to fetch audit logs: {str(e)}",
                "value": []
            }
        
        # Fetch Identity Protection risky users
        print("Fetching Identity Protection risky users...")
        try:
            risky_users = _get_azure_graph_data(access_token, "/identityProtection/riskyUsers?$top=10")
            config_data["identity_protection_risky_users"] = risky_users
            print("Successfully fetched risky users")
        except Exception as e:
            print(f"Failed to fetch risky users: {str(e)}")
            config_data["identity_protection_risky_users"] = {
                "error": f"Failed to fetch risky users: {str(e)}",
                "value": []
            }

        # Fetch directory roles and a sample of members
        print("Fetching Directory Roles...")
        try:
            directory_roles = _get_azure_graph_data(access_token, "/directoryRoles")
            config_data["directory_roles"] = directory_roles
            print("Successfully fetched Directory Roles")
            try:
                role_values = (directory_roles or {}).get("value", [])
                role_members = {}
                for role in role_values[:3]:
                    role_id = role.get("id")
                    if role_id:
                        members = _get_azure_graph_data(access_token, f"/directoryRoles/{role_id}/members?$top=10")
                        role_members[role_id] = members
                if role_members:
                    config_data["directory_role_members"] = role_members
            except Exception as e:
                print(f"Failed to fetch directory role members: {str(e)}")
        except Exception as e:
            print(f"Failed to fetch directory roles: {str(e)}")
            config_data["directory_roles"] = {
                "error": f"Failed to fetch directory roles: {str(e)}",
                "value": []
            }

        # Fetch group settings (for group self-service / EnableGroupCreation)
        print("Fetching Group Settings...")
        try:
            group_settings = _get_azure_graph_data(access_token, "/groupSettings")
            config_data["group_settings"] = group_settings
            print("Successfully fetched Group Settings")
        except Exception as e:
            print(f"Failed to fetch group settings: {str(e)}")
            config_data["group_settings"] = {
                "error": f"Failed to fetch group settings: {str(e)}",
                "value": []
            }

        # Fetch general tenant settings (admin center access, LinkedIn integration, etc.)
        print("Fetching Directory Settings...")
        try:
            # Use /settings as per ISO rules for directory settings
            settings_resp = _get_azure_graph_data(access_token, "/settings?$top=200")
            config_data["settings"] = settings_resp
            print("Successfully fetched Directory Settings")
        except Exception as e:
            print(f"Failed to fetch directory settings: {str(e)}")
            config_data["settings"] = {
                "error": f"Failed to fetch directory settings: {str(e)}",
                "value": []
            }

        # Fetch certificate-based auth configuration under organization
        print("Fetching Certificate Based Auth Configuration...")
        try:
            org_list = config_data.get("organization") or _get_azure_graph_data(access_token, "/organization")
            org_values = (org_list or {}).get("value", [])
            if org_values:
                org_id = org_values[0].get("id")
                if org_id:
                    cba = _get_azure_graph_data(access_token, f"/organization/{org_id}/certificateBasedAuthConfiguration")
                    config_data["certificate_based_auth_configuration"] = cba
                    print("Successfully fetched Certificate Based Auth Configuration")
        except Exception as e:
            print(f"Failed to fetch certificate based auth configuration: {str(e)}")
            config_data["certificate_based_auth_configuration"] = {
                "error": f"Failed to fetch certificate based auth configuration: {str(e)}",
                "value": []
            }

        # Fetch Lifecycle Workflows (identity governance)
        print("Fetching Identity Governance Lifecycle Workflows...")
        try:
            lifecycle = _get_azure_graph_data(access_token, "/identityGovernance/lifecycleWorkflows/workflows")
            config_data["lifecycle_workflows"] = lifecycle
            print("Successfully fetched Lifecycle Workflows")
        except Exception as e:
            print(f"Failed to fetch lifecycle workflows: {str(e)}")
            config_data["lifecycle_workflows"] = {
                "error": f"Failed to fetch lifecycle workflows: {str(e)}",
                "value": []
            }
        
        # Summarize coverage of ISO 27017 graph paths
        iso_paths = _load_iso_graph_paths()
        implemented = set()
        # Map our implemented calls to base paths (no query)
        implemented.update({
            "/identity/conditionalAccess/policies",
            "/policies/authenticationMethodsPolicy",
            "/users",
            "/organization",
            "/policies/authorizationPolicy",
            "/applications",
            "/groups",
            "/policies/crossTenantAccessPolicy",
            "/policies/crossTenantAccessPolicy/default",
            "/policies/crossTenantAccessPolicy/partners",
            "/auditLogs/directoryAudits",
            "/settings",
            "/groupSettings",
            "/directoryRoles",
            "/directoryRoles/{id}/members",
            "/identityProtection/riskyUsers",
            "/organization/{id}/certificateBasedAuthConfiguration",
            "/identityGovernance/lifecycleWorkflows/workflows",
        })
        # Normalize ISO paths (strip query if any)
        iso_base = {_strip_query(p) for p in iso_paths}
        covered = sorted(p for p in iso_base if p in implemented)
        uncovered = sorted(p for p in iso_base if p not in implemented)
        config_data["iso_27017_graph_paths"] = {
            "total": len(iso_base),
            "covered": covered,
            "uncovered": uncovered,
        }

        # Perform compliance checking against ISO 27017 rules
        print("Performing compliance check against ISO 27017 rules...")
        try:
            compliance_results = _check_compliance(config_data)
            config_data["compliance_check"] = compliance_results
            print(f"Compliance check completed. Score: {compliance_results['summary']['compliance_score']}%")
        except Exception as e:
            print(f"Failed to perform compliance check: {str(e)}")
            config_data["compliance_check"] = {
                "error": f"Failed to perform compliance check: {str(e)}",
                "summary": {"compliance_score": 0}
            }

        print("Successfully completed Azure config fetch")
        
        # Log the configuration fetch
        await _log_azure_config_fetch(
            user_id=current_user.id,
            user_email=current_user.email,
            organization_id=current_user.organization_id,
            change_type="config_fetch",
            status="success"
        )
        
        return config_data
        
    except Exception as e:
        # Log the failed fetch
        try:
            await _log_azure_config_fetch(
                user_id=current_user.id,
                user_email=current_user.email,
                organization_id=current_user.organization_id,
                change_type="config_fetch",
                status="failed",
                error_message=str(e)
            )
        except:
            pass  # Don't fail if logging fails
        
        print(f"=== UNEXPECTED ERROR ===")
        print(f"Error: {str(e)}")
        print(f"Error type: {type(e).__name__}")
        import traceback
        print(f"Traceback: {traceback.format_exc()}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch Azure AD configuration: {str(e)}",
        )


async def _log_azure_config_fetch(
    user_id: str,
    user_email: str,
    organization_id: str,
    change_type: str,
    status: str,
    error_message: Optional[str] = None,
    details: Optional[dict] = None
):
    """Log Azure AD configuration fetch or change."""
    log_entry = {
        "user_id": user_id,
        "user_email": user_email,
        "organization_id": organization_id,
        "change_type": change_type,  # "config_fetch", "config_update", "connection", etc.
        "status": status,  # "success", "failed"
        "timestamp": datetime.utcnow(),
        "error_message": error_message,
        "details": details or {}
    }
    
    try:
        await database.db.azure_config_logs.insert_one(log_entry)
    except Exception as e:
        print(f"Failed to log Azure config change: {str(e)}")


@router.get("/logs")
async def get_azure_config_logs(
    current_user: UserInDB = Depends(get_current_user),
    start_date: Optional[str] = Query(None, description="Start date (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="End date (YYYY-MM-DD)"),
    user_email: Optional[str] = Query(None, description="Filter by user email"),
    change_type: Optional[str] = Query(None, description="Filter by change type"),
    status_filter: Optional[str] = Query(None, description="Filter by status"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of logs to return"),
    skip: int = Query(0, ge=0, description="Number of logs to skip")
):
    """Retrieve Azure AD configuration change logs with filtering."""
    if not current_user.organization_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User is not associated with an organization",
        )
    
    # Build query filter
    query = {"organization_id": current_user.organization_id}
    
    # Date filtering
    if start_date or end_date:
        date_filter = {}
        if start_date:
            try:
                start_dt = datetime.strptime(start_date, "%Y-%m-%d")
                date_filter["$gte"] = start_dt
            except ValueError:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid start_date format. Use YYYY-MM-DD"
                )
        if end_date:
            try:
                end_dt = datetime.strptime(end_date, "%Y-%m-%d") + timedelta(days=1)
                date_filter["$lt"] = end_dt
            except ValueError:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid end_date format. Use YYYY-MM-DD"
                )
        if date_filter:
            query["timestamp"] = date_filter
    
    # User filtering
    if user_email:
        query["user_email"] = {"$regex": user_email, "$options": "i"}
    
    # Change type filtering
    if change_type:
        query["change_type"] = change_type
    
    # Status filtering
    if status_filter:
        query["status"] = status_filter
    
    try:
        # Fetch logs
        cursor = database.db.azure_config_logs.find(query).sort("timestamp", -1).skip(skip).limit(limit)
        logs = await cursor.to_list(length=limit)
        
        # Get total count
        total_count = await database.db.azure_config_logs.count_documents(query)
        
        # Convert ObjectId to string
        for log in logs:
            log["_id"] = str(log["_id"])
            log["timestamp"] = log["timestamp"].isoformat() if isinstance(log["timestamp"], datetime) else log["timestamp"]
        
        return {
            "logs": logs,
            "total": total_count,
            "skip": skip,
            "limit": limit
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve logs: {str(e)}"
        )


@router.get("/logs/export/csv")
async def export_azure_config_logs_csv(
    current_user: UserInDB = Depends(get_current_user),
    start_date: Optional[str] = Query(None, description="Start date (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="End date (YYYY-MM-DD)"),
    user_email: Optional[str] = Query(None, description="Filter by user email"),
    change_type: Optional[str] = Query(None, description="Filter by change type"),
    status_filter: Optional[str] = Query(None, description="Filter by status")
):
    """Export Azure AD configuration change logs as CSV."""
    if not current_user.organization_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User is not associated with an organization",
        )
    
    # Build query filter (same as get_azure_config_logs)
    query = {"organization_id": current_user.organization_id}
    
    if start_date or end_date:
        date_filter = {}
        if start_date:
            start_dt = datetime.strptime(start_date, "%Y-%m-%d")
            date_filter["$gte"] = start_dt
        if end_date:
            end_dt = datetime.strptime(end_date, "%Y-%m-%d") + timedelta(days=1)
            date_filter["$lt"] = end_dt
        if date_filter:
            query["timestamp"] = date_filter
    
    if user_email:
        query["user_email"] = {"$regex": user_email, "$options": "i"}
    if change_type:
        query["change_type"] = change_type
    if status_filter:
        query["status"] = status_filter
    
    try:
        cursor = database.db.azure_config_logs.find(query).sort("timestamp", -1)
        logs = await cursor.to_list(length=None)
        
        # Create CSV
        output = io.StringIO()
        writer = csv.writer(output)
        
        # Write header
        writer.writerow([
            "Timestamp", "User Email", "Change Type", "Status", 
            "Error Message", "Details"
        ])
        
        # Write data
        for log in logs:
            timestamp = log["timestamp"]
            if isinstance(timestamp, datetime):
                timestamp = timestamp.isoformat()
            
            writer.writerow([
                timestamp,
                log.get("user_email", ""),
                log.get("change_type", ""),
                log.get("status", ""),
                log.get("error_message", ""),
                json.dumps(log.get("details", {}))
            ])
        
        output.seek(0)
        return Response(
            content=output.getvalue(),
            media_type="text/csv",
            headers={
                "Content-Disposition": f"attachment; filename=azure_config_logs_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.csv"
            }
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to export logs: {str(e)}"
        )


@router.get("/logs/export/pdf")
async def export_azure_config_logs_pdf(
    current_user: UserInDB = Depends(get_current_user),
    start_date: Optional[str] = Query(None, description="Start date (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="End date (YYYY-MM-DD)"),
    user_email: Optional[str] = Query(None, description="Filter by user email"),
    change_type: Optional[str] = Query(None, description="Filter by change type"),
    status_filter: Optional[str] = Query(None, description="Filter by status")
):
    """Export Azure AD configuration change logs as PDF."""
    try:
        from reportlab.lib import colors
        from reportlab.lib.pagesizes import letter
        from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
        from reportlab.lib.styles import getSampleStyleSheet
        from reportlab.lib.units import inch
    except ImportError:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="PDF export requires reportlab. Install with: pip install reportlab"
        )
    
    if not current_user.organization_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User is not associated with an organization",
        )
    
    # Build query filter (same as get_azure_config_logs)
    query = {"organization_id": current_user.organization_id}
    
    if start_date or end_date:
        date_filter = {}
        if start_date:
            start_dt = datetime.strptime(start_date, "%Y-%m-%d")
            date_filter["$gte"] = start_dt
        if end_date:
            end_dt = datetime.strptime(end_date, "%Y-%m-%d") + timedelta(days=1)
            date_filter["$lt"] = end_dt
        if date_filter:
            query["timestamp"] = date_filter
    
    if user_email:
        query["user_email"] = {"$regex": user_email, "$options": "i"}
    if change_type:
        query["change_type"] = change_type
    if status_filter:
        query["status"] = status_filter
    
    try:
        cursor = database.db.azure_config_logs.find(query).sort("timestamp", -1)
        logs = await cursor.to_list(length=None)
        
        # Create PDF
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=letter, topMargin=0.5*inch)
        story = []
        styles = getSampleStyleSheet()
        
        # Title
        title = Paragraph("Azure AD Configuration Change Logs", styles['Title'])
        story.append(title)
        story.append(Spacer(1, 0.2*inch))
        
        # Summary
        summary_text = f"Total Logs: {len(logs)}<br/>Generated: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}"
        summary = Paragraph(summary_text, styles['Normal'])
        story.append(summary)
        story.append(Spacer(1, 0.3*inch))
        
        # Table data
        table_data = [["Timestamp", "User", "Change Type", "Status", "Error"]]
        
        for log in logs:
            timestamp = log["timestamp"]
            if isinstance(timestamp, datetime):
                timestamp = timestamp.strftime("%Y-%m-%d %H:%M:%S")
            
            table_data.append([
                timestamp,
                log.get("user_email", ""),
                log.get("change_type", ""),
                log.get("status", ""),
                log.get("error_message", "")[:50] if log.get("error_message") else ""
            ])
        
        # Create table
        table = Table(table_data)
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('FONTSIZE', (0, 1), (-1, -1), 8),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.lightgrey]),
        ]))
        
        story.append(table)
        doc.build(story)
        
        buffer.seek(0)
        return Response(
            content=buffer.read(),
            media_type="application/pdf",
            headers={
                "Content-Disposition": f"attachment; filename=azure_config_logs_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.pdf"
            }
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to export logs as PDF: {str(e)}"
        )


