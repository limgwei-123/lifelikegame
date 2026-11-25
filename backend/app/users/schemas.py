
from typing import Literal
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError
from pydantic import BaseModel, EmailStr, Field, ConfigDict, field_validator, model_validator
import uuid

class UserMeResponse(BaseModel):
  model_config = ConfigDict(from_attributes=True)

  id: uuid.UUID
  email: EmailStr
  current_value: int
  display_name: str | None = None
  avatar_key: str = 'leaf'
  timezone: str


class UpdateProfileRequest(BaseModel):
  model_config = ConfigDict(extra='forbid')

  display_name: str | None = Field(default=None, max_length=30)
  avatar_key: Literal['leaf', 'tree', 'sun', 'book'] | None = None
  timezone: str | None = Field(default=None, max_length=64)

  @field_validator('display_name', mode='before')
  @classmethod
  def clean_name(cls, value):
    if isinstance(value, str):
      value = value.strip()
      if not value:
        raise ValueError('Display name must not be blank')
    return value

  @field_validator('avatar_key', 'timezone')
  @classmethod
  def require_value(cls, value):
    if value is None:
      raise ValueError('Value must not be null')
    return value

  @field_validator('timezone')
  @classmethod
  def valid_timezone(cls, value):
    try:
      ZoneInfo(value)
    except (ZoneInfoNotFoundError, ValueError):
      raise ValueError('Unknown timezone') from None
    return value

  @model_validator(mode='after')
  def require_changes(self):
    if not self.model_fields_set:
      raise ValueError('Provide at least one profile field')
    return self
