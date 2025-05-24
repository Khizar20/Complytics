from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPBearer
from schemas.users import UserCreate, UserInDB, OrganizationInDB
from utils.security import get_current_user
from db import database
from typing import List
from utils.security import get_password_hash
from datetime import datetime
from superadmin_deps import get_superadmin


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