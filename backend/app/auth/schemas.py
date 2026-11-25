from pydantic import BaseModel, EmailStr, Field, ConfigDict, SecretStr, field_validator
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


class ChangePasswordRequest(BaseModel):
  model_config = ConfigDict(extra='forbid')

  current_password: SecretStr = Field(min_length=1)
  new_password: SecretStr = Field(min_length=8, max_length=128)

  @field_validator('new_password')
  @classmethod
  def nonblank_password(cls, value):
    if not value.get_secret_value().strip():
      raise ValueError('Password must not be blank')
    return value
