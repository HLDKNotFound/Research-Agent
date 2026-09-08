from fastapi import APIRouter
from app.api.auth import router as auth_router
from app.api.projects import router as projects_router
from app.api.conversations import router as conversations_router
from app.api.runs import router as runs_router
from app.api.files import router as files_router
from app.api.reports import router as reports_router

api_router = APIRouter()
api_router.include_router(auth_router)
api_router.include_router(projects_router)
api_router.include_router(conversations_router)
api_router.include_router(runs_router)
api_router.include_router(files_router)
api_router.include_router(reports_router)

__all__ = ["api_router"]
