from pydantic import BaseModel, Field
from typing import Optional, Any
from datetime import datetime
from app.models.contract import ContractStatus, ContractType

class ContractCreate(BaseModel):
    title: str = Field(..., min_length=2, max_length=500)
    contract_type: ContractType = ContractType.OTHER
    description: Optional[str] = None
    party_a: Optional[str] = None
    party_b: Optional[str] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    contract_text: Optional[str] = None

class ContractUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=2, max_length=500)
    contract_type: Optional[ContractType] = None
    description: Optional[str] = None
    party_a: Optional[str] = None
    party_b: Optional[str] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    contract_text: Optional[str] = None

class ContractStatusUpdate(BaseModel):
    status: ContractStatus

class ContractResponse(BaseModel):
    id: str
    title: str
    contract_type: ContractType
    status: ContractStatus
    description: Optional[str]
    party_a: Optional[str]
    party_b: Optional[str]
    start_date: Optional[datetime]
    end_date: Optional[datetime]
    file_url: Optional[str]
    file_name: Optional[str]
    ai_analysis: Optional[Any]
    ai_analyzed_at: Optional[datetime]
    company_id: str
    created_by_id: str
    created_at: datetime
    updated_at: Optional[datetime]

    model_config = {"from_attributes": True}

class ContractListResponse(BaseModel):
    contracts: list[ContractResponse]
    total: int
    page: int
    limit: int
