from enum import Enum
from pydantic import BaseModel, EmailStr, Field, ConfigDict
from typing import Optional
from datetime import datetime
from bson import ObjectId
from pydantic import field_validator


class UserRole(str, Enum):
    SUPERADMIN = "superadmin"
    ADMIN = "admin"
    TEAM_MEMBER = "team_member"

class OrganizationBase(BaseModel):
    name: str
    domain: str
    is_active: bool = False

class OrganizationInDB(OrganizationBase):
    id: str = Field(..., alias="_id")
    created_at: datetime
    updated_at: datetime

class UserBase(BaseModel):
    email: EmailStr
    first_name: str = Field(..., min_length=1)
    last_name: str = Field(..., min_length=1)

class UserCreate(UserBase):
    password: str = Field(..., min_length=8)
    organization_name: Optional[str] = None
    organization_domain: Optional[str] = None

class UserInDB(UserBase):
    model_config = ConfigDict(arbitrary_types_allowed=True)
    
    id: str = Field(..., alias="_id")
    role: UserRole
    organization_id: Optional[str] = None
    is_active: bool = True
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    created_by: Optional[str] = None

    @classmethod
    def from_mongo(cls, data: dict):
        if not data:
            return None
        data["_id"] = str(data["_id"])
        return cls(**data)

class PendingRegistration(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)
    
    id: Optional[str] = Field(None, alias="_id")
    user_data: UserCreate  # Change from dict to UserCreate
    is_approved: bool = False
    approved_by: Optional[str] = None
    approved_at: Optional[datetime] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)

    @classmethod
    def from_mongo(cls, data: dict):
        if not data:
            return None
        # Create a new dictionary to avoid modifying the original
        result = data.copy()
        # Convert ObjectId to string if exists
        if "_id" in result:
            result["_id"] = str(result["_id"])
        # Ensure user_data is properly structured
        if "user_data" in result and isinstance(result["user_data"], dict):
            result["user_data"] = UserCreate(**result["user_data"])
        return cls(**result)