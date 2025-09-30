from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPBearer
from schemas.users import UserInDB, UserCreate, AccountDeletionRequest
from utils.security import (
    get_current_user, 
    generate_random_password, 
    send_credentials_email,
    get_password_hash,
    send_role_change_email,
    send_simple_email
)
from db import database
from typing import List, Optional
from datetime import datetime
from pydantic import BaseModel
from bson import ObjectId

router = APIRouter()
security = HTTPBearer()

class TeamMemberCreate(BaseModel):
    first_name: str
    last_name: str
    email: str
    role: str  # compliance_team, it_team, or management_team

class TeamMemberUpdate(BaseModel):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    role: Optional[str] = None
    is_active: Optional[bool] = None

class BulkDeleteRequest(BaseModel):
    member_ids: List[str]

class DeletionRequestCreate(BaseModel):
    reason: Optional[str] = None

@router.get("/team-members", response_model=List[UserInDB])
async def list_team_members(
    current_user: UserInDB = Depends(get_current_user)
):
    # Verify admin permissions
    if current_user.role not in ["superadmin", "admin"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins can view team members"
        )
    
    # Get all team members for the organization
    team_members = await database.db.users.find(
        {
            "organization_id": current_user.organization_id,
            "role": {"$in": ["compliance_team", "it_team", "management_team"]}
        }
    ).to_list(None)
    
    # Convert MongoDB documents
    converted_members = []
    for member in team_members:
        member["_id"] = str(member["_id"])
        converted_members.append(UserInDB(**member))
    
    return converted_members

@router.post("/create-team-member", response_model=UserInDB)
async def create_team_member(
    user_data: TeamMemberCreate,
    current_user: UserInDB = Depends(get_current_user)
):
    # Verify admin permissions and get organization
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only organization admins can create team members"
        )
    
    if not current_user.organization_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't belong to any organization"
        )
    
    # Validate team role
    valid_roles = ["compliance_team", "it_team", "management_team"]
    if user_data.role not in valid_roles:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid role. Must be one of: {', '.join(valid_roles)}"
        )
    
    # Check if email exists
    if await database.db.users.find_one({"email": user_data.email}):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
    
    # Get organization details
    try:
        org_id = ObjectId(current_user.organization_id)
        org = await database.db.organizations.find_one({"_id": org_id})
        if not org:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Organization not found"
            )
    except:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid organization ID format"
        )
    
    # Generate random password
    temp_password = generate_random_password()
    
    # Create team member
    user_dict = {
        "first_name": user_data.first_name,
        "last_name": user_data.last_name,
        "email": user_data.email,
        "password_hash": get_password_hash(temp_password),
        "role": user_data.role,
        "organization_id": str(org_id),
        "created_by": current_user.id,
        "is_active": True,
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow()
    }
    
    # Insert the user
    result = await database.db.users.insert_one(user_dict)
    if not result.acknowledged:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create team member"
        )
    
    # Get the created user
    created_user = await database.db.users.find_one({"_id": result.inserted_id})
    if not created_user:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve created user"
        )
    
    # Send email with credentials
    try:
        await send_credentials_email(
            email=user_data.email,
            username=user_data.email,
            password=temp_password,
            organization_name=org["name"],
            first_name=user_data.first_name,
            last_name=user_data.last_name,
            role=user_data.role
        )
    except Exception as e:
        # Log the error but don't fail the operation
        print(f"Failed to send email: {str(e)}")
    
    # Convert the user document to UserInDB model
    created_user["_id"] = str(created_user["_id"])
    return UserInDB(**created_user)

@router.delete("/team-members/{member_id}")
async def delete_team_member(
    member_id: str,
    current_user: UserInDB = Depends(get_current_user)
):
    # Verify admin permissions
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only organization admins can delete team members"
        )
    
    try:
        # Convert string ID to ObjectId
        obj_id = ObjectId(member_id)
    except:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid member ID format"
        )
    
    # Find and delete the team member
    result = await database.db.users.delete_one({
        "_id": obj_id,
        "organization_id": current_user.organization_id,
        "role": {"$in": ["compliance_team", "it_team", "management_team"]}
    })
    
    if result.deleted_count == 0:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Team member not found or not authorized to delete"
        )
    
    return {"message": "Team member deleted successfully"}

