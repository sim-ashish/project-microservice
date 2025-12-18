import os
import jwt
from fastapi import FastAPI, HTTPException, Depends, status
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
from fastapi.security import OAuth2PasswordRequestForm
from utils import authenticate_user, create_access_token, get_current_user, oauth2_scheme, hash_password
from database import get_db
from sqlalchemy.orm import Session
from models import Group, User as UserModel

from schemas import LoginData, RegisterUser, User, TokenData, RefreshTokenData, GroupCreate, GroupResponse, GroupMemberAction
from redis_client import publish_to_redis, close_redis

load_dotenv()

SECRET_KEY = os.getenv("SECRET_KEY")
ALGORITHM = os.getenv("ALGORITHM")

app = FastAPI()

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins in development
    allow_credentials=True,
    allow_methods=["*"],  # Allow all methods
    allow_headers=["*"],  # Allow all headers
)

@app.post("/register", response_model=User)
def register(user_data: RegisterUser, db: Session = Depends(get_db)):
    """
    Register a new user.
    Checks if email already exists and creates a new user with bcrypt hashed password.
    """
    # Check if user already exists
    existing_user = db.query(UserModel).filter(UserModel.email == user_data.email).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
    
    # Hash the password using bcrypt
    hashed_password = hash_password(user_data.password)
    
    # Create new user
    new_user = UserModel(
        email=user_data.email,
        name=user_data.name,
        password=hashed_password
    )
    
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    
    return User(
        id=new_user.id,
        email=new_user.email,
        name=new_user.name,
        created_at=new_user.created_at.isoformat(),
        updated_at=new_user.updated_at.isoformat()
    )


@app.post("/login", response_model=TokenData)
def login(data: LoginData, db: Session = Depends(get_db)):
    """
    Login with email and password.
    Returns JWT access token on successful authentication.
    """
    user = authenticate_user(data, db)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
        )
    token = create_access_token(data={"sub": user["email"]})
    return TokenData(access_token=token, token_type="bearer")

@app.get("/verify-token")
@app.post("/verify-token")
def verify_token(token: str = Depends(oauth2_scheme)):
    """
    Verify JWT token validity.
    Uses oauth2_scheme to automatically extract and validate token from Authorization header.
    Supports both GET and POST methods for nginx auth_request compatibility.
    """
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return {"valid": True, "user": payload["sub"]}
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token expired"
        )
    except jwt.InvalidTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token"
        )


@app.post("/token", response_model=TokenData)
async def login_for_access_token(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db)
):
    """
    OAuth2 compatible token endpoint.
    Used by Swagger UI for authentication.
    """
    user = authenticate_user(LoginData(email=form_data.username, password=form_data.password), db)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
        )

    token = create_access_token(data={"sub": user["email"]})
    return TokenData(access_token=token, token_type="bearer")


# ========================================================= Protected Routes =======================================================
@app.get("/users/me")
def read_users_me(current_user: dict = Depends(get_current_user)):
    return current_user


@app.post("/groups", response_model=GroupResponse)
def create_group(
    group_data: GroupCreate,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Create a new group.
    Requires authentication. The created_by field is automatically set from the authenticated user.
    The creator is automatically added as a member of the group.
    """
    # Get the user from database
    user = db.query(UserModel).filter(UserModel.email == current_user["email"]).first()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Create new group with authenticated user's ID
    new_group = Group(
        name=group_data.name,
        description=group_data.description,
        created_by=user.id
    )
    
    # Add the creator as a member of the group
    new_group.members.append(user)
    
    db.add(new_group)
    db.commit()
    db.refresh(new_group)
    
    return GroupResponse(
        id=new_group.id,
        name=new_group.name,
        description=new_group.description,
        created_by=user.email,
        created_at=new_group.created_at.isoformat(),
        updated_at=new_group.updated_at.isoformat()
    )

@app.get("/verify-group-access/{group_id}")
def verify_group_access(
    group_id: int,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Verify if the authenticated user is a member of the specified group.
    Returns 200 if user is a member, 403 if not.
    """
    # Get the user from database
    user = db.query(UserModel).filter(UserModel.email == current_user["email"]).first()
    print(current_user, group_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Check if group exists
    group = db.query(Group).filter(Group.id == group_id).first()
    if not group:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Group not found"
        )
    
    # Check if user is a member of the group
    is_member = user in group.members
    
    if not is_member:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not a member of this group"
        )
    
    return {
        "valid": True,
        "user": user.email,
        "group_id": group_id,
        "group_name": group.name
    }

