from datetime import datetime, timezone
from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException
from ..security import current_user_id, owner_key, encrypt_text, decrypt_text, csrf_protect

def make_router(collection,prefix,tag,fields,schema):
    router=APIRouter(prefix=prefix,tags=[tag])
    def enc(v):
        if v is None:return None
        if hasattr(v,"isoformat"):v=v.isoformat()
        return encrypt_text(str(v))
    def dec(doc):
        out={"id":str(doc["_id"])}
        for k in fields:
            v=doc.get(k)
            if v is not None:v=decrypt_text(v)
            if k in {"limit","target_amount","current_amount","amount"} and v is not None:v=float(v)
            out[k]=v
        return out
    @router.get("")
    def listing(user_id=Depends(current_user_id)):
        return [dec(x) for x in collection.find({"owner_key":owner_key(user_id)}).sort("created_at",-1)]
    @router.post("",status_code=201)
    def create(payload:schema,user_id=Depends(current_user_id),_=Depends(csrf_protect)):
        data=payload.model_dump(); doc={"owner_key":owner_key(user_id),"created_at":datetime.now(timezone.utc)}
        for k in fields:
            if k in data:doc[k]=enc(data[k])
        r=collection.insert_one(doc);doc["_id"]=r.inserted_id;return dec(doc)
    @router.delete("/{item_id}",status_code=204)
    def delete(item_id,user_id=Depends(current_user_id),_=Depends(csrf_protect)):
        try:oid=ObjectId(item_id)
        except:raise HTTPException(400,"ID non valido.")
        r=collection.delete_one({"_id":oid,"owner_key":owner_key(user_id)})
        if not r.deleted_count:raise HTTPException(404,"Elemento non trovato.")
    return router
