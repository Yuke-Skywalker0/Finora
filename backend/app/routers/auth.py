from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Response, HTTPException, Request
from google.auth.transport import requests
from google.oauth2 import id_token

from ..config import settings
from ..db import users
from ..models import GoogleLogin
from ..security import create_session, current_user_id, create_csrf_token, csrf_protect

router = APIRouter(prefix="/api/auth", tags=["auth"])

@router.post("/google")
def google_login(payload: GoogleLogin, response: Response):
    try:
        info = id_token.verify_oauth2_token(
            payload.credential,
            requests.Request(),
            settings.google_client_id
        )
    except Exception as exc:
        raise HTTPException(status_code=401, detail="Login Google non valido.") from exc

    if not info.get("email_verified"):
        raise HTTPException(status_code=401, detail="Email Google non verificata.")

    sub = info["sub"]

    users.update_one(
        {"google_sub": sub},
        {
            "$set": {
                "email": info.get("email", ""),
                "name": info.get("name", ""),
                "picture": info.get("picture", ""),
                "updated_at": datetime.now(timezone.utc)
            },
            "$setOnInsert": {
                "google_sub": sub,
                "created_at": datetime.now(timezone.utc)
            }
        },
        upsert=True
    )

    token = create_session(sub)

    csrf = create_csrf_token()
    response.set_cookie(
        "finora_session",
        token,
        httponly=True,
        secure=settings.cookie_secure,
        samesite=settings.cookie_samesite,
        max_age=settings.access_token_minutes * 60,
        path="/",
        domain=None
    )
    response.set_cookie(
        "finora_csrf", csrf, httponly=False, secure=settings.cookie_secure,
        samesite=settings.cookie_samesite, max_age=settings.access_token_minutes * 60, path="/"
    )

    return {
        "name": info.get("name", ""),
        "email": info.get("email", ""),
        "picture": info.get("picture", "")
    }

@router.get("/me")
def me(user_id: str = Depends(current_user_id)):
    user = users.find_one({"google_sub": user_id})

    if not user:
        raise HTTPException(status_code=401, detail="Utente non trovato.")

    return {
        "name": user.get("name", ""),
        "email": user.get("email", ""),
        "picture": user.get("picture", "")
    }

@router.post("/logout", status_code=204)
def logout(response: Response, _: None = Depends(csrf_protect)):
    response.delete_cookie("finora_session", path="/")
    response.delete_cookie("finora_csrf", path="/")
