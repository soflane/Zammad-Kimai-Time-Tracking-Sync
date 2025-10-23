from cryptography.fernet import Fernet
from app.config import settings

def get_fernet_key():
    """Returns the Fernet key from settings."""
    return Fernet(settings.encryption_key.encode('utf-8'))

def encrypt_data(data: str) -> str:
    """Encrypts a string using Fernet."""
    f = get_fernet_key()
    return f.encrypt(data.encode('utf-8')).decode('utf-8')

def decrypt_data(encrypted_data: str) -> str:
    """Decrypts a string using Fernet."""
    f = get_fernet_key()
    return f.decrypt(encrypted_data.encode('utf-8')).decode('utf-8')
