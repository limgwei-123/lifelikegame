
from pydantic import BaseModel, EmailStr, Field, ConfigDict
import uuid

class UserMeResponse(BaseModel):
  model_config = ConfigDict(from_attributes=True)

  id: uuid.UUID
  email: EmailStr