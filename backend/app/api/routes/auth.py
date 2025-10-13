from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from datetime import timedelta
from app.core.database import get_db
from app.core.security import verify_password, create_access_token, get_password_hash, validate_sa_id
from app.core.config import settings
from app.schemas.auth import Token, LoginRequest
from app.schemas.user import UserCreate, UserResponse
from app.models.user import User
from app.models.resume import Resume
from app.api.dependencies import get_current_user
from fastapi.responses import JSONResponse

router = APIRouter()

@router.post("/register", response_model=UserResponse)
def register(user: UserCreate, db: Session = Depends(get_db)):
    # Validate South African ID number
    if not validate_sa_id(user.sa_id_number):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid South African ID number format"
        )
    
    # Check if user already exists by username, email, or SA ID
    db_user = db.query(User).filter(
        (User.username == user.username) | 
        (User.email == user.email) |
        (User.sa_id_number == user.sa_id_number)
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
    
    # Create new user
    hashed_password = get_password_hash(user.password)
    db_user = User(
        username=user.username,
        email=user.email,
        name=user.name,
        surname=user.surname,
        sa_id_number=user.sa_id_number,
        hashed_password=hashed_password
    )
    
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user

@router.post("/login", response_model=Token)
def login(login_data: LoginRequest, db: Session = Depends(get_db)):
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
    return current_user

@router.post("/logout")
def logout(current_user: User = Depends(get_current_user)):
    """
    Simple logout endpoint
    Client should discard the token on their side
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
    Update user profile (excluding sensitive fields like SA ID)
    """
    # Prevent updating SA ID number and username
    if 'sa_id_number' in user_update:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="South African ID number cannot be changed"
        )
    
    if 'username' in user_update:
        # Check if new username is available
        existing_user = db.query(User).filter(
            User.username == user_update['username'],
            User.id != current_user.id
        ).first()
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Username already taken"
            )
    
    for field, value in user_update.items():
        if hasattr(current_user, field) and field not in ['id', 'sa_id_number']:
            setattr(current_user, field, value)
    
    db.commit()
    db.refresh(current_user)
    return current_user


