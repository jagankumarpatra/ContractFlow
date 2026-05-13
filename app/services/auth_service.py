from sqlalchemy.orm import Session
from app.models.user import User, UserRole
from app.models.company import Company
from app.schemas.user import UserRegister, UserLogin
from app.core.security import hash_password, verify_password, create_access_token
from app.core.exceptions import ConflictError, UnauthorizedError, NotFoundError

def register_user(data: UserRegister, db: Session) -> tuple[User, str]:
    # Check email uniqueness
    if db.query(User).filter(User.email == data.email).first():
        raise ConflictError("Email already registered")

    # Get or create company
    company = db.query(Company).filter(Company.name == data.company_name).first()
    if not company:
        company = Company(name=data.company_name)
        db.add(company)
        db.flush()

    # First user in a company becomes admin
    existing_users = db.query(User).filter(User.company_id == company.id).count()
    role = UserRole.ADMIN if existing_users == 0 else UserRole.MEMBER

    user = User(
        name=data.name,
        email=data.email,
        hashed_password=hash_password(data.password),
        company_id=company.id,
        role=role
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    token = create_access_token({"sub": user.id, "company_id": user.company_id})
    return user, token

def login_user(data: UserLogin, db: Session) -> tuple[User, str]:
    user = db.query(User).filter(User.email == data.email).first()
    if not user or not verify_password(data.password, user.hashed_password):
        raise UnauthorizedError("Invalid email or password")
    if not user.is_active:
        raise UnauthorizedError("Account is inactive")

    token = create_access_token({"sub": user.id, "company_id": user.company_id})
    return user, token
