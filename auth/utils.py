import os
from datetime import datetime, timedelta, timezone
import bcrypt

from fastapi import Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordBearer
from fastapi.openapi.models import OAuthFlows as OAuthFlowsModel
from fastapi.security.utils import get_authorization_scheme_param
# from jose import jwt, JWTError
import jwt
from dotenv import load_dotenv
from sqlalchemy.orm import Session
from schemas import LoginData

# Load environment variables
load_dotenv()

# Security settings
SECRET_KEY = os.getenv("SECRET_KEY")
ALGORITHM = os.getenv("ALGORITHM", "HS256").strip('"')
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", 30))


class CustomOAuth2PasswordBearer(OAuth2PasswordBearer):
    async def __call__(self, request: Request) -> str:
        authorization: str = request.headers.get("Authorization")
        scheme, param = get_authorization_scheme_param(authorization)
        
        if not authorization or scheme.lower() != "bearer":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication token is missing or invalid. Please provide a valid Bearer token.",
                headers={"WWW-Authenticate": "Bearer"},
            )
        return param


# OAuth2 scheme for token authentication
oauth2_scheme = CustomOAuth2PasswordBearer(tokenUrl="token")


# ==================== Password Hashing Utils ====================

def hash_password(password: str) -> str:
    """
    Hash a password using bcrypt.
    
    Args:
        password: Plain text password
        
    Returns:
        Hashed password string
    """
    # Generate salt and hash password
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password.encode('utf-8'), salt)
    return hashed.decode('utf-8')


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verify a password against its hash.
    
    Args:
        plain_password: Plain text password to verify
        hashed_password: Hashed password from database
        
    Returns:
        True if password matches, False otherwise
    """
    return bcrypt.checkpw(plain_password.encode('utf-8'), hashed_password.encode('utf-8'))


def authenticate_user(user: LoginData, db: Session = None):
    """
    Authenticate user with email and password.
    If db is not provided, uses hardcoded demo credentials for backward compatibility.
    """
    # If no database session provided, use demo authentication
    if db is None:
        if user.email == "testuser@example.com" and user.password == "testpass":
            return {"email": user.email}
        return None
    
    # Query user from database
    from models import User as UserModel
    db_user = db.query(UserModel).filter(UserModel.email == user.email).first()
    
    if not db_user:
        return None
    
    # Verify password using bcrypt
    if not verify_password(user.password, db_user.password):
        return None
    
    return {"email": db_user.email, "id": db_user.id, "name": db_user.name}


def get_current_user(token: str = Depends(oauth2_scheme)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or expired authentication token. Please login again.",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_email = payload.get("sub")
        if user_email is None:
            raise credentials_exception
        return {"email": user_email}
    except jwt.ExpiredSignatureError:
        raise credentials_exception
    
def create_access_token(data: dict):
    """
    Create a JWT access token.
    
    Args:
        data: Dictionary containing claims to encode in token
        
    Returns:
        Encoded JWT token string
    """
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt