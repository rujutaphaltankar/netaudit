from fastapi import APIRouter

from app.api.v1 import configs, health

api_router = APIRouter()
api_router.include_router(health.router)
api_router.include_router(configs.router)
