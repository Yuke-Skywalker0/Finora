import hashlib
import hmac
import secrets
from datetime import datetime, timedelta, timezone

import jwt
from cryptography.fernet import Fernet, InvalidToken
from fastapi import Cookie, Header, HTTPException, status

from .config import settings

fernet = Fernet(settings.data_encryption_key.encode())

def owner_key(google_sub: str) -> str:
    return hmac.new(settings.user_index_secret.encode(), google_sub.encode(), hashlib.sha256).hexdigest()

def encrypt_text(value: str) -> str: return fernet.encrypt(value.encode()).decode()

def decrypt_text(value: str) -> str:
    try: return fernet.decrypt(value.encode()).decode()
    except InvalidToken as exc: raise HTTPException(status_code=500, detail="Impossibile decifrare i dati.") from exc

def create_session(user_id: str) -> str:
    now=datetime.now(timezone.utc)
    return jwt.encode({"sub":user_id,"iat":now,"exp":now+timedelta(minutes=settings.access_token_minutes)},settings.jwt_secret,algorithm="HS256")

def create_csrf_token() -> str: return secrets.token_urlsafe(32)

def current_user_id(finora_session: str | None = Cookie(default=None)) -> str:
    if not finora_session: raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Non autenticato.")
    try:
        payload=jwt.decode(finora_session,settings.jwt_secret,algorithms=["HS256"])
        sub=payload.get("sub")
        if not sub: raise ValueError()
        return str(sub)
    except (jwt.PyJWTError,ValueError) as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Sessione non valida.") from exc

def csrf_protect(csrf_cookie: str | None = Cookie(default=None, alias="finora_csrf"), csrf_header: str | None = Header(default=None, alias="X-CSRF-Token")):
    if not csrf_cookie or not csrf_header or not hmac.compare_digest(csrf_cookie, csrf_header):
        raise HTTPException(status_code=403, detail="CSRF token non valido.")
