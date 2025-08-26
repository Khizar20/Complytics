from fastapi import APIRouter, HTTPException, Depends, status
from pydantic import BaseModel, Field
from typing import Optional
from utils.security import get_current_user
from schemas.users import UserInDB

import msal
from datetime import datetime
from db import database


router = APIRouter()


class AzureCredentials(BaseModel):
    clientId: str = Field(..., min_length=1)
    clientSecret: str = Field(..., min_length=1)
    tenantId: str = Field(..., min_length=1)


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
        _ = _test_azure_connection(
            credentials.clientId, credentials.clientSecret, credentials.tenantId
        )
        # Upsert org-level Azure connection status (no secrets stored)
        await database.db.azure_connections.update_one(
            {"organization_id": current_user.organization_id},
            {
                "$set": {
                    "organization_id": current_user.organization_id,
                    "connected": True,
                    "tenant_id": credentials.tenantId,
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


