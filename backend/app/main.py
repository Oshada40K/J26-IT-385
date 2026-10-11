# Shared application entry point, maintained by the group leader.
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
from pathlib import Path

load_dotenv(Path(__file__).resolve().parents[1] / '.env', override=False)
from app.auth.router import router as auth_router
from app.auth.config import allowed_origins

from app.component01_skill.router import router as skill_router
from app.component02_personality.router import router as personality_router
from app.component03_career.router import router as career_router
from app.component03_career.service import career_lifespan
from app.component04_roadmap.router import router as roadmap_router

app = FastAPI(title="AI-Based Smart Career Path Recommendation System API", lifespan=career_lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins(),
    allow_credentials=True,
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
app.include_router(auth_router)


@app.middleware('http')
async def auth_response_headers(request, call_next):
    response = await call_next(request)
    if request.url.path.startswith('/api/auth/'):
        response.headers['Cache-Control'] = 'no-store'
        response.headers['Pragma'] = 'no-cache'
    return response
