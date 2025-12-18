from pydantic import BaseModel, EmailStr


class LoginData(BaseModel):
    email: EmailStr
    password: str

class RegisterUser(BaseModel):
    email: EmailStr
    name: str
    password: str

class User(BaseModel):
    id: int
    email: EmailStr
    name: str
    created_at: str
    updated_at: str

    class Config:
        orm_mode = True

class TokenData(BaseModel):
    access_token: str | None = None
    token_type: str | None = None

class RefreshTokenData(BaseModel):
    refresh_token: str


class GroupCreate(BaseModel):
    name: str
    description: str | None = None


class GroupResponse(BaseModel):
    id: int
    name: str
    description: str | None
    created_by: str  # Email of the creator
    created_at: str
    updated_at: str

    class Config:
        from_attributes = True


class GroupMemberAction(BaseModel):
    user_email: EmailStr