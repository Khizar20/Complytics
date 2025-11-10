from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPBearer
from schemas.users import UserCreate, UserInDB, OrganizationInDB, AccountDeletionRequest
from utils.security import get_current_user, send_simple_email
from db import database
from typing import List
from utils.security import get_password_hash
from datetime import datetime
from superadmin_deps import get_superadmin
from bson import ObjectId


router = APIRouter()
security = HTTPBearer()

@router.post("/create-admin")
async def create_admin_account(
    user_data: UserCreate,
    current_user: UserInDB = Depends(get_superadmin)  # Changed here
):
    # Verify superadmin permissions
    if current_user.role != "superadmin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only superadmins can create admin accounts"
        )
    
    # Check if email already exists
    if await database.db.users.find_one({"email": user_data.email}):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
    
    # Create new admin user
    user_dict = user_data.model_dump(exclude={"password"})
    user_dict["password_hash"] = get_password_hash(user_data.password)
    user_dict["role"] = "admin"
    user_dict["created_by"] = current_user.id
    user_dict["is_active"] = True
    user_dict["created_at"] = datetime.utcnow()
    user_dict["updated_at"] = datetime.utcnow()
    
    result = await database.db.users.insert_one(user_dict)
    created_user = await database.db.users.find_one({"_id": result.inserted_id})
    
    return UserInDB.from_mongo(created_user)  # Updated line

@router.get("/admins", response_model=List[UserInDB])
async def list_all_admins(
    current_user: UserInDB = Depends(get_current_user)
):
    if current_user.role != "superadmin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only superadmins can view this list"
        )
    
    admins = await database.db.users.find({"role": "admin"}).to_list(None)
    
    # Convert MongoDB documents to UserInDB models properly
    admin_list = []
    for admin in admins:
        admin['_id'] = str(admin['_id'])  # Convert ObjectId to string
        admin_list.append(UserInDB(**admin))
    
    return admin_list

@router.get("/organizations/active", response_model=List[OrganizationInDB])
async def get_active_organizations(
    current_user: UserInDB = Depends(get_current_user)
):
    if current_user.role != "superadmin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only superadmins can view organizations"
        )
    
    orgs = await database.db.organizations.find(
        {"is_active": True}
    ).to_list(length=None)
    
    # Convert MongoDB documents to OrganizationInDB models properly
    org_list = []
    for org in orgs:
        org['_id'] = str(org['_id'])  # Convert ObjectId to string
        org_list.append(OrganizationInDB(**org))
    
    return org_list

@router.get("/active-users", response_model=List[UserInDB])
async def get_active_users(
    current_user: UserInDB = Depends(get_superadmin)
):
    # Get all active users (both admins and team members)
    users = await database.db.users.find(
        {"is_active": True}
    ).to_list(length=None)
    
    # Convert MongoDB documents to UserInDB models
    return [UserInDB.from_mongo(user) for user in users]

@router.delete("/users/{user_id}")
async def delete_user(
    user_id: str,
    current_user: UserInDB = Depends(get_superadmin)
):
    """
    Delete a user and all related organization data.
    If the user has an organization, all organization data will be deleted.
    """
    try:
        obj_id = ObjectId(user_id)
    except:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid user ID"
        )
    
    # Find the user
    user = await database.db.users.find_one({"_id": obj_id})
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Prevent superadmin from deleting themselves
    if user.get("role") == "superadmin" and str(user.get("_id")) == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete your own superadmin account"
        )
    
    user_id_str = str(user.get("_id"))
    org_id = user.get("organization_id")
    
    # If user has an organization, delete all organization-related data
    if org_id:
        # Collect all user ids in the organization (admin + team)
        org_users = await database.db.users.find({"organization_id": org_id}).to_list(length=None)
        org_user_ids = [str(u.get("_id")) for u in org_users if u.get("_id")]
        
        # Delete compliance chat history for all org users
        if org_user_ids:
            await database.db.compliance_chat_history.delete_many({
                "user_id": {"$in": org_user_ids}
            })
        
        # Delete UI testing results for the organization
        await database.db.ui_testing_results.delete_many({
            "organization_id": org_id
        })
        
        # Delete Azure connection records for the organization
        await database.db.azure_connections.delete_many({
            "organization_id": org_id
        })
        
        # Delete Azure config logs for the organization
        await database.db.azure_config_logs.delete_many({
            "organization_id": org_id
        })
        
        # Delete all users in the organization (including the current user)
        await database.db.users.delete_many({"organization_id": org_id})
        
        # Delete organization record
        try:
            await database.db.organizations.delete_one({"_id": ObjectId(org_id)})
        except:
            # If ObjectId conversion fails, attempt by string match
            await database.db.organizations.delete_one({"_id": org_id})
        
        return {
            "message": f"User and organization (ID: {org_id}) deleted successfully. All related data has been removed.",
            "deleted_user_id": user_id_str,
            "deleted_organization_id": org_id,
            "deleted_users_count": len(org_user_ids)
        }
    else:
        # User has no organization, just delete user-specific data
        # Delete compliance chat history for this user
        await database.db.compliance_chat_history.delete_many({
            "user_id": user_id_str
        })
        
        # Delete Azure config logs for this user
        await database.db.azure_config_logs.delete_many({
            "user_id": user_id_str
        })
        
        # Delete the user
        await database.db.users.delete_one({"_id": obj_id})
        
        return {
            "message": f"User deleted successfully. All related data has been removed.",
            "deleted_user_id": user_id_str
        }

