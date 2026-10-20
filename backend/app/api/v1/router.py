from fastapi import APIRouter

from app.api.v1 import ai, audits, auth, configs, health, rules, users

api_router = APIRouter()
for module in (health, auth, users, configs, audits, rules, ai):
    api_router.include_router(module.router)
