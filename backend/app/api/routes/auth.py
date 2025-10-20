from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from datetime import timedelta
from app.core.database import get_db
from app.core.security import verify_password, create_access_token, get_password_hash, validate_sa_id, hash_sa_id
from app.core.config import settings
from app.schemas.auth import Token, LoginRequest
from app.schemas.user import UserCreate, UserResponse
from app.models.user import User
from app.api.dependencies import get_current_user
from fastapi.responses import JSONResponse
from datetime import datetime
import logging

logger = logging.getLogger(__name__)
router = APIRouter()

@router.post("/register", response_model=UserResponse)
def register(user: UserCreate, db: Session = Depends(get_db)):
    """
    Register a new user with POPI Act compliance
    """
    # Validate South African ID number
    if not validate_sa_id(user.sa_id_number):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid South African ID number format"
        )
    
    # Hash the ID number for storage
    hashed_id = hash_sa_id(user.sa_id_number)
    
    # Check if user already exists by username, email, or hashed SA ID
    db_user = db.query(User).filter(
        (User.username == user.username) | 
        (User.email == user.email) |
        (User.hashed_sa_id == hashed_id)
    ).first()
    
    if db_user:
        if db_user.username == user.username:
            detail = "Username already registered"
        elif db_user.email == user.email:
            detail = "Email already registered"
        else:
            detail = "South African ID number already registered"
        
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=detail
        )
    
    # Verify consent requirements
    if not user.consent_popi:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="POPI Act consent is required to use this service"
        )
    
    if not user.consent_terms:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Terms and conditions consent is required"
        )
    
    # Create new user with hashed ID and password
    hashed_password = get_password_hash(user.password)
    db_user = User(
        username=user.username,
        email=user.email,
        name=user.name,
        surname=user.surname,
        hashed_sa_id=hashed_id,  
        hashed_password=hashed_password,
        consent_popi=user.consent_popi,
        consent_terms=user.consent_terms,
        consent_given_at=datetime.utcnow()
    )
    
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    
    # Log consent for audit trail
    logger.info(f"User registered with consent: {db_user.username}, POPI: {user.consent_popi}, Terms: {user.consent_terms}")
    
    return db_user

@router.post("/login", response_model=Token)
def login(login_data: LoginRequest, db: Session = Depends(get_db)):
    """
    Login user with username/email and password
    """
    # Allow login with either username or email
    user = db.query(User).filter(
        (User.username == login_data.username) | (User.email == login_data.username)
    ).first()

    if not user or not verify_password(login_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username/email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Check if user is active
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Account is deactivated",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.username, "user_id": user.id, "email": user.email}, 
        expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}

@router.get("/me", response_model=UserResponse)
def read_users_me(current_user: User = Depends(get_current_user)):
    """
    Get current user profile (excluding sensitive hashed fields)
    """
    return current_user

@router.post("/logout")
def logout(current_user: User = Depends(get_current_user)):
    """
    Simple logout endpoint
    """
    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={
            "message": "Successfully logged out. Please discard your token.",
            "success": True
        }
    )

@router.put("/me", response_model=UserResponse)
def update_user_profile(
    user_update: dict,  
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Update user profile (excluding sensitive fields)
    """
    # Prevent updating sensitive fields
    blocked_fields = ['hashed_sa_id', 'consent_popi', 'consent_terms', 'consent_given_at']
    for field in blocked_fields:
        if field in user_update:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot update {field}"
            )
    
    # Handle username change with availability check
    if 'username' in user_update:
        existing_user = db.query(User).filter(
            User.username == user_update['username'],
            User.id != current_user.id
        ).first()
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Username already taken"
            )
    
    # Update allowed fields
    for field, value in user_update.items():
        if hasattr(current_user, field) and field not in ['id', 'hashed_sa_id', 'hashed_password']:
            setattr(current_user, field, value)
    
    current_user.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(current_user)
    return current_user

@router.post("/consent/withdraw-marketing")
def withdraw_marketing_consent(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Withdraw marketing consent
    """
    current_user.consent_marketing = False
    current_user.updated_at = datetime.utcnow()
    db.commit()
    
    logger.info(f"User {current_user.username} withdrew marketing consent")
    
    return {"message": "Marketing consent withdrawn successfully"}

@router.get("/consent/status")
def get_consent_status(current_user: User = Depends(get_current_user)):
    """
    Get current consent status
    """
    return {
        "popi_consent": current_user.consent_popi,
        "terms_consent": current_user.consent_terms,
        "consent_given_at": current_user.consent_given_at
    }