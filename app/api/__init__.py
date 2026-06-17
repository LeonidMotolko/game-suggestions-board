from fastapi import APIRouter
from app.api.auth import router as auth_router
from app.api.suggestions import router as suggestions_router
from app.api.admin import router as admin_router

api_router = APIRouter()
api_router.include_router(auth_router)
api_router.include_router(suggestions_router, tags=["suggestions"])
api_router.include_router(admin_router, prefix="/admin", tags=["admin"])