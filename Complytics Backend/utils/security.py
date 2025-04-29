from passlib.context import CryptContext
from jose import JWTError, jwt
from datetime import datetime, timedelta
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from config import settings
from db import database
from schemas.users import UserInDB
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import random
import string
from typing import Optional
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import ssl

security = HTTPBearer(auto_error=False)

pwd_context = CryptContext(schemes=["bcrypt"], bcrypt__rounds=12, deprecated="auto")

oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl="auth/login",
    scheme_name="JWT",
    auto_error=False
)

def verify_password(plain_password: str, hashed_password: str):
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password: str):
    return pwd_context.hash(password)

SUPERADMIN_CREDENTIALS = {
    "email": "superadmin@complytics.com",
    "password_hash": get_password_hash("Admin@123"),  # Hashed version
    "role": "superadmin",
    "is_active": True
}

async def authenticate_user(email: str, password: str):
    # 1. Check superadmin credentials
    if email == "superadmin@complytics.com" and password == "Admin@123":
        return UserInDB(
            _id="superadmin_unique_id",
            email=email,
            first_name="Super",
            last_name="Admin",
            role="superadmin",
            is_active=True,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
    
    # 2. Check database users
    user = await database.db.users.find_one({"email": email})
    if not user:
        return None
    
    # Verify password (assuming you have password hashing)
    if not verify_password(password, user["password_hash"]):
        return None
    
    return UserInDB.from_mongo(user)

def create_access_token(data: dict, expires_delta: timedelta = None):
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=15))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)

async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    token = credentials.credentials
    
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        email: str = payload.get("sub")
        if email is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authentication credentials",
            )
        
        # First check if it's the superadmin
        if email == "superadmin@complytics.com":
            return UserInDB(
                _id="superadmin_unique_id",
                email=email,
                first_name="Super",
                last_name="Admin",
                role="superadmin",
                is_active=True,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )
            
        # Then check database users
        user = await database.db.users.find_one({"email": email})
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        return UserInDB.from_mongo(user)
        
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
        )
        
def generate_random_password(length: int = 12) -> str:
    """Generate a random password with letters, digits and special chars"""
    chars = string.ascii_letters + string.digits + "!@#$%^&*"
    return ''.join(random.choice(chars) for _ in range(length))

async def send_credentials_email(
    email: str,
    username: str,
    password: str,
    organization_name: str,
    first_name: str,
    last_name: str,
    role: str
):
    subject = "Your User Account has been created"
    
    # Format the role for display
    role_display = role.replace('_', ' ').title()
    
    body = f"""
    <html>
        <body>
            <h2>Welcome to {organization_name}!</h2>
            <p>Dear {first_name} {last_name},</p>
            <p>Your user account has been created with the following details:</p>
            <ul>
                <li><strong>Email:</strong> {email}</li>
                <li><strong>Password:</strong> {password}</li>
                <li><strong>Role:</strong> {role_display}</li>
            </ul>
            <p>Please use these credentials to log in to your account. We recommend changing your password after your first login.</p>
            <p>Best regards,<br>{organization_name} Team</p>
        </body>
    </html>
    """
    
    message = MIMEMultipart()
    message["From"] = settings.SMTP_FROM_EMAIL
    message["To"] = email
    message["Subject"] = subject
    
    # Attach the HTML body
    message.attach(MIMEText(body, "html"))
    
    # Create SMTP session
    context = ssl.create_default_context()
    with smtplib.SMTP_SSL(settings.SMTP_HOST, settings.SMTP_PORT, context=context) as server:
        server.login(settings.SMTP_USERNAME, settings.SMTP_PASSWORD)
        server.send_message(message)

async def send_role_change_email(
    email: str,
    first_name: str,
    last_name: str,
    old_role: str,
    new_role: str,
    organization_name: str
):
    subject = "Your Role Has Been Updated"
    
    # Format roles for display
    old_role_display = old_role.replace('_', ' ').title()
    new_role_display = new_role.replace('_', ' ').title()
    
    body = f"""
    <html>
        <body>
            <h2>Role Update Notification</h2>
            <p>Dear {first_name} {last_name},</p>
            <p>Your role in {organization_name} has been updated:</p>
            <ul>
                <li><strong>Previous Role:</strong> {old_role_display}</li>
                <li><strong>New Role:</strong> {new_role_display}</li>
            </ul>
            <p>This change may affect your access and permissions within the system. If you have any questions about your new role, please contact your organization administrator.</p>
            <p>Best regards,<br>{organization_name} Team</p>
        </body>
    </html>
    """
    
    message = MIMEMultipart()
    message["From"] = settings.SMTP_FROM_EMAIL
    message["To"] = email
    message["Subject"] = subject
    
    # Attach the HTML body
    message.attach(MIMEText(body, "html"))
    
    # Create SMTP session
    context = ssl.create_default_context()
    with smtplib.SMTP_SSL(settings.SMTP_HOST, settings.SMTP_PORT, context=context) as server:
        server.login(settings.SMTP_USERNAME, settings.SMTP_PASSWORD)
        server.send_message(message)