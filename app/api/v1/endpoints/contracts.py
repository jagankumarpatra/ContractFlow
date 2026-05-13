from fastapi import APIRouter, Depends, UploadFile, File, BackgroundTasks, Query
from sqlalchemy.orm import Session
from typing import Optional
from app.db.base import get_db
from app.models.user import User
from app.schemas.contract import (
    ContractCreate, ContractUpdate, ContractStatusUpdate,
    ContractResponse, ContractListResponse
)
from app.services import contract_service
from app.services.ai_service import analyze_contract
from app.services.s3_service import upload_contract_file
from app.utils.deps import get_current_user
from app.models.contract import Contract
from datetime import datetime
import logging

logger = logging.getLogger(__name__)
router = APIRouter()

def _run_analysis_inline(contract_id: str):
    """Run AI analysis inline (used as background task fallback)."""
    from app.db.base import SessionLocal
    from app.models.contract import Contract
    db = SessionLocal()
    try:
        contract = db.query(Contract).filter(Contract.id == contract_id).first()
        if contract and contract.contract_text:
            analysis = analyze_contract(contract.contract_text, contract.title)
            contract.ai_analysis = analysis
            contract.ai_analyzed_at = datetime.utcnow()
            db.commit()
    except Exception as e:
        logger.error(f"Inline analysis failed: {e}")
    finally:
        db.close()

@router.post("/", response_model=ContractResponse, status_code=201)
def create_contract(
    data: ContractCreate,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Create a new contract. Triggers async AI analysis if contract_text provided."""
    contract = contract_service.create_contract(data, current_user, db)
    if contract.contract_text:
        # Always use BackgroundTasks — works without Celery/Redis
        background_tasks.add_task(_run_analysis_inline, contract.id)
    return contract

@router.get("/", response_model=ContractListResponse)
def list_contracts(
    status: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """List contracts with optional filtering and search."""
    contracts, total = contract_service.list_contracts(
        current_user, db, status=status, search=search, page=page, limit=limit
    )
    return ContractListResponse(contracts=contracts, total=total, page=page, limit=limit)

@router.get("/{contract_id}", response_model=ContractResponse)
def get_contract(
    contract_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get a single contract by ID."""
    return contract_service.get_contract(contract_id, current_user, db)

@router.patch("/{contract_id}", response_model=ContractResponse)
def update_contract(
    contract_id: str,
    data: ContractUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Update contract details."""
    return contract_service.update_contract(contract_id, data, current_user, db)

@router.patch("/{contract_id}/status", response_model=ContractResponse)
def update_status(
    contract_id: str,
    data: ContractStatusUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Update contract status (follows valid transition rules)."""
    return contract_service.update_contract_status(contract_id, data, current_user, db)

@router.post("/{contract_id}/analyze", response_model=ContractResponse)
def trigger_ai_analysis(
    contract_id: str,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Manually trigger AI analysis on a contract."""
    contract = contract_service.get_contract(contract_id, current_user, db)
    background_tasks.add_task(_run_analysis_inline, contract.id)
    return contract

@router.post("/{contract_id}/upload", response_model=ContractResponse)
async def upload_file(
    contract_id: str,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Upload a contract file (PDF/text)."""
    contract = contract_service.get_contract(contract_id, current_user, db)
    content = await file.read()
    file_url = upload_contract_file(content, file.filename, current_user.company_id)
    contract.file_url = file_url
    contract.file_name = file.filename
    db.commit()
    db.refresh(contract)
    return contract

@router.delete("/{contract_id}", status_code=204)
def delete_contract(
    contract_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Delete a draft or terminated contract."""
    contract_service.delete_contract(contract_id, current_user, db)
