from fastapi import APIRouter

from routers import auth, courses, health, learning, taxonomies, users

api_router = APIRouter()
api_router.include_router(health.router)
api_router.include_router(auth.router)
api_router.include_router(users.router)
api_router.include_router(courses.router)
api_router.include_router(learning.router)
api_router.include_router(taxonomies.router)
