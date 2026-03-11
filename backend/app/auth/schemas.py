from pydantic import BaseModel, EmailStr, Field, ConfigDict
import uuid

class SignupRequest(BaseModel):
  email: EmailStr
  password: str

class LoginRequest(BaseModel):
  email: EmailStr
  password: str

class TokenResponse(BaseModel):
  model_config = ConfigDict(from_attributes=True)

  access_token: str
  token_type: str = "bearer"
