from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from app.config import settings
from app.database import engine, Base
from app.routers import auth, users, teams, work_items, dashboard

# Create database tables if they do not exist
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Newtonite Operations Management API",
    description="Internal Operations Management MVP API with concurrency control, RBAC, and audit logging.",
    version="1.0.0",
)

# CORS setup
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"] if settings.ENVIRONMENT == "development" else settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include Routers
app.include_router(auth.router)
app.include_router(users.router)
app.include_router(teams.router)
app.include_router(work_items.router)
app.include_router(dashboard.router)


@app.get("/api/health")
def health_check():
    """Health check endpoint for container and uptime verification."""
    return {"status": "ok", "app": "Newtonite Operations API", "version": "1.0.0"}


@app.get("/")
def root():
    return {"message": "Welcome to Newtonite Operations Management API. Visit /docs for OpenAPI documentation."}
