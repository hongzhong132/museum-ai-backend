from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.routes.halls import router as halls_router
from app.routes.exhibits import router as exhibits_router
from app.routes.route_plan import router as route_router

BASE_DIR = Path(__file__).resolve().parent.parent
MEDIA_DIR = BASE_DIR / "media"
MEDIA_DIR.mkdir(parents=True, exist_ok=True)

app = FastAPI(
    title="Museum AI Backend",
    version="0.1.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:5174",
        "http://127.0.0.1:5174",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 供前端直接访问生成后的 TTS 音频文件
app.mount("/media", StaticFiles(directory=str(MEDIA_DIR)), name="media")

app.include_router(halls_router)
app.include_router(exhibits_router)
app.include_router(route_router)


@app.get("/")
def root():
    return {"message": "Museum AI backend is running"}
