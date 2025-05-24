from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import HTTPBearer
from typing import Optional
from pydantic import BaseModel
from db import database
from schemas.users import UserRole, UserInDB
from utils.security import get_current_user
from bson import ObjectId

router = APIRouter()
security = HTTPBearer()

class UserData(BaseModel):
    email: str
    role: UserRole
    team: Optional[str] = None

@router.get("/user-data", response_model=UserData)
async def get_user_data(current_user: UserInDB = Depends(get_current_user)):
    try:
        # Convert string ID to ObjectId if needed
        user_id = ObjectId(current_user.id) if isinstance(current_user.id, str) else current_user.id
        
        # Get user data from database
        user = await database.db.users.find_one({"_id": user_id})
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        # Convert role to lowercase to match enum
        role = user["role"].lower()
        if role not in [r.value for r in UserRole]:
            raise HTTPException(status_code=500, detail=f"Invalid role value: {role}")
        
        return UserData(
            email=user["email"],
            role=role,
            team=user.get("team", None)
        )
    except Exception as e:
        print(f"Error in get_user_data: {str(e)}")  # Add logging
        if isinstance(e, HTTPException):
            raise e
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/team-members")
async def get_team_members(team: str, current_user: UserInDB = Depends(get_current_user)):
    try:
        # Convert string ID to ObjectId if needed
        org_id = ObjectId(current_user.organization_id) if isinstance(current_user.organization_id, str) else current_user.organization_id
        
        # Get team members from database
        team_members = await database.db.users.find({
            "organization_id": org_id,
            "team": team
        }).to_list(length=None)
        
        return [
            {
                "email": member["email"],
                "name": f"{member['first_name']} {member['last_name']}",
                "role": member["role"].lower()  # Convert role to lowercase
            }
            for member in team_members
        ]
    except Exception as e:
        print(f"Error in get_team_members: {str(e)}")  # Add logging
        if isinstance(e, HTTPException):
            raise e
        raise HTTPException(status_code=500, detail=str(e)) 