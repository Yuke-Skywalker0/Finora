from collections import defaultdict
from pathlib import Path
from time import monotonic

from fastapi import FastAPI
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.base import BaseHTTPMiddleware

from .db import ensure_indexes
from .routers import auth, dashboard, transactions, accounts, budgets, goals, recurring

FRONTEND_DIR = Path(__file__).resolve().parents[2] / "frontend"

class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
        response.headers["Cross-Origin-Opener-Policy"] = "same-origin"
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        response.headers["Cache-Control"] = "no-store" if request.url.path.startswith("/api/") else response.headers.get("Cache-Control", "public, max-age=300")
        return response

class RateLimitMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, limit=120, window=60):
        super().__init__(app)
        self.limit, self.window, self.buckets = limit, window, defaultdict(list)

    async def dispatch(self, request, call_next):
        if request.url.path.startswith("/api/"):
            ip = request.client.host if request.client else "unknown"
            now = monotonic()
            bucket = [t for t in self.buckets[ip] if now - t < self.window]
            if len(bucket) >= self.limit:
                return JSONResponse(status_code=429, content={"detail": "Troppe richieste, riprova più tardi."})
            bucket.append(now)
            self.buckets[ip] = bucket
        return await call_next(request)

app = FastAPI(title="Finora", version="12.0.0", docs_url="/docs", redoc_url=None)
app.add_middleware(RateLimitMiddleware)
app.add_middleware(SecurityHeadersMiddleware)

@app.on_event("startup")
def startup():
    ensure_indexes()

@app.get("/health")
def health():
    return {"status": "ok", "app": "finora", "version": "12.0.0"}

app.include_router(auth.router)
app.include_router(transactions.router)
app.include_router(dashboard.router)
app.include_router(accounts.router)
app.include_router(budgets.router)
app.include_router(goals.router)
app.include_router(recurring.router)

# Same-origin deployment: frontend and API are served by the same Render service.
app.mount("/", StaticFiles(directory=str(FRONTEND_DIR), html=True), name="frontend")