@router.get("/deletion-requests")
async def list_deletion_requests(current_user: UserInDB = Depends(get_superadmin)):
    requests = await database.db.account_deletion_requests.find({}).to_list(length=None)
    return [AccountDeletionRequest.from_mongo(r) for r in requests]

@router.post("/deletion-requests/{request_id}/approve")
async def approve_deletion_request(
    request_id: str,
    current_user: UserInDB = Depends(get_superadmin)
):
    try:
        obj_id = ObjectId(request_id)
    except:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid request ID")

    req = await database.db.account_deletion_requests.find_one({"_id": obj_id})
    if not req:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Request not found")
    if req.get("status") != "pending":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Request is not pending")

    # Execute deletion: delete org-scoped data and accounts
    org_id = req.get("organization_id")
    if org_id:
        # Collect all user ids in the organization (admin + team)
        org_users = await database.db.users.find({"organization_id": org_id}).to_list(length=None)
        org_user_ids = [str(u.get("_id")) for u in org_users if u.get("_id")]

        # Delete compliance chat history for all org users
        if org_user_ids:
            await database.db.compliance_chat_history.delete_many({
                "user_id": {"$in": org_user_ids}
            })

        # Delete Azure connection records for the organization
        await database.db.azure_connections.delete_many({
            "organization_id": org_id
        })

        # Delete team members and admin users under org
        await database.db.users.delete_many({"organization_id": org_id})

        # Delete organization record
        try:
            await database.db.organizations.delete_one({"_id": ObjectId(org_id)})
        except:
            # If ObjectId conversion fails, attempt by string match
            await database.db.organizations.delete_one({"_id": org_id})

    # Mark request as approved and executed
    await database.db.account_deletion_requests.update_one(
        {"_id": obj_id},
        {
            "$set": {
                "status": "approved",
                "reviewed_by": current_user.id,
                "reviewed_at": datetime.utcnow(),
                "executed_at": datetime.utcnow(),
                "updated_at": datetime.utcnow()
            },
            "$push": {
                "events": {
                    "type": "approved",
                    "by": current_user.id,
                    "at": datetime.utcnow()
                }
            }
        }
    )

    updated = await database.db.account_deletion_requests.find_one({"_id": obj_id})
    # Notify involved parties
    try:
        # Notify superadmin (self-confirmation)
        await send_simple_email(
            to_email="superadmin@complytics.com",
            subject="Admin Account Deletion Approved",
            html_body=f"<p>Deletion request {request_id} approved and executed.</p>"
        )
        # Notify original admin by email if we can find it
        requester_id = updated.get("requester_user_id") if updated else req.get("requester_user_id")
        if requester_id:
            user = await database.db.users.find_one({"_id": ObjectId(requester_id)})
            if user and user.get("email"):
                try:
                    await send_simple_email(
                        to_email=user["email"],
                        subject="Your Account Deletion Has Been Processed",
                        html_body="<p>Your account and associated organization data have been deleted.</p>"
                    )
                except Exception as e:
                    print(f"Failed to notify requester: {str(e)}")
    except Exception as e:
        print(f"Notification error: {str(e)}")

    return AccountDeletionRequest.from_mongo(updated)

@router.post("/deletion-requests/{request_id}/reject")
async def reject_deletion_request(
    request_id: str,
    reason: str | None = None,
    current_user: UserInDB = Depends(get_superadmin)
):
    try:
        obj_id = ObjectId(request_id)
    except:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid request ID")

    req = await database.db.account_deletion_requests.find_one({"_id": obj_id})
    if not req:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Request not found")
    if req.get("status") != "pending":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Request is not pending")

    await database.db.account_deletion_requests.update_one(
        {"_id": obj_id},
        {
            "$set": {
                "status": "rejected",
                "reviewed_by": current_user.id,
                "reviewed_at": datetime.utcnow(),
                "updated_at": datetime.utcnow()
            },
            "$push": {
                "events": {
                    "type": "rejected",
                    "by": current_user.id,
                    "at": datetime.utcnow(),
                    "detail": reason or None
                }
            }
        }
    )

    updated = await database.db.account_deletion_requests.find_one({"_id": obj_id})
    # Notify requester about rejection
    try:
        requester_id = updated.get("requester_user_id") if updated else req.get("requester_user_id")
        if requester_id:
            user = await database.db.users.find_one({"_id": ObjectId(requester_id)})
            if user and user.get("email"):
                await send_simple_email(
                    to_email=user["email"],
                    subject="Your Account Deletion Request Was Rejected",
                    html_body=f"<p>Your request was rejected. Reason: {reason or 'Not provided'}.</p>"
                )
    except Exception as e:
        print(f"Failed to notify requester of rejection: {str(e)}")

    return AccountDeletionRequest.from_mongo(updated)