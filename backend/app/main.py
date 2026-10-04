# SHARED FILE - controlled by the group leader.
# Ask the group leader before adding routers, middleware, or global settings.

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.component01_skill.routes import router as component01_router
from app.component02_personality.routes import router as component02_router
from app.component03_career.routes import router as component03_router
from app.component04_roadmap.routes import router as component04_router

app = FastAPI(title="AI-Based Smart Career Path Recommendation System API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# NOTE: Database tables are NOT created automatically on startup.
# Run database/schema.sql against PostgreSQL instead (see README.md).


@app.get("/health")
def health():
    return {
        "status": "ok",
        "message": "Career Recommendation System API is running",
    }


app.include_router(component01_router)
app.include_router(component02_router)
app.include_router(component03_router)
app.include_router(component04_router)
