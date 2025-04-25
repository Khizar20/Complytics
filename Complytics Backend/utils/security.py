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

async def send_credentials_email(email: str, username: str, password: str, organization_name: str):
    """Send email with login credentials using Gmail SMTP"""
    subject = f"Your Complytics Admin Account Credentials"
    
    body = f"""
        <html>
        <head>
            <style type="text/css">
                body {{
                    font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                    line-height: 1.6;
                    color: #333333;
                    max-width: 600px;
                    margin: 0 auto;
                    padding: 20px;
                }}
                .header {{
                    text-align: center;
                    padding: 20px 0;
                    border-bottom: 1px solid #eaeaea;
                    margin-bottom: 30px;
                }}
                .logo {{
                    max-width: 150px;
                    height: auto;
                }}
                .content-card {{
                    background-color: #ffffff;
                    border-radius: 8px;
                    padding: 25px;
                    margin: 20px 0;
                    box-shadow: 0 2px 10px rgba(0, 0, 0, 0.05);
                }}
                .credentials {{
                    background-color: #f8f9fa;
                    border-left: 4px solid #3b82f6;
                    padding: 15px;
                    margin: 20px 0;
                    border-radius: 4px;
                }}
                .button {{
                    display: inline-block;
                    padding: 12px 24px;
                    background-color: #3b82f6;
                    color: white !important;
                    text-decoration: none;
                    border-radius: 4px;
                    font-weight: 500;
                    margin: 15px 0;
                }}
                .footer {{
                    margin-top: 30px;
                    padding-top: 20px;
                    border-top: 1px solid #eaeaea;
                    font-size: 12px;
                    color: #6b7280;
                    text-align: center;
                }}
                .important-note {{
                    background-color: #fef2f2;
                    color: #b91c1c;
                    padding: 12px;
                    border-radius: 4px;
                    margin: 20px 0;
                }}
            </style>
        </head>
        <body>
            <div class="header">
                <!-- Replace with your actual logo URL -->
                <img src="https://raw.githubusercontent.com/Khizar20/Complytics-Frontend/refs/heads/main/complytics.png" alt="Complytics Logo" class="logo">
            </div>
            
            <div class="content-card">
                <h2 style="color: #1e40af; margin-top: 0;">Welcome to Complytics!</h2>
                <p>Your administrator account has been successfully created. Below are your login credentials:</p>
                
                <div class="credentials">
                    <p style="margin: 5px 0;"><strong>Email/Username:</strong> {username}</p>
                    <p style="margin: 5px 0;"><strong>Temporary Password:</strong> {password}</p>
                </div>
                
                <div style="text-align: center; margin: 25px 0;">
                    <a href="https://app.complytics.com/login" class="button">Login to Your Account</a>
                </div>
                
                <div class="important-note">
                    <p style="margin: 0;"><strong>⚠️ Security Notice:</strong> For your account security, please change this temporary password immediately after logging in.</p>
                </div>
                
                <p>If you didn't request this account, please contact our support team immediately.</p>
            </div>
            
            <div class="footer">
                <p>© {datetime.now().year} Complytics. All rights reserved.</p>
                <p>
                    <a href="https://complytics.com" style="color: #6b7280; text-decoration: none;">Website</a> | 
                    <a href="https://complytics.com/privacy" style="color: #6b7280; text-decoration: none;">Privacy Policy</a> | 
                    <a href="https://complytics.com/contact" style="color: #6b7280; text-decoration: none;">Contact Us</a>
                </p>
                <p>This email was sent to {email}. Please do not reply to this message.</p>
            </div>
        </body>
        </html>
        """
    
    # Create message container
    msg = MIMEMultipart('alternative')
    msg['Subject'] = subject
    msg['From'] = "khizarahmed3@gmail.com"
    msg['To'] = email
    
    # Attach HTML version
    msg.attach(MIMEText(body, 'html'))
    
    try:
        # Connect to Gmail SMTP server
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
            server.login("khizarahmed3@gmail.com", settings.SMTP_PASSWORD)
            server.send_message(msg)
        return True
    except Exception as e:
        print(f"Failed to send email: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to send credentials email"
        )