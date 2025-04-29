from enum import Enum
from pydantic import BaseModel, EmailStr, Field, ConfigDict
from typing import Optional
from datetime import datetime
from bson import ObjectId
from pydantic import field_validator


class UserRole(str, Enum):
    SUPERADMIN = "superadmin"
    ADMIN = "admin"
    COMPLIANCE_TEAM = "compliance_team"
    IT_TEAM = "it_team"
    MANAGEMENT_TEAM = "management_team"

class OrganizationBase(BaseModel):
    name: str
    domain: str
    is_active: bool = False

class OrganizationCreate(OrganizationBase):
    pass

class OrganizationInDB(OrganizationBase):
    model_config = ConfigDict(arbitrary_types_allowed=True)
    
    id: str = Field(..., alias="_id")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    created_by: Optional[str] = None

    @classmethod
    def from_mongo(cls, data: dict):
        if not data:
            return None
        data["_id"] = str(data["_id"])
        return cls(**data)

class UserBase(BaseModel):
    email: EmailStr
    first_name: str
    last_name: str

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
    user_data: UserCreate
    is_approved: bool = False
    approved_by: Optional[str] = None
    approved_at: Optional[datetime] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)

    @classmethod
    def from_mongo(cls, data: dict):
        if not data:
            return None
        result = data.copy()
        if "_id" in result:
            result["_id"] = str(result["_id"])
        if "user_data" in result and isinstance(result["user_data"], dict):
            result["user_data"] = UserCreate(**result["user_data"])
        return cls(**result)