from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPBearer
from schemas.users import UserCreate, PendingRegistration, UserInDB
from db import database
from datetime import datetime
from utils.security import generate_random_password, send_credentials_email, get_password_hash
from utils.security import get_current_user
from typing import List
from bson import ObjectId
import json
import traceback

router = APIRouter()
security = HTTPBearer()

@router.post("/register", response_model=dict)
async def register_organization_admin(user_data: UserCreate):
    try:
        # Debug: Log incoming registration attempt
        print(f"\n[DEBUG] Registration attempt for: {user_data.email}")
        print(f"Full user data: {user_data.model_dump()}")

        # Check if email exists in either users or pending registrations
        existing_user = await database.db.users.find_one({"email": user_data.email})
        existing_pending = await database.db.pending_registrations.find_one(
            {"user_data.email": user_data.email}
        )

        if existing_user:
            print(f"[WARNING] Email already registered as user: {user_data.email}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered"
            )

        if existing_pending:
            print(f"[WARNING] Email already in pending registrations: {user_data.email}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already pending approval"
            )

        # Prepare the pending registration document
        pending_reg = {
            "user_data": user_data.model_dump(),
            "is_approved": False,  # Explicitly set to False
            "approved_by": None,
            "approved_at": None,
            "created_at": datetime.utcnow()
        }

        print(f"\n[DEBUG] Prepared document for insertion:")
        print(json.dumps(pending_reg, indent=2, default=str))

        # Insert the document
        result = await database.db.pending_registrations.insert_one(pending_reg)
        
        if not result.acknowledged:
            print("[ERROR] Insert operation not acknowledged by MongoDB")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to save registration"
            )

        print(f"\n[SUCCESS] Inserted document with _id: {result.inserted_id}")

        # Verify the inserted document
        doc = await database.db.pending_registrations.find_one(
            {"_id": result.inserted_id}
        )
        
        if not doc:
            print("[ERROR] Failed to verify inserted document")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to verify registration"
            )

        print("\n[DEBUG] Verified inserted document:")
        print(json.dumps(doc, indent=2, default=str))

        # Immediate query check
        pending_count = await database.db.pending_registrations.count_documents(
            {"is_approved": False}
        )
        print(f"\n[STATUS] Current pending registrations count: {pending_count}")

        return {
            "message": "Registration submitted for approval. You'll receive an email once approved.",
            "registration_id": str(result.inserted_id)
        }

    except HTTPException:
        # Re-raise HTTP exceptions we created
        raise
    except Exception as e:
        print(f"\n[CRITICAL] Unexpected error: {str(e)}")
        print(f"Error type: {type(e).__name__}")
        traceback.print_exc()  # Print full traceback
        
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred during registration"
        )
        
@router.get("/pending-registrations", response_model=List[PendingRegistration])
async def get_pending_registrations(
    current_user: UserInDB = Depends(get_current_user)
):
    print("\n[DEBUG] Entering get_pending_registrations")  # Debug log
    print(f"Current user role: {current_user.role}")  # Debug log
    
    if current_user.role != "superadmin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only superadmins can view pending registrations"
        )
    
    # Debug: Count pending registrations before query
    pending_count = await database.db.pending_registrations.count_documents(
        {"is_approved": False}
    )
    print(f"[DEBUG] Found {pending_count} pending registrations")  # Debug log
    
    # Get all pending registrations
    cursor = database.db.pending_registrations.find({"is_approved": False})
    pending = []
    
    async for doc in cursor:
        print(f"\n[DEBUG] Raw MongoDB document:")  # Debug log
        print(doc)  # Debug log
        # Convert MongoDB document
        doc["_id"] = str(doc["_id"])
        pending.append(doc)
    
    print(f"\n[DEBUG] Returning {len(pending)} pending registrations")  # Debug log
    return pending

@router.post("/approve-registration/{registration_id}", response_model=UserInDB)
async def approve_registration(
    registration_id: str,
    current_user: UserInDB = Depends(get_current_user)
):
    try:
        # Convert string ID to ObjectId
        obj_id = ObjectId(registration_id)
    except:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid registration ID format"
        )

    # Find and DELETE the pending registration in one atomic operation
    pending = await database.db.pending_registrations.find_one_and_delete({"_id": obj_id})
    if not pending:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Registration not found"
        )
    
    # Check if user already exists
    existing_user = await database.db.users.find_one({"email": pending["user_data"]["email"]})
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User with this email already exists"
        )

    try:
        # Create organization first
        org_data = {
            "name": pending["user_data"]["organization_name"],
            "domain": pending["user_data"]["organization_domain"],
            "is_active": True,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
            "created_by": current_user.id
        }
        org_result = await database.db.organizations.insert_one(org_data)
        
        # Generate random password
        temp_password = generate_random_password()
        
        # Create admin user
        user_dict = pending["user_data"].copy()
        user_dict["password_hash"] = get_password_hash(temp_password)
        user_dict["role"] = "admin"
        user_dict["organization_id"] = str(org_result.inserted_id)
        user_dict["is_active"] = True
        user_dict["created_at"] = datetime.utcnow()
        user_dict["updated_at"] = datetime.utcnow()
        user_dict["created_by"] = current_user.id
        
        # Create user (no need to update pending registration since we deleted it)
        user_result = await database.db.users.insert_one(user_dict)
        
        # Get the created user
        created_user = await database.db.users.find_one({"_id": user_result.inserted_id})
        if not created_user:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to retrieve created user"
            )
        
        # Send email with credentials
        try:
            await send_credentials_email(
                email=created_user["email"],
                username=created_user["email"],
                password=temp_password,
                organization_name=org_data["name"],
                first_name=created_user["first_name"],
                last_name=created_user["last_name"],
                role=created_user["role"]
            )
        except Exception as email_error:
            # Log the email error but don't fail the whole operation
            print(f"Failed to send email: {str(email_error)}")
            # Consider adding to a retry queue in production
        
        return UserInDB.from_mongo(created_user)
        
    except Exception as e:
        # Clean up any partially created data
        if 'org_result' in locals():
            await database.db.organizations.delete_one({"_id": org_result.inserted_id})
        if 'user_result' in locals():
            await database.db.users.delete_one({"_id": user_result.inserted_id})
        
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to approve registration: {str(e)}"
        )