@app.get("/groups")
def get_user_groups(
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get all groups the authenticated user is a member of.
    """
    user = db.query(UserModel).filter(UserModel.email == current_user["email"]).first()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    groups = [
        GroupResponse(
            id=group.id,
            name=group.name,
            description=group.description,
            created_by=group.creator.email,
            created_at=group.created_at.isoformat(),
            updated_at=group.updated_at.isoformat()
        )
        for group in user.groups
    ]
    
    return {"groups": groups}


@app.post("/groups/{group_id}/members")
async def add_member_to_group(
    group_id: int,
    member_data: GroupMemberAction,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Add a user to a group.
    Only the group creator can add members.
    """
    # Get the current user
    current_user_obj = db.query(UserModel).filter(UserModel.email == current_user["email"]).first()
    
    if not current_user_obj:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Current user not found"
        )
    
    # Check if group exists
    group = db.query(Group).filter(Group.id == group_id).first()
    if not group:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Group not found"
        )
    
    # Check if current user is the creator of the group
    if group.created_by != current_user_obj.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the group creator can add members"
        )
    
    # Find the user to add
    user_to_add = db.query(UserModel).filter(UserModel.email == member_data.user_email).first()
    if not user_to_add:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User with email {member_data.user_email} not found"
        )
    
    # Check if user is already a member
    if user_to_add in group.members:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"User {member_data.user_email} is already a member of this group"
        )
    
    # Add user to group
    group.members.append(user_to_add)
    db.commit()
    
    # Publish to Redis for real-time notification
    await publish_to_redis(
        "added_to_group",
        {
            "type": "add",
            "group_id": group_id,
            "user_email": member_data.user_email,
            "text": f"{user_to_add.name} ({member_data.user_email}) was added to {group.name}",
            "added_by": current_user["email"]
        }
    )
    
    return {
        "message": f"User {member_data.user_email} added to group successfully",
        "group_id": group_id,
        "group_name": group.name,
        "member_email": member_data.user_email
    }


@app.delete("/groups/{group_id}/members")
async def remove_member_from_group(
    group_id: int,
    member_data: GroupMemberAction,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Remove a user from a group.
    Only the group creator can remove members.
    Users cannot remove themselves if they are the creator.
    """
    # Get the current user
    current_user_obj = db.query(UserModel).filter(UserModel.email == current_user["email"]).first()
    
    if not current_user_obj:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Current user not found"
        )
    
    # Check if group exists
    group = db.query(Group).filter(Group.id == group_id).first()
    if not group:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Group not found"
        )
    
    # Check if current user is the creator of the group
    if group.created_by != current_user_obj.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the group creator can remove members"
        )
    
    # Find the user to remove
    user_to_remove = db.query(UserModel).filter(UserModel.email == member_data.user_email).first()
    if not user_to_remove:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User with email {member_data.user_email} not found"
        )
    
    # Check if trying to remove the creator
    if user_to_remove.id == group.created_by:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot remove the group creator from the group"
        )
    
    # Check if user is a member
    if user_to_remove not in group.members:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"User {member_data.user_email} is not a member of this group"
        )
    
    # Remove user from group
    group.members.remove(user_to_remove)
    db.commit()
    
    # Publish to Redis for real-time notification
    await publish_to_redis(
        "remove_from_group",
        {
            "type": "leave",
            "group_id": group_id,
            "user_email": member_data.user_email,
            "text": f"{user_to_remove.name} ({member_data.user_email}) was removed from {group.name}",
            "removed_by": current_user["email"]
        }
    )
    
    return {
        "message": f"User {member_data.user_email} removed from group successfully",
        "group_id": group_id,
        "group_name": group.name,
        "removed_email": member_data.user_email
    }


@app.on_event("shutdown")
async def shutdown_event():
    """Close Redis connection on shutdown"""
    await close_redis()