from datetime import datetime, timezone

from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException

from ..db import transactions, accounts
from ..models import TransactionCreate, TransactionUpdate
from ..security import current_user_id, decrypt_text, encrypt_text, owner_key, csrf_protect

router = APIRouter(prefix="/api/transactions", tags=["transactions"])

def decode(doc):
    return {
        "id": str(doc["_id"]),
        "type": decrypt_text(doc["type_enc"]),
        "amount": float(decrypt_text(doc["amount_enc"])),
        "category": decrypt_text(doc["category_enc"]),
        "description": decrypt_text(doc["description_enc"]),
        "date": decrypt_text(doc["date_enc"]),
        "account_id": doc.get("account_id")
    }

@router.get("")
def list_transactions(user_id: str = Depends(current_user_id)):
    key = owner_key(user_id)
    docs = transactions.find({"owner_key": key}).sort("created_at", -1)
    return [decode(doc) for doc in docs]

@router.post("", status_code=201)
def create_transaction(payload: TransactionCreate, user_id: str = Depends(current_user_id), _: None = Depends(csrf_protect)):
    key = owner_key(user_id)
    if payload.account_id:
        try:
            account = accounts.find_one({"_id": ObjectId(payload.account_id), "owner_key": key})
        except Exception as exc:
            raise HTTPException(400, "Conto non valido.") from exc
        if not account:
            raise HTTPException(400, "Conto non valido.")

    doc = {
        "owner_key": key,
        "type_enc": encrypt_text(payload.type),
        "amount_enc": encrypt_text(f"{payload.amount:.2f}"),
        "category_enc": encrypt_text(payload.category),
        "description_enc": encrypt_text(payload.description),
        "date_enc": encrypt_text(payload.date.isoformat()),
        "account_id": payload.account_id,
        "created_at": datetime.now(timezone.utc)
    }

    result = transactions.insert_one(doc)
    doc["_id"] = result.inserted_id
    return decode(doc)

@router.put("/{transaction_id}")
def update_transaction(transaction_id: str, payload: TransactionUpdate, user_id: str = Depends(current_user_id), _: None = Depends(csrf_protect)):
    try:
        oid = ObjectId(transaction_id)
    except Exception as exc:
        raise HTTPException(status_code=400, detail="ID non valido.") from exc
    key = owner_key(user_id)
    if payload.account_id:
        try:
            account = accounts.find_one({"_id": ObjectId(payload.account_id), "owner_key": key})
        except Exception as exc:
            raise HTTPException(status_code=400, detail="Conto non valido.") from exc
        if not account:
            raise HTTPException(status_code=400, detail="Conto non valido.")
    result = transactions.update_one({"_id": oid, "owner_key": key}, {"$set": {
        "type_enc": encrypt_text(payload.type), "amount_enc": encrypt_text(f"{payload.amount:.2f}"),
        "category_enc": encrypt_text(payload.category), "description_enc": encrypt_text(payload.description),
        "date_enc": encrypt_text(payload.date.isoformat()), "account_id": payload.account_id
    }})
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Transazione non trovata.")
    return decode(transactions.find_one({"_id": oid, "owner_key": key}))

@router.delete("/{transaction_id}", status_code=204)
def delete_transaction(transaction_id: str, user_id: str = Depends(current_user_id), _: None = Depends(csrf_protect)):
    try:
        object_id = ObjectId(transaction_id)
    except Exception as exc:
        raise HTTPException(status_code=400, detail="ID non valido.") from exc

    result = transactions.delete_one({
        "_id": object_id,
        "owner_key": owner_key(user_id)
    })

    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Transazione non trovata.")
