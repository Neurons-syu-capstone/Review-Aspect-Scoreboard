"""
Review-Aspect-Scoreboard FastAPI 백엔드
실행: uvicorn main:app --reload --port 8000
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from src.routers import products, sentences

app = FastAPI(title="Review Aspect Scoreboard API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],  # Vite 개발 서버
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(products.router,  prefix="/api/products",  tags=["products"])
app.include_router(sentences.router, prefix="/api/sentences", tags=["sentences"])

@app.get("/")
def root():
    return {"status": "ok", "service": "Review Aspect Scoreboard API"}
