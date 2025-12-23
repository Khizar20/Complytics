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
        # Decode token and get role first to check if expiration should be ignored
        payload_unverified = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM], options={"verify_exp": False})
        role = payload_unverified.get("role")
        
        # For superadmin, admin, compliance_team, it_team, and management_team, ignore expiration
        # For other roles, verify expiration normally
        if role in ("superadmin", "admin", "compliance_team", "it_team", "management_team"):
            payload = payload_unverified  # Use unverified payload (expiration ignored)
        else:
            # Verify expiration for other roles
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
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <style>
            body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif; line-height: 1.6; color: #1f2937; margin: 0; padding: 0; background-color: #f3f4f6; }}
            .email-container {{ max-width: 600px; margin: 0 auto; background-color: #ffffff; }}
            .header {{ background: linear-gradient(135deg, #1e3a8a 0%, #2563eb 50%, #06b6d4 100%); color: white; padding: 40px 30px; text-align: center; }}
            .header h1 {{ margin: 0; font-size: 28px; font-weight: 700; font-family: 'Montserrat', sans-serif; }}
            .header p {{ margin: 10px 0 0 0; opacity: 0.95; font-size: 16px; }}
            .content {{ padding: 40px 30px; }}
            .greeting {{ font-size: 18px; color: #1f2937; margin-bottom: 20px; }}
            .info-box {{ background: #f9fafb; border-left: 4px solid #2563eb; padding: 20px; margin: 25px 0; border-radius: 8px; }}
            .info-item {{ margin: 12px 0; font-size: 15px; }}
            .info-item strong {{ color: #1e3a8a; display: inline-block; min-width: 100px; }}
            .info-item .value {{ color: #1f2937; font-weight: 600; }}
            .password-box {{ background: #fef3c7; border: 2px solid #f59e0b; padding: 15px; border-radius: 8px; margin: 20px 0; text-align: center; }}
            .password-box .password {{ font-size: 20px; font-weight: 700; color: #1f2937; font-family: 'Courier New', monospace; letter-spacing: 2px; }}
            .warning {{ background: #fee2e2; border-left: 4px solid #ef4444; padding: 15px; margin: 25px 0; border-radius: 8px; }}
            .warning p {{ margin: 5px 0; color: #991b1b; font-size: 14px; }}
            .cta-button {{ display: inline-block; background: linear-gradient(135deg, #2563eb 0%, #06b6d4 100%); color: white; padding: 14px 32px; text-decoration: none; border-radius: 8px; font-weight: 600; margin: 25px 0; }}
            .footer {{ background: #f9fafb; padding: 30px; text-align: center; border-top: 1px solid #e5e7eb; }}
            .footer p {{ margin: 8px 0; color: #6b7280; font-size: 14px; }}
            .footer .brand {{ color: #1e3a8a; font-weight: 700; font-size: 16px; }}
        </style>
    </head>
    <body>
        <div class="email-container">
            <div class="header">
                <h1>Welcome to Complytics!</h1>
                <p>Your account has been successfully created</p>
            </div>
            <div class="content">
                <div class="greeting">
                    Dear {first_name} {last_name},
                </div>
                <p>Your user account has been created and you can now access the Complytics platform. Please find your login credentials below:</p>
                
                <div class="info-box">
                    <div class="info-item">
                        <strong>Email:</strong>
                        <span class="value">{email}</span>
                    </div>
                    <div class="info-item">
                        <strong>Role:</strong>
                        <span class="value">{role_display}</span>
                    </div>
                    {f'<div class="info-item"><strong>Organization:</strong><span class="value">{organization_name}</span></div>' if organization_name else ''}
                </div>
                
                <div class="password-box">
                    <div style="font-size: 14px; color: #92400e; margin-bottom: 8px;">Your Temporary Password</div>
                    <div class="password">{password}</div>
                </div>
                
                <div class="warning">
                    <p><strong>🔒 Security Notice:</strong></p>
                    <p>Please change your password immediately after your first login for security purposes.</p>
                </div>
                
                <div style="text-align: center;">
                    <a href="#" class="cta-button">Login to Dashboard</a>
                </div>
                
                <p style="margin-top: 30px; color: #6b7280; font-size: 14px;">
                    If you have any questions or need assistance, please don't hesitate to contact our support team.
                </p>
            </div>
            <div class="footer">
                <p class="brand">Complytics</p>
                <p>AI-Powered Compliance Management Platform</p>
                <p style="margin-top: 15px;">This is an automated email. Please do not reply.</p>
            </div>
        </div>
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
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <style>
            body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif; line-height: 1.6; color: #1f2937; margin: 0; padding: 0; background-color: #f3f4f6; }}
            .email-container {{ max-width: 600px; margin: 0 auto; background-color: #ffffff; }}
            .header {{ background: linear-gradient(135deg, #1e3a8a 0%, #2563eb 50%, #06b6d4 100%); color: white; padding: 40px 30px; text-align: center; }}
            .header h1 {{ margin: 0; font-size: 28px; font-weight: 700; font-family: 'Montserrat', sans-serif; }}
            .header p {{ margin: 10px 0 0 0; opacity: 0.95; font-size: 16px; }}
            .content {{ padding: 40px 30px; }}
            .greeting {{ font-size: 18px; color: #1f2937; margin-bottom: 20px; }}
            .role-change-box {{ background: #f0f9ff; border: 2px solid #06b6d4; padding: 25px; margin: 25px 0; border-radius: 8px; }}
            .role-item {{ display: flex; align-items: center; margin: 15px 0; padding: 15px; background: white; border-radius: 6px; }}
            .role-label {{ font-size: 13px; color: #6b7280; text-transform: uppercase; font-weight: 600; letter-spacing: 0.5px; min-width: 120px; }}
            .role-value {{ font-size: 18px; font-weight: 700; color: #1e3a8a; }}
            .arrow {{ margin: 0 20px; color: #06b6d4; font-size: 24px; font-weight: bold; }}
            .info-box {{ background: #f9fafb; border-left: 4px solid #2563eb; padding: 20px; margin: 25px 0; border-radius: 8px; }}
            .info-box p {{ margin: 8px 0; color: #374151; font-size: 15px; }}
            .footer {{ background: #f9fafb; padding: 30px; text-align: center; border-top: 1px solid #e5e7eb; }}
            .footer p {{ margin: 8px 0; color: #6b7280; font-size: 14px; }}
            .footer .brand {{ color: #1e3a8a; font-weight: 700; font-size: 16px; }}
        </style>
    </head>
    <body>
        <div class="email-container">
            <div class="header">
                <h1>Role Update Notification</h1>
                <p>Your account permissions have been updated</p>
            </div>
            <div class="content">
                <div class="greeting">
                    Dear {first_name} {last_name},
                </div>
                <p>Your role in Complytics has been updated. This change may affect your access and permissions within the system.</p>
                
                <div class="role-change-box">
                    <div class="role-item">
                        <div class="role-label">Previous Role</div>
                        <div class="arrow">→</div>
                        <div class="role-value">{old_role_display}</div>
                    </div>
                    <div class="role-item" style="background: linear-gradient(135deg, #eff6ff 0%, #e0f2fe 100%); border: 2px solid #06b6d4;">
                        <div class="role-label">New Role</div>
                        <div class="arrow">→</div>
                        <div class="role-value" style="color: #06b6d4;">{new_role_display}</div>
                    </div>
                </div>
                
                <div class="info-box">
                    <p><strong>What this means:</strong></p>
                    <p>Your new role grants you different access levels and permissions. You may notice changes in:</p>
                    <ul style="margin: 10px 0; padding-left: 20px; color: #374151;">
                        <li>Available features and modules</li>
                        <li>Data access and visibility</li>
                        <li>Action permissions</li>
                    </ul>
                </div>
                
                <p style="margin-top: 30px; color: #6b7280; font-size: 14px;">
                    If you have any questions about your new role or need assistance, please contact your organization administrator.
                </p>
            </div>
            <div class="footer">
                <p class="brand">Complytics</p>
                <p>AI-Powered Compliance Management Platform</p>
                <p style="margin-top: 15px;">This is an automated email. Please do not reply.</p>
            </div>
        </div>
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

async def send_forgot_password_email(
    email: str,
    password: str,
    first_name: str,
    last_name: str,
    role: str
):
    """Send forgot password email with new credentials"""
    subject = "Your Complytics Account - Password Reset"
    
    # Format the role for display
    role_display = role.replace('_', ' ').title()
    
    body = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <style>
            body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif; line-height: 1.6; color: #1f2937; margin: 0; padding: 0; background-color: #f3f4f6; }}
            .email-container {{ max-width: 600px; margin: 0 auto; background-color: #ffffff; }}
            .header {{ background: linear-gradient(135deg, #1e3a8a 0%, #2563eb 50%, #06b6d4 100%); color: white; padding: 40px 30px; text-align: center; }}
            .header h1 {{ margin: 0; font-size: 28px; font-weight: 700; font-family: 'Montserrat', sans-serif; }}
            .header p {{ margin: 10px 0 0 0; opacity: 0.95; font-size: 16px; }}
            .content {{ padding: 40px 30px; }}
            .greeting {{ font-size: 18px; color: #1f2937; margin-bottom: 20px; }}
            .info-box {{ background: #f9fafb; border-left: 4px solid #2563eb; padding: 20px; margin: 25px 0; border-radius: 8px; }}
            .info-item {{ margin: 12px 0; font-size: 15px; }}
            .info-item strong {{ color: #1e3a8a; display: inline-block; min-width: 100px; }}
            .info-item .value {{ color: #1f2937; font-weight: 600; }}
            .password-box {{ background: #fef3c7; border: 2px solid #f59e0b; padding: 15px; border-radius: 8px; margin: 20px 0; text-align: center; }}
            .password-box .password {{ font-size: 20px; font-weight: 700; color: #1f2937; font-family: 'Courier New', monospace; letter-spacing: 2px; }}
            .security-warning {{ background: #fee2e2; border: 2px solid #ef4444; padding: 20px; margin: 25px 0; border-radius: 8px; }}
            .security-warning h3 {{ margin: 0 0 12px 0; color: #991b1b; font-size: 16px; }}
            .security-warning ul {{ margin: 10px 0; padding-left: 20px; color: #991b1b; }}
            .security-warning li {{ margin: 8px 0; font-size: 14px; }}
            .cta-button {{ display: inline-block; background: linear-gradient(135deg, #2563eb 0%, #06b6d4 100%); color: white; padding: 14px 32px; text-decoration: none; border-radius: 8px; font-weight: 600; margin: 25px 0; }}
            .footer {{ background: #f9fafb; padding: 30px; text-align: center; border-top: 1px solid #e5e7eb; }}
            .footer p {{ margin: 8px 0; color: #6b7280; font-size: 14px; }}
            .footer .brand {{ color: #1e3a8a; font-weight: 700; font-size: 16px; }}
        </style>
    </head>
    <body>
        <div class="email-container">
            <div class="header">
                <h1>🔒 Password Reset Confirmation</h1>
                <p>Your account credentials have been updated</p>
            </div>
            <div class="content">
                <div class="greeting">
                    Dear {first_name} {last_name},
                </div>
                <p>We received a request to reset your password for your Complytics account. Your account has been updated with new credentials.</p>
                
                <div class="info-box">
                    <div class="info-item">
                        <strong>Email:</strong>
                        <span class="value">{email}</span>
                    </div>
                    <div class="info-item">
                        <strong>Role:</strong>
                        <span class="value">{role_display}</span>
                    </div>
                </div>
                
                <div class="password-box">
                    <div style="font-size: 14px; color: #92400e; margin-bottom: 8px;">Your New Temporary Password</div>
                    <div class="password">{password}</div>
                </div>
                
                <div class="security-warning">
                    <h3>⚠️ Important Security Notice</h3>
                    <ul>
                        <li><strong>Change immediately:</strong> Please change your password immediately after logging in for security purposes.</li>
                        <li><strong>Didn't request this?</strong> If you did not request this password reset, please contact your administrator immediately.</li>
                        <li><strong>Keep it secure:</strong> Never share your password with anyone. Complytics staff will never ask for your password.</li>
                    </ul>
                </div>
                
                <div style="text-align: center;">
                    <a href="#" class="cta-button">Login to Dashboard</a>
                </div>
                
                <p style="margin-top: 30px; color: #6b7280; font-size: 14px;">
                    If you have any questions or concerns, please contact our support team immediately.
                </p>
            </div>
            <div class="footer">
                <p class="brand">Complytics</p>
                <p>AI-Powered Compliance Management Platform</p>
                <p style="margin-top: 15px;">This is an automated email. Please do not reply.</p>
            </div>
        </div>
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

async def send_simple_email(
    to_email: str,
    subject: str,
    html_body: str
):
    message = MIMEMultipart()
    message["From"] = settings.SMTP_FROM_EMAIL
    message["To"] = to_email
    message["Subject"] = subject

    message.attach(MIMEText(html_body, "html"))

    context = ssl.create_default_context()
    with smtplib.SMTP_SSL(settings.SMTP_HOST, settings.SMTP_PORT, context=context) as server:
        server.login(settings.SMTP_USERNAME, settings.SMTP_PASSWORD)
        server.send_message(message)