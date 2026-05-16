"""
T2: FastAPI应用入口
"""
import os
import sys
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# 确保backend目录在path中
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # 项目根目录
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from backend.routers import city, poi, session, planner, constraint

app = FastAPI(title="DIY旅行助手", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(city.router, prefix="/api/v1")
app.include_router(poi.router, prefix="/api/v1")
app.include_router(session.router, prefix="/api/v1")
app.include_router(planner.router, prefix="/api/v1")
app.include_router(constraint.router, prefix="/api/v1")


@app.get("/api/v1/health")
def health():
    return {"status": "ok", "version": "1.0.0"}
