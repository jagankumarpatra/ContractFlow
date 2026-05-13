from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime

class CompanyCreate(BaseModel):
    name: str = Field(..., min_length=2, max_length=255)
    domain: Optional[str] = None
    description: Optional[str] = None

class CompanyResponse(BaseModel):
    id: str
    name: str
    domain: Optional[str]
    description: Optional[str]
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}
