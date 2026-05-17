from fastapi import APIRouter

from .file.controller import FileRouter
from .health.controller import HealthRouter
from .upload.controller import UploadRouter

common_router = APIRouter(prefix="/common")

common_router.include_router(FileRouter)
common_router.include_router(HealthRouter)
common_router.include_router(UploadRouter)
