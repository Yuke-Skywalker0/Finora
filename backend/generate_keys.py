import secrets
from cryptography.fernet import Fernet

print("JWT_SECRET=" + secrets.token_urlsafe(64))
print("DATA_ENCRYPTION_KEY=" + Fernet.generate_key().decode())
print("USER_INDEX_SECRET=" + secrets.token_urlsafe(64))
