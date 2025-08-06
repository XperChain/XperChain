from cryptography.fernet import Fernet
import hashlib, base64
def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

# 사용자 password 기반 대칭키 생성 (권장: salt를 추가해 강화)
def generate_fernet_key(password: str) -> bytes:
    key = hashlib.sha256(password.encode()).digest()
    return base64.urlsafe_b64encode(key)

def encrypt_private_key(private_key: str, password: str) -> str:
    fernet_key = generate_fernet_key(password)
    f = Fernet(fernet_key)
    return f.encrypt(private_key.encode()).decode()

def decrypt_private_key(encrypted_key: str, password: str) -> str:
    fernet_key = generate_fernet_key(password)
    f = Fernet(fernet_key)
    return f.decrypt(encrypted_key.encode()).decode()
