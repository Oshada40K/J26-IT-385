# Shared application entry point, maintained by the group leader.
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.component01_skill.router import router as skill_router
from app.component02_personality.router import router as personality_router
from app.component03_career.router import router as career_router
from app.component03_career.service import career_lifespan
from app.component04_roadmap.router import router as roadmap_router

app = FastAPI(title="AI-Based Smart Career Path Recommendation System API", lifespan=career_lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def root():
    return {
        "message": "AI-Based Smart Career Path Recommendation System API",
        "status": "running",
    }


@app.get("/health")
def health():
    return {"status": "healthy"}


app.include_router(skill_router)
app.include_router(personality_router)
app.include_router(career_router)
app.include_router(roadmap_router)
