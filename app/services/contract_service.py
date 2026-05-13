from sqlalchemy.orm import Session
from sqlalchemy import or_
from app.models.contract import Contract, ContractStatus
from app.models.user import User
from app.schemas.contract import ContractCreate, ContractUpdate, ContractStatusUpdate
from app.core.exceptions import NotFoundError, ForbiddenError, BadRequestError

# Valid status transitions
VALID_TRANSITIONS = {
    ContractStatus.DRAFT:        [ContractStatus.UNDER_REVIEW, ContractStatus.TERMINATED],
    ContractStatus.UNDER_REVIEW: [ContractStatus.APPROVED, ContractStatus.DRAFT, ContractStatus.TERMINATED],
    ContractStatus.APPROVED:     [ContractStatus.SIGNED, ContractStatus.UNDER_REVIEW, ContractStatus.TERMINATED],
    ContractStatus.SIGNED:       [ContractStatus.EXPIRED, ContractStatus.TERMINATED],
    ContractStatus.EXPIRED:      [],
    ContractStatus.TERMINATED:   [],
}

def create_contract(data: ContractCreate, user: User, db: Session) -> Contract:
    contract = Contract(
        company_id=user.company_id,
        created_by_id=user.id,
        title=data.title,
        contract_type=data.contract_type,
        description=data.description,
        party_a=data.party_a,
        party_b=data.party_b,
        start_date=data.start_date,
        end_date=data.end_date,
        contract_text=data.contract_text
    )
    db.add(contract)
    db.commit()
    db.refresh(contract)
    return contract

def get_contract(contract_id: str, user: User, db: Session) -> Contract:
    contract = db.query(Contract).filter(
        Contract.id == contract_id,
        Contract.company_id == user.company_id
    ).first()
    if not contract:
        raise NotFoundError("Contract not found")
    return contract

def list_contracts(
    user: User, db: Session,
    status: str = None, search: str = None,
    page: int = 1, limit: int = 20
) -> tuple[list[Contract], int]:
    query = db.query(Contract).filter(Contract.company_id == user.company_id)

    if status:
        query = query.filter(Contract.status == status)

    if search:
        query = query.filter(
            or_(
                Contract.title.ilike(f"%{search}%"),
                Contract.party_a.ilike(f"%{search}%"),
                Contract.party_b.ilike(f"%{search}%")
            )
        )

    total = query.count()
    contracts = query.order_by(Contract.created_at.desc())\
                    .offset((page - 1) * limit).limit(limit).all()
    return contracts, total

def update_contract(contract_id: str, data: ContractUpdate, user: User, db: Session) -> Contract:
    contract = get_contract(contract_id, user, db)

    if contract.status == ContractStatus.SIGNED:
        raise BadRequestError("Cannot edit a signed contract")

    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(contract, field, value)

    db.commit()
    db.refresh(contract)
    return contract

def update_contract_status(contract_id: str, data: ContractStatusUpdate, user: User, db: Session) -> Contract:
    contract = get_contract(contract_id, user, db)

    allowed = VALID_TRANSITIONS.get(contract.status, [])
    if data.status not in allowed:
        raise BadRequestError(
            f"Cannot transition from '{contract.status}' to '{data.status}'. "
            f"Allowed: {[s.value for s in allowed]}"
        )

    contract.status = data.status
    db.commit()
    db.refresh(contract)
    return contract

def delete_contract(contract_id: str, user: User, db: Session) -> None:
    contract = get_contract(contract_id, user, db)
    if contract.status not in [ContractStatus.DRAFT, ContractStatus.TERMINATED]:
        raise BadRequestError("Only draft or terminated contracts can be deleted")
    db.delete(contract)
    db.commit()
