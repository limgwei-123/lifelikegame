from pydantic import BaseModel, EmailStr, Field

class SignupRequest(BaseModel):
  email: EmailStr
  password: str

class LoginRequest(BaseModel):
  email: EmailStr
  password: str

class TokenResponse(BaseModel):
  access_token: str
  token_type: str = "bearer"

class UserMeResponse(BaseModel):
  id: str
  email: EmailStr