@router.post("/team-members/bulk-delete")
async def bulk_delete_team_members(
    request: BulkDeleteRequest,
    current_user: UserInDB = Depends(get_current_user)
):
    # Verify admin permissions
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only organization admins can delete team members"
        )
    
    try:
        # Convert string IDs to ObjectIds
        obj_ids = [ObjectId(member_id) for member_id in request.member_ids]
    except:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid member ID format"
        )
    
    # Delete multiple team members
    result = await database.db.users.delete_many({
        "_id": {"$in": obj_ids},
        "organization_id": current_user.organization_id,
        "role": {"$in": ["compliance_team", "it_team", "management_team"]}
    })
    
    if result.deleted_count == 0:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No team members found or not authorized to delete"
        )
    
    return {"message": f"Successfully deleted {result.deleted_count} team members"}

@router.patch("/team-members/{member_id}", response_model=UserInDB)
async def update_team_member(
    member_id: str,
    update_data: TeamMemberUpdate,
    current_user: UserInDB = Depends(get_current_user)
):
    # Verify admin permissions
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only organization admins can update team members"
        )
    
    try:
        # Convert string ID to ObjectId
        obj_id = ObjectId(member_id)
    except:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid member ID format"
        )
    
    # Get the current team member data
    current_member = await database.db.users.find_one({
        "_id": obj_id,
        "organization_id": current_user.organization_id,
        "role": {"$in": ["compliance_team", "it_team", "management_team"]}
    })
    
    if not current_member:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Team member not found or not authorized to update"
        )
    
    # Prepare update data
    update_dict = {k: v for k, v in update_data.model_dump().items() if v is not None}
    if not update_dict:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No valid update data provided"
        )
    
    # Add updated_at timestamp
    update_dict["updated_at"] = datetime.utcnow()
    
    # Update the team member
    result = await database.db.users.find_one_and_update(
        {
            "_id": obj_id,
            "organization_id": current_user.organization_id,
            "role": {"$in": ["compliance_team", "it_team", "management_team"]}
        },
        {"$set": update_dict},
        return_document=True
    )
    
    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Team member not found or not authorized to update"
        )
    
    # If role was changed, send notification email
    if "role" in update_dict and update_dict["role"] != current_member["role"]:
        try:
            # Get organization details
            org = await database.db.organizations.find_one({"_id": ObjectId(current_user.organization_id)})
            if org:
                await send_role_change_email(
                    email=current_member["email"],
                    first_name=current_member["first_name"],
                    last_name=current_member["last_name"],
                    old_role=current_member["role"],
                    new_role=update_dict["role"],
                    organization_name=org["name"]
                )
        except Exception as e:
            # Log the error but don't fail the operation
            print(f"Failed to send role change email: {str(e)}")
    
    # Convert to UserInDB model
    result["_id"] = str(result["_id"])
    return UserInDB(**result)

@router.post("/request-account-deletion")
async def request_account_deletion(
    payload: DeletionRequestCreate,
    current_user: UserInDB = Depends(get_current_user)
):
    # Only admins can request deletion of their own account/org
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins can request account deletion"
        )

    # Ensure only one active/pending request per admin/org
    existing = await database.db.account_deletion_requests.find_one({
        "requester_user_id": current_user.id,
        "status": "pending"
    })
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A pending deletion request already exists"
        )

    doc = {
        "requester_user_id": current_user.id,
        "organization_id": current_user.organization_id,
        "reason": payload.reason,
        "status": "pending",
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow(),
        "events": [
            {
                "type": "requested",
                "by": current_user.id,
                "at": datetime.utcnow(),
                "detail": payload.reason or None
            }
        ]
    }

    result = await database.db.account_deletion_requests.insert_one(doc)
    created = await database.db.account_deletion_requests.find_one({"_id": result.inserted_id})

    # Notify superadmin via email if configured
    try:
        await send_simple_email(
            to_email="superadmin@complytics.com",
            subject="New Admin Account Deletion Request",
            html_body=f"""
            <html><body>
            <p>An admin has requested account deletion.</p>
            <ul>
              <li>User: {current_user.email}</li>
              <li>Organization ID: {current_user.organization_id or 'N/A'}</li>
              <li>Reason: {payload.reason or 'None provided'}</li>
            </ul>
            </body></html>
            """
        )
    except Exception as e:
        print(f"Failed to send deletion request email: {str(e)}")
    return AccountDeletionRequest.from_mongo(created)

@router.get("/account-deletion-request", response_model=AccountDeletionRequest | None)
async def get_my_deletion_request(current_user: UserInDB = Depends(get_current_user)):
    if current_user.role != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only admins can view deletion requests")
    req = await database.db.account_deletion_requests.find_one({
        "requester_user_id": current_user.id,
        "status": {"$in": ["pending", "rejected", "approved"]}
    }, sort=[("created_at", -1)])
    if not req:
        return None
    return AccountDeletionRequest.from_mongo(req)