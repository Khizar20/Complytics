from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPBearer
from schemas.users import UserInDB
from utils.security import get_current_user, generate_random_password,send_credentials_email
from db import database
from typing import List
from schemas.users import UserCreate
from utils.security import get_password_hash
from datetime import datetime



router = APIRouter()
security = HTTPBearer()

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
    
    # Get all team members and convert ObjectId to string
    team_members = await database.db.users.find(
        {"role": "team_member"}
    ).to_list(None)
    
    # Explicit conversion of MongoDB documents
    converted_members = []
    for member in team_members:
        member["_id"] = str(member["_id"])  # Convert ObjectId to string
        converted_members.append(UserInDB(**member))
    
    return converted_members  

@router.post("/create-team-member", response_model=UserInDB)
async def create_team_member(
    user_data: UserCreate,
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
    
    # Check if email exists
    if await database.db.users.find_one({"email": user_data.email}):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
    
    # Generate random password
    temp_password = generate_random_password()
    
    # Create team member
    user_dict = user_data.model_dump(exclude={"password"})
    user_dict["password_hash"] = get_password_hash(temp_password)
    user_dict["role"] = "team_member"
    user_dict["organization_id"] = current_user.organization_id
    user_dict["created_by"] = current_user.id
    user_dict["is_active"] = True
    user_dict["created_at"] = datetime.utcnow()
    user_dict["updated_at"] = datetime.utcnow()
    
    result = await database.db.users.insert_one(user_dict)
    created_user = await database.db.users.find_one({"_id": result.inserted_id})
    
    # Send email with credentials
    org = await database.db.organizations.find_one({"_id": current_user.organization_id})
    await send_credentials_email(
        email=user_data.email,
        username=user_data.email,
        password=temp_password,
        organization_name=org["name"]
    )
    
    return UserInDB.from_mongo(created_user)