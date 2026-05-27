"""Authentication routes: register, login, key management."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import get_developer_for_api_key
from app.models import APIKey, Developer
from app.schemas import (
    APIKeyOut,
    DeveloperOut,
    LoginRequest,
    RegisterRequest,
    RegisterResponse,
    TokenResponse,
)
from app.security import (
    api_key_prefix_display,
    create_access_token,
    generate_api_key,
    hash_api_key,
    hash_password,
    verify_password,
)

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post(
    "/register",
    response_model=RegisterResponse,
    status_code=status.HTTP_201_CREATED,
)
def register(payload: RegisterRequest, db: Session = Depends(get_db)) -> RegisterResponse:
    existing = db.execute(
        select(Developer).where(Developer.email == payload.email)
    ).scalar_one_or_none()
    if existing is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email is already registered.",
        )

    developer = Developer(
        email=payload.email,
        hashed_password=hash_password(payload.password),
        tier="free",
    )
    db.add(developer)
    db.flush()

    plaintext_key = generate_api_key()
    api_key = APIKey(
        developer_id=developer.id,
        key_hash=hash_api_key(plaintext_key),
        key_prefix=api_key_prefix_display(plaintext_key),
        is_active=True,
    )
    db.add(api_key)
    db.commit()
    db.refresh(developer)

    return RegisterResponse(
        id=developer.id,
        email=developer.email,
        tier=developer.tier,
        api_key=plaintext_key,
    )


@router.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)) -> TokenResponse:
    developer = db.execute(
        select(Developer).where(Developer.email == payload.email)
    ).scalar_one_or_none()
    if developer is None or not verify_password(payload.password, developer.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password.",
        )

    token, expires_in = create_access_token(
        subject=str(developer.id),
        extra={"email": developer.email, "tier": developer.tier},
    )
    return TokenResponse(access_token=token, expires_in=expires_in)


@router.get("/me", response_model=DeveloperOut)
def me(developer: Developer = Depends(get_developer_for_api_key)) -> DeveloperOut:
    return DeveloperOut.model_validate(developer)


@router.get("/keys", response_model=list[APIKeyOut])
def list_keys(
    developer: Developer = Depends(get_developer_for_api_key),
    db: Session = Depends(get_db),
) -> list[APIKeyOut]:
    keys = db.execute(
        select(APIKey).where(APIKey.developer_id == developer.id)
    ).scalars().all()
    return [APIKeyOut.model_validate(k) for k in keys]
