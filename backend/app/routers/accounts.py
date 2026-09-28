from datetime import datetime, timezone
from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException

from ..db import accounts, transactions
from ..models import AccountCreate
from ..security import current_user_id, owner_key, encrypt_text, decrypt_text, csrf_protect

router = APIRouter(prefix="/api/accounts", tags=["accounts"])

def decode(doc):
    return {
        "id": str(doc["_id"]),
        "name": decrypt_text(doc["name_enc"]),
        "type": decrypt_text(doc["type_enc"]),
        "initial_balance": float(decrypt_text(doc["balance_enc"]))
    }

@router.get("")
def list_accounts(user_id: str = Depends(current_user_id)):
    docs = accounts.find({"owner_key": owner_key(user_id)}).sort("created_at", 1)
    return [decode(x) for x in docs]

@router.post("", status_code=201)
def create_account(payload: AccountCreate, user_id: str = Depends(current_user_id), _: None = Depends(csrf_protect)):
    doc = {
        "owner_key": owner_key(user_id),
        "name_enc": encrypt_text(payload.name.strip()),
        "type_enc": encrypt_text(payload.type),
        "balance_enc": encrypt_text(f"{payload.initial_balance:.2f}"),
        "created_at": datetime.now(timezone.utc)
    }
    r = accounts.insert_one(doc)
    doc["_id"] = r.inserted_id
    return decode(doc)

@router.delete("/{account_id}", status_code=204)
def delete_account(account_id: str, user_id: str = Depends(current_user_id), _: None = Depends(csrf_protect)):
    try:
        oid = ObjectId(account_id)
    except Exception as exc:
        raise HTTPException(400, "ID non valido.") from exc
    key = owner_key(user_id)
    if transactions.find_one({"owner_key": key, "account_id": account_id}):
        raise HTTPException(409, "Questo conto ha transazioni collegate.")
    r = accounts.delete_one({"_id": oid, "owner_key": key})
    if r.deleted_count == 0:
        raise HTTPException(404, "Conto non trovato.")
