"""
main FastAPI application for the Handshake Lab 1 project.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes.auth import router as auth_router
from app.api.routes.assistant import router as assistant_router
from app.api.routes.events import router as events_router
from app.api.routes.student_profile import router as student_profile_router


# create the FastAPI application
app = FastAPI(
    title="Handshake Lab 1 API",
    description="Backend API for the Pair 16 Handshake prototype",
    version="0.1.0",
)


# allow the React frontend to communicate with the backend
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# make the authentication endpoints available to FastAPI
app.include_router(auth_router)

# make the protected student profile endpoints available
app.include_router(student_profile_router)

# make the protected student event endpoints available
app.include_router(events_router)

# make the protected assistant endpoint available
app.include_router(assistant_router)


@app.get("/")
def read_root():
    """return a simple message from the backend."""

    return {
        "message": "Handshake Lab 1 API is running",
        "pair": 16,
        "city_set": ["Sunnyvale", "Cupertino", "Mountain View"],
    }


@app.get("/health")
def health_check():
    """confirm that the backend is healthy."""

    return {
        "status": "healthy",
        "service": "fastapi-backend",
    }
