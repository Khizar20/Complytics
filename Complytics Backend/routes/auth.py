from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from datetime import timedelta
from pydantic import BaseModel
from utils.security import (
    authenticate_user,
    create_access_token,
    get_current_user,
    get_password_hash,
    verify_password,
    generate_random_password,
    send_forgot_password_email
)
from schemas.users import UserInDB, PasswordChange
from config import settings
from db import database

router = APIRouter()

class ForgotPasswordRequest(BaseModel):
    email: str

@router.post("/forgot-password")
async def forgot_password(request: ForgotPasswordRequest):
    # Find user by email
    user = await database.db.users.find_one({"email": request.email})
    
    if not user:
        # Return success even if user not found for security
        return {"message": "If an account exists with this email, you will receive your credentials shortly."}
    
    # Generate a new random password
    new_password = generate_random_password()
    
    # Hash the new password
    hashed_password = get_password_hash(new_password)
    
    # Update user's password in database
    await database.db.users.update_one(
        {"email": request.email},
        {"$set": {"password_hash": hashed_password}}
    )
    
    try:
        # Send email with new credentials using the forgot password template
        await send_forgot_password_email(
            email=request.email,
            password=new_password,
            first_name=user.get("first_name", ""),
            last_name=user.get("last_name", ""),
            role=user.get("role", "user")
        )
        return {"message": "If an account exists with this email, you will receive your credentials shortly."}
    except Exception as e:
        print(f"Error sending email: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to send email"
        )

@router.post("/login", response_model=dict)
async def login(form_data: OAuth2PasswordRequestForm = Depends()):
    user = await authenticate_user(form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.email, "role": user.role},  # Include role in token
        expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}

@router.get("/me", response_model=UserInDB)
async def read_users_me(current_user: UserInDB = Depends(get_current_user)):
    return current_user

@router.put("/profile", response_model=UserInDB)
async def update_profile(
    password_change: PasswordChange,
    current_user: UserInDB = Depends(get_current_user)
):
    print(f"Received profile update request for user: {current_user.email}")
    
    # Get user from database by email
    user = await database.db.users.find_one({"email": current_user.email})
    print(f"Found user in database: {user is not None}")
    
    if not user:
        print(f"User not found in database for email: {current_user.email}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    # Verify current password
    if not verify_password(password_change.current_password, user["password_hash"]):
        print("Current password verification failed")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current password is incorrect"
        )

    print("Current password verified successfully")

    # Update password
    hashed_password = get_password_hash(password_change.new_password)
    update_result = await database.db.users.update_one(
        {"email": current_user.email},
        {"$set": {"password_hash": hashed_password}}
    )
    print(f"Password update result: {update_result.modified_count} documents modified")

    # Get updated user
    updated_user = await database.db.users.find_one({"email": current_user.email})
    print(f"Retrieved updated user: {updated_user is not None}")
    
    return UserInDB.from_mongo(updated_user)