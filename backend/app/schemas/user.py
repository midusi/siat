from pydantic import BaseModel, ConfigDict, EmailStr, field_validator
from enum import Enum

class Role(str, Enum):
    Admin = "ROLE_ADMIN"
    Operador = "ROLE_OPERADOR"
    
class UserCreateRequest(BaseModel):
    username: str
    password: str
    confirm_password: str
    email: EmailStr
    role: Role
    first_name: str
    last_name: str
    active: bool = True

class UserUpdateRequest(BaseModel):
    email: EmailStr | None = None
    role: Role | None = None
    first_name: str | None = None
    last_name: str | None = None

class AdminResetPasswordRequest(BaseModel):
    new_password: str
    confirm_password: str

class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str
    confirm_password: str

class UserProfileUpdateRequest(BaseModel):
    first_name: str | None = None
    last_name: str | None = None
    email: EmailStr | None = None
    
class UserLoginRequest(BaseModel):
    username: str
    password: str
    
class UserResponse(BaseModel):
    id: int
    username: str
    email: str
    role: Role
    first_name: str
    last_name: str
    active: bool = True
        
    model_config = ConfigDict(from_attributes=True)