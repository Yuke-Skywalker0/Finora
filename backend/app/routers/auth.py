from datetime import datetime, timezone
from urllib.parse import urlencode
import secrets

from fastapi import APIRouter, Depends, Response, HTTPException, Request
from fastapi.responses import RedirectResponse
import requests
from google.oauth2 import id_token
from google.auth.transport import requests as google_requests

from ..config import settings
from ..db import users
from ..security import create_session, current_user_id, create_csrf_token, csrf_protect

router = APIRouter(prefix="/api/auth", tags=["auth"])


def _set_session_cookies(response: Response, user_id: str):
    token = create_session(user_id)
    csrf = create_csrf_token()
    response.set_cookie(
        "finora_session", token, httponly=True, secure=settings.cookie_secure,
        samesite=settings.cookie_samesite, max_age=settings.access_token_minutes * 60,
        path="/", domain=None
    )
    response.set_cookie(
        "finora_csrf", csrf, httponly=False, secure=settings.cookie_secure,
        samesite=settings.cookie_samesite, max_age=settings.access_token_minutes * 60, path="/"
    )


@router.get("/google/start")
def google_start():
    if not settings.google_client_id or not settings.google_client_secret or not settings.google_redirect_uri:
        raise HTTPException(status_code=500, detail="Google OAuth non configurato sul server.")

    state = secrets.token_urlsafe(32)
    params = {
        "client_id": settings.google_client_id,
        "redirect_uri": settings.google_redirect_uri,
        "response_type": "code",
        "scope": "openid email profile",
        "state": state,
        "prompt": "select_account",
        "access_type": "online",
    }
    response = RedirectResponse(
        "https://accounts.google.com/o/oauth2/v2/auth?" + urlencode(params), status_code=302
    )
    response.set_cookie(
        "finora_oauth_state", state, httponly=True, secure=settings.cookie_secure,
        samesite="lax", max_age=600, path="/"
    )
    return response


@router.get("/google/callback")
def google_callback(request: Request):
    code = request.query_params.get("code")
    returned_state = request.query_params.get("state")
    expected_state = request.cookies.get("finora_oauth_state")

    if not code or not returned_state or not expected_state or not secrets.compare_digest(returned_state, expected_state):
        raise HTTPException(status_code=400, detail="Sessione OAuth non valida. Riprova il login.")

    token_response = requests.post(
        "https://oauth2.googleapis.com/token",
        data={
            "code": code,
            "client_id": settings.google_client_id,
            "client_secret": settings.google_client_secret,
            "redirect_uri": settings.google_redirect_uri,
            "grant_type": "authorization_code",
        },
        timeout=10,
    )
    if not token_response.ok:
        raise HTTPException(status_code=401, detail="Google non ha autorizzato l'accesso.")

    token_data = token_response.json()
    raw_id_token = token_data.get("id_token")
    if not raw_id_token:
        raise HTTPException(status_code=401, detail="Token Google non disponibile.")

    try:
        info = id_token.verify_oauth2_token(
            raw_id_token, google_requests.Request(), settings.google_client_id
        )
    except Exception as exc:
        raise HTTPException(status_code=401, detail="Token Google non valido.") from exc

    if not info.get("email_verified"):
        raise HTTPException(status_code=401, detail="Email Google non verificata.")

    sub = info["sub"]
    now = datetime.now(timezone.utc)
    users.update_one(
        {"google_sub": sub},
        {
            "$set": {
                "email": info.get("email", ""),
                "name": info.get("name", ""),
                "picture": info.get("picture", ""),
                "updated_at": now,
            },
            "$setOnInsert": {"google_sub": sub, "created_at": now},
        },
        upsert=True,
    )

    response = RedirectResponse("/", status_code=303)
    _set_session_cookies(response, sub)
    response.delete_cookie("finora_oauth_state", path="/")
    return response


@router.get("/me")
def me(user_id: str = Depends(current_user_id)):
    user = users.find_one({"google_sub": user_id})
    if not user:
        raise HTTPException(status_code=401, detail="Utente non trovato.")
    return {"name": user.get("name", ""), "email": user.get("email", ""), "picture": user.get("picture", "")}


@router.post("/logout", status_code=204)
def logout(response: Response, _: None = Depends(csrf_protect)):
    response.delete_cookie("finora_session", path="/")
    response.delete_cookie("finora_csrf", path="/")
