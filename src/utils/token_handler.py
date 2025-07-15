from __future__ import annotations

from datetime import datetime, timedelta
from typing import TYPE_CHECKING, Optional, Tuple
from uuid import UUID

import jwt
from pydantic import BaseModel, Field
from pytz import timezone
import time

from src.models import User
from src.utils.log import log

if TYPE_CHECKING:
    pass


class Token(BaseModel):
    sub: UUID
    email: str
    name: str
    iat: int = Field(
        default_factory=lambda: int(datetime.now(timezone("UTC")).timestamp())
    )
    exp: int

    class Config:
        json_encoders = {
            UUID: lambda v: str(v),
        }


class RefreshToken(BaseModel):
    sub: UUID
    jti: str  # JWT ID for token revocation
    iat: int = Field(
        default_factory=lambda: int(datetime.now(timezone("UTC")).timestamp())
    )
    exp: int

    class Config:
        json_encoders = {
            UUID: lambda v: str(v),
        }


class TokenHandler:
    def __init__(self, secret: str, algorithm: str = "HS256"):
        self.secret = secret
        self.algorithm = algorithm
        # In production, use Redis or database for revoked tokens
        self.revoked_tokens: set = set()

    def create_token_pair(self, user: User) -> Tuple[str, str]:
        """Create both access and refresh tokens"""
        log.debug("Creating token pair for user: %s", user.id)
        
        # Access token - short lived (15 minutes)
        access_token = self.create_access_token(user)
        
        # Refresh token - longer lived (7 days)
        refresh_token = self.create_refresh_token(user)
        
        log.info("Token pair created for user: %s", user.id)
        return access_token, refresh_token

    def create_access_token(self, user: User) -> str:  # 15 minutes
        log.debug("Creating access token for user: %s", user.id)
        now = int(time.time())
        access_payload = {
            "sub": str(user.id),
            "email": user.email,
            "name": user.name,
            "iat": now,
            "exp": now + 60 * 15  # 15 minutes
        }
        token = jwt.encode(access_payload, self.secret, algorithm=self.algorithm)
        log.info("Access token created for user: %s", user.id)
        return token

    def create_refresh_token(self, user: User) -> str:  # 7 days
        log.debug("Creating refresh token for user: %s", user.id)
        import secrets
        jti = secrets.token_urlsafe(32)  # Unique token ID
        
        now = int(time.time())
        refresh_payload = {
            "sub": str(user.id),
            "type": "refresh",
            "iat": now,
            "exp": now + 60 * 60 * 24 * 7  # 7 days
        }
        token = jwt.encode(refresh_payload, self.secret, algorithm=self.algorithm)
        log.info("Refresh token created for user: %s", user.id)
        return token

    def refresh_access_token(self, refresh_token: str) -> Optional[str]:
        """Use refresh token to get new access token"""
        try:
            decoded = jwt.decode(refresh_token, self.secret, algorithms=[self.algorithm])
            refresh_payload = RefreshToken(**decoded)
            
            # Check if token is revoked
            if refresh_token in self.revoked_tokens:
                log.warning("Refresh token is revoked")
                return None
            
            # Get user and create new access token
            # In production, fetch user from database
            from src.app import user_handler
            user = user_handler.fetch_user(user_id=refresh_payload.sub)
            if not user:
                log.warning("User not found for refresh token")
                return None
                
            return self.create_access_token(user)
            
        except jwt.ExpiredSignatureError:
            log.warning("Refresh token has expired")
            return None
        except jwt.InvalidTokenError:
            log.error("Invalid refresh token")
            return None

    def revoke_refresh_token(self, refresh_token: str) -> bool:
        """Revoke a refresh token"""
        try:
            decoded = jwt.decode(refresh_token, self.secret, algorithms=[self.algorithm])
            self.revoked_tokens.add(refresh_token)
            log.info("Refresh token revoked for user: %s", decoded.get('sub'))
            return True
        except jwt.InvalidTokenError:
            log.error("Invalid refresh token for revocation")
            return False

    def validate_token(self, token: str) -> Optional[Token]:
        log.debug("Validating token")
        try:
            decoded = jwt.decode(token, self.secret, algorithms=[self.algorithm])
            log.info("Token successfully validated")
            return Token(**decoded)
        except jwt.ExpiredSignatureError:
            log.warning("Token has expired")
            return None
        except jwt.InvalidTokenError:
            log.error("Invalid token provided")
            return None

    def decode_token(self, token: str) -> Optional[Token]:
        log.debug("Decoding token")
        try:
            decoded = jwt.decode(token, self.secret, algorithms=[self.algorithm])
            log.info("Token successfully decoded")
            return Token(**decoded)
        except jwt.InvalidTokenError:
            log.error("Token decoding failed due to invalid token", exc_info=True)
            raise

    def decode_refresh_token(self, token: str) -> dict:
        payload = jwt.decode(token, self.secret, algorithms=[self.algorithm])
        if payload.get("type") != "refresh":
            raise Exception("Not a refresh token")
        return payload
