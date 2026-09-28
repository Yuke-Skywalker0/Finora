from collections import defaultdict
from time import monotonic
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from .config import settings
from .db import ensure_indexes
from .routers import auth, dashboard, transactions, accounts, budgets, goals, recurring

class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
        response.headers["Cross-Origin-Opener-Policy"] = "same-origin"
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        return response

class RateLimitMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, limit=120, window=60):
        super().__init__(app); self.limit=limit; self.window=window; self.buckets=defaultdict(list)
    async def dispatch(self, request, call_next):
        if request.url.path.startswith("/api/"):
            ip=request.client.host if request.client else "unknown"
            now=monotonic(); bucket=self.buckets[ip]
            self.buckets[ip]=[t for t in bucket if now-t < self.window]
            if len(self.buckets[ip]) >= self.limit:
                return JSONResponse(status_code=429, content={"detail":"Troppe richieste, riprova più tardi."})
            self.buckets[ip].append(now)
        return await call_next(request)

app = FastAPI(title="Finora API", version="1.1.0", docs_url="/docs", redoc_url=None)
app.add_middleware(RateLimitMiddleware)
app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(CORSMiddleware, allow_origins=settings.origins, allow_credentials=True, allow_methods=["GET","POST","DELETE","OPTIONS"], allow_headers=["Content-Type","X-CSRF-Token"])

@app.on_event("startup")
def startup(): ensure_indexes()

@app.get("/health")
def health(): return {"status":"ok"}

app.include_router(auth.router)
app.include_router(transactions.router)
app.include_router(dashboard.router)
app.include_router(accounts.router)
app.include_router(budgets.router)
app.include_router(goals.router)
app.include_router(recurring.router)
