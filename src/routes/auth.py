from __future__ import annotations

import os

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import JSONResponse
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, EmailStr

from src.app import app, user_handler
from src.models import User
from src.utils import Token, TokenHandler

router = APIRouter(prefix="/auth", tags=["Authentication"])
JWT_SECRET = os.environ["JWT_SECRET"]


class Credential(BaseModel):
    email: EmailStr
    password: str


class RefreshRequest(BaseModel):
    refresh_token: str


token_handler = TokenHandler(os.environ["JWT_SECRET"])
security = HTTPBearer()


def get_user_token(credentials: HTTPAuthorizationCredentials = Depends(security)):
    token = token_handler.decode_token(credentials.credentials)
    if token is None:
        raise HTTPException(status_code=401, detail="Token is expired or invalid")
    return token


@router.post("/signin")
async def signin_route(request: Request, credential: Credential) -> JSONResponse:
    user = await user_handler.fetch_user(
        email=credential.email, password=credential.password
    )
    if not user:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    access_token, refresh_token = token_handler.create_token_pair(user)

    return JSONResponse({
        "message": "success", 
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
        "expires_in": 900  # 15 minutes
    })


@router.post("/signup")
async def signup_route(request: Request, user: User) -> JSONResponse:
    _user = await user_handler.fetch_user(email=user.email, password=user.password)
    if _user is not None:
        raise HTTPException(400, "User already exists")

    await user_handler.create_user(user=user)

    return JSONResponse({"message": "success"})


@router.get("/fetch")
async def fetch_user_route(token: Token = Depends(get_user_token)) -> User:
    user = await user_handler.fetch_user(user_id=token.sub)
    return user


@router.post("/refresh")
async def refresh_route(request: Request, refresh_request: RefreshRequest) -> JSONResponse:
    """Refresh access token using refresh token"""
    new_access_token = await token_handler.refresh_access_token(refresh_request.refresh_token)
    
    if not new_access_token:
        raise HTTPException(status_code=401, detail="Invalid or expired refresh token")
    
    return JSONResponse({
        "message": "success", 
        "access_token": new_access_token,
        "token_type": "bearer",
        "expires_in": 900  # 15 minutes
    })


@router.post("/logout")
async def logout_route(request: Request, refresh_request: RefreshRequest) -> JSONResponse:
    """Logout by revoking refresh token"""
    success = token_handler.revoke_refresh_token(refresh_request.refresh_token)
    
    if not success:
        raise HTTPException(status_code=400, detail="Invalid refresh token")
    
    return JSONResponse({"message": "success"})


@router.post("/update")
async def update_user_route(
    user: User, token: Token = Depends(get_user_token)
) -> User:
    updated_user = await user_handler.update_user(
        user_id=token.sub, update_payload=user
    )
    if updated_user is None:
        raise HTTPException(400, "Failed to update User")
    return updated_user


app.include_router(router)
