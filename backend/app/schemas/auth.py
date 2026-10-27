from pydantic import BaseModel

class ResetRequest(BaseModel):
    identifier: str  # username or email

class ResetPerform(BaseModel):
    token: str
    new_password: str
    confirm_password: str
