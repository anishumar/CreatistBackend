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
    try:
        # Check database connection
        db_status = "disconnected"
        if hasattr(app.state, 'pool') and app.state.pool is not None:
            try:
                # Test database connection
                async with app.state.pool.acquire() as conn:
                    await conn.fetchval("SELECT 1")
                db_status = "connected"
            except Exception as e:
                logger.error(f"Database connection test failed: {e}")
                db_status = "error"
        
        fin = perf_counter() - ini
        return JSONResponse({
            "message": "success", 
            "response_time": fin,
            "database": db_status,
            "status": "API is responding"
        })
    except Exception as e:
        logger.error(f"Ping failed: {e}")
        fin = perf_counter() - ini
        return JSONResponse({
            "message": "error",
            "response_time": fin,
            "error": str(e)
        })


@app.get("/health")
async def health_check():
    """Health check endpoint for deployment monitoring"""
    try:
        # Check if database is available
        db_status = "connected"
        if hasattr(app.state, 'pool') and app.state.pool is None:
            db_status = "disconnected"
        
        return JSONResponse({
            "status": "healthy",
            "message": "API is running",
            "database": db_status,
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
    
    # Check if database is available
    if not hasattr(request.app.state, 'pool') or request.app.state.pool is None:
        raise HTTPException(status_code=503, detail="Database not available")
    
    query = """
        INSERT INTO feedback (user_id, email, message)
        VALUES ($1, $2, $3)
    """
    user_id = user.id if user else None
    logging.info(f"Inserting feedback: user_id={user_id}, email={feedback.email}, message={feedback.message.strip()}")
    result = await request.app.state.pool.execute(query, user_id, feedback.email, feedback.message.strip())
    logging.info(f"Feedback insert result: {result}")
    return {"message": "Feedback sent successfully."}
