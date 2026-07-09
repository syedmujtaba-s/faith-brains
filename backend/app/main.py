from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import router
from app.config import get_settings

app = FastAPI(
    title="FaithBrains API",
    version="0.1.0",
    description=(
        "Islamic learning assistant API — Quran + Hadith search with visible sources. "
        "Educational tool; not a religious authority and not a source of rulings (fatwas)."
    ),
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=get_settings().cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.middleware("http")
async def security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers.setdefault("X-Content-Type-Options", "nosniff")
    response.headers.setdefault("X-Frame-Options", "DENY")
    response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
    return response


app.include_router(router, prefix="/api/v1")
