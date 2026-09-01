from fastapi import APIRouter

from routers import (
    access,
    admin,
    assignments,
    auth,
    courses,
    faq,
    grading,
    health,
    learning,
    quiz,
    sitemap,
    taxonomies,
    users,
)

api_router = APIRouter()
api_router.include_router(health.router)
api_router.include_router(sitemap.router)
api_router.include_router(auth.router)
api_router.include_router(users.router)
api_router.include_router(courses.router)
api_router.include_router(learning.router)
api_router.include_router(assignments.router)
api_router.include_router(grading.router)
api_router.include_router(admin.router)
api_router.include_router(access.router)
api_router.include_router(quiz.router)
api_router.include_router(faq.router)
api_router.include_router(taxonomies.router)
