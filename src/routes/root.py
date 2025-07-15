from __future__ import annotations

from time import perf_counter

from fastapi import Request
from fastapi.responses import JSONResponse

from src.app import app, user_handler


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
