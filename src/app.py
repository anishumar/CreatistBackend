from __future__ import annotations

import os
import asyncpg
import logging
import json

from dotenv import load_dotenv
from fastapi import FastAPI, Request
from starlette.middleware.base import BaseHTTPMiddleware

from src.utils import UserHandler  # type: ignore  # noqa

logger = logging.getLogger(__name__)

load_dotenv()
user_handler = UserHandler()

HOST = os.environ["HOST"]
PORT = os.environ["PORT"]


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        # Log request details
        logger.info(f"📥 {request.method} {request.url.path}")
        
        # For POST requests to /posts, log the raw body
        if request.method == "POST" and request.url.path == "/posts":
            try:
                body = await request.body()
                logger.info(f"📄 Raw request body: {body.decode('utf-8')}")
                
                # Try to parse as JSON for better logging
                try:
                    json_body = json.loads(body.decode('utf-8'))
                    logger.info(f"📄 Parsed JSON body: {json.dumps(json_body, indent=2)}")
                except json.JSONDecodeError:
                    logger.warning("📄 Request body is not valid JSON")
                    
            except Exception as e:
                logger.error(f"❌ Error reading request body: {e}")
        
        response = await call_next(request)
        
        # Log response status
        logger.info(f"📤 Response status: {response.status_code}")
        
        return response


async def startup():
    await user_handler.init()

    # Initialize PostgreSQL connection pool
    app.state.pool = await asyncpg.create_pool(
        os.environ["DATABASE_URL"],
        min_size=1,
        max_size=10
    )
    app.state.jwt_secret = os.environ["JWT_SECRET"]


async def shutdown():
    if hasattr(app.state, 'pool'):
        await app.state.pool.close()


app = FastAPI(title="Creatist API Documentation", on_startup=[startup], on_shutdown=[shutdown])

# Add request logging middleware
app.add_middleware(RequestLoggingMiddleware)

from .routes import *  # noqa
from .routes.ws_chat import router as ws_router
from .routes.post import router as post_router

# Include WebSocket router
app.include_router(ws_router)
# Include Post router
app.include_router(post_router)
