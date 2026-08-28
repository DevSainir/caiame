from fastapi import APIRouter

from routers import auth, courses, health, taxonomies

api_router = APIRouter()
api_router.include_router(health.router)
api_router.include_router(auth.router)
api_router.include_router(courses.router)
api_router.include_router(taxonomies.router)
