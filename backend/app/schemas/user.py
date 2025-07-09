from pydantic import BaseModel, ConfigDict, EmailStr
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