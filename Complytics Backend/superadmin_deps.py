from fastapi import Depends, HTTPException, status
from schemas.users import UserInDB
from utils.security import get_current_user

async def get_superadmin(current_user: UserInDB = Depends(get_current_user)):
    if current_user.role != "superadmin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Superadmin privileges required"
        )
    return current_user