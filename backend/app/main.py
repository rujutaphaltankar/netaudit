"""FastAPI application entry point. Run with: uvicorn app.main:app --reload"""
from __future__ import annotations

import logging

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.v1.router import api_router
from app.core.config import get_settings
from app.core.errors import AppError

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
log = logging.getLogger("netaudit")


def _error(status: int, code: str, message: str, details: dict | None = None) -> JSONResponse:
    return JSONResponse(status_code=status, content={"error": {"code": code, "message": message, "details": details or {}}})


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(title=settings.app_name, version=settings.app_version,
                  description="Multi-vendor network configuration security compliance auditor.")

    app.add_middleware(
        CORSMiddleware, allow_origins=settings.cors_origin_list, allow_credentials=False,
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE"], allow_headers=["*"],
    )

    @app.exception_handler(AppError)
    async def handle_app_error(_: Request, exc: AppError) -> JSONResponse:
        return _error(exc.status_code, exc.code, exc.message, exc.details)

    @app.exception_handler(Exception)
    async def handle_unexpected(_: Request, exc: Exception) -> JSONResponse:
        # Log only the exception type: messages can contain uploaded configuration content.
        log.error("unhandled_error type=%s", type(exc).__name__)
        return _error(500, "internal_error", "An unexpected error occurred.")

    app.include_router(api_router, prefix=settings.api_v1_prefix)
    return app


app = create_app()
