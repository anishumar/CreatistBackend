from __future__ import annotations

import os
from fastapi import APIRouter, Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel
from typing import Optional
from src.app import app
from src.utils.email_handler import send_otp_mail
from src.utils import TokenHandler, token_handler
import random

router = APIRouter(prefix="/auth/otp", tags=["OTP Authentication"])
JWT_SECRET = os.environ["JWT_SECRET"]
token_handler = TokenHandler(JWT_SECRET)
security = HTTPBearer()



def get_user_token(credentials: HTTPAuthorizationCredentials = Depends(security)):
    return token_handler.decode_token(credentials.credentials)


class StatusUpdate(BaseModel):
    is_verified: bool


class OTPRequest(BaseModel):
    email_address: str
    otp: Optional[str] = None


class OTPHandler:
    def __init__(self):
        self.otps = {}

    def generate_otp(self, email_address: str) -> str:
        otp = random.randint(100000, 999999)
        self.otps[email_address] = otp
        return str(otp)
    
    def verify_otp(self, email_address: str, otp: int) -> bool:
        return self.otps.get(email_address) == int(otp)
    
otp_handler = OTPHandler()
    

@router.post("")
async def send_otp(request: Request, data: OTPRequest):
    email_address = data.email_address

    otp = otp_handler.generate_otp(email_address=email_address)
    await send_otp_mail(
        email_address=email_address,
        otp=otp,
    )

    return True


@router.post("/verify")
async def verify_otp(
    request: Request,
    data: OTPRequest,
):
    email_address = data.email_address
    otp = data.otp

    if not otp_handler.verify_otp(email_address=email_address, otp=otp):
        return False

    return True


app.include_router(router)