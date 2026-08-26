from fastapi import APIRouter

from app.api.auth import router as auth_router
from app.api.cv_documents import router as cv_documents_router
from app.api.extraction import router as extraction_router
from app.api.health import router as health_router
from app.api.job_targets import router as job_targets_router
from app.api.match_analyses import router as match_analyses_router

api_router = APIRouter()
api_router.include_router(auth_router)
api_router.include_router(cv_documents_router)
api_router.include_router(extraction_router)
api_router.include_router(job_targets_router)
api_router.include_router(match_analyses_router)
api_router.include_router(health_router)
