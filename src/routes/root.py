from __future__ import annotations

from time import perf_counter
import logging

from fastapi import Request, HTTPException, status, Depends
from fastapi.responses import JSONResponse
from typing import Optional
from src.models.feedback import FeedbackCreate
from src.models.user import User  # If user association is needed

from src.app import app, user_handler
from src.routes.visionboard import get_user_token
from src.utils import Token


@app.route("/")
def root(request: Request) -> JSONResponse:
    return JSONResponse(
        {"message": "API for Creatist iOS Application"}, status_code=200
    )


@app.route("/ping")
async def root(request: Request) -> JSONResponse:
    ini = perf_counter()
    _ = await user_handler.supabase.table("users").select("*").execute()
    fin = perf_counter() - ini

    return JSONResponse({"message": "success", "response_time": fin})


@app.get("/health")
async def health_check():
    """Health check endpoint for deployment monitoring"""
    try:
        # Simple health check - just return success
        return JSONResponse({
            "status": "healthy",
            "message": "API is running",
            "timestamp": perf_counter()
        })
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return JSONResponse(
            status_code=503,
            content={
                "status": "unhealthy", 
                "error": str(e)
            }
        )

# Dependency to get current user or None (pseudo, replace with your actual logic)
async def get_current_user_optional(request: Request) -> Optional[User]:
    from fastapi.security.utils import get_authorization_scheme_param
    auth: str = request.headers.get("Authorization")
    if not auth:
        return None
    scheme, credentials = get_authorization_scheme_param(auth)
    if not credentials or scheme.lower() != "bearer":
        return None
    try:
        token: Token = get_user_token(credentials)
        user = await user_handler.fetch_user(user_id=token.sub)
        return user
    except Exception:
        return None

@app.post("/api/feedback")
async def send_feedback(
    feedback: FeedbackCreate,
    request: Request,
    user: Optional[User] = Depends(get_current_user_optional)
):
    if not feedback.message.strip():
        raise HTTPException(status_code=400, detail="Message cannot be empty.")
    if len(feedback.message) > 2000:
        raise HTTPException(status_code=400, detail="Message too long.")
    query = """
        INSERT INTO feedback (user_id, email, message)
        VALUES ($1, $2, $3)
    """
    user_id = user.id if user else None
    logging.info(f"Inserting feedback: user_id={user_id}, email={feedback.email}, message={feedback.message.strip()}")
    result = await request.app.state.pool.execute(query, user_id, feedback.email, feedback.message.strip())
    logging.info(f"Feedback insert result: {result}")
    return {"message": "Feedback sent successfully."